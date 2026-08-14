from datetime import datetime, timezone
from typing import Any


STEP_STATES = ("pending", "eligible", "executed", "done")

STATE_PENDING = "pending"
STATE_ELIGIBLE = "eligible"
STATE_EXECUTED = "executed"
STATE_DONE = "done"


class WithdrawalEngine:
    """Evaluates multi-step withdrawal strategies against live portfolio state.

    Each strategy step has:
        id              – unique identifier
        condition       – dict describing when the step becomes eligible
        action          – dict describing what to do once eligible
        once            – if True, execute at most once then mark done
        cooldown_seconds – seconds to wait after execution before re-evaluating
        sequential      – if True, this step can only run after the previous step has executed
    """

    # ── public ────────────────────────────────────────────────────────────

    def evaluate_withdrawal_strategy(
        self,
        strategy_steps: list[dict],
        step_states: dict[str, dict],
        portfolio_state: dict[str, Any],
    ) -> list[dict]:
        """Walk through *strategy_steps* in order and return a list of action
        dicts for every step that should fire right now.

        *step_states* is mutated in-place so callers can persist it between
        evaluation rounds.
        """

        now = datetime.now(timezone.utc)
        actions: list[dict] = []

        for idx, step in enumerate(strategy_steps):
            step_id = str(step["id"])
            state = step_states.get(step_id, {})
            current_status = state.get("status", STATE_PENDING)

            # ── once flag: skip if already executed ───────────────────────
            if step.get("once", False) and current_status in (STATE_EXECUTED, STATE_DONE):
                continue

            # ── sequential constraint ─────────────────────────────────────
            if step.get("sequential", False) and idx > 0:
                prev_id = str(strategy_steps[idx - 1]["id"])
                prev_status = step_states.get(prev_id, {}).get("status", STATE_PENDING)
                if prev_status not in (STATE_EXECUTED, STATE_DONE):
                    continue

            # ── cooldown check ────────────────────────────────────────────
            cooldown = step.get("cooldown_seconds", 0)
            last_executed_at = state.get("last_executed_at")
            if cooldown > 0 and last_executed_at is not None:
                if isinstance(last_executed_at, str):
                    last_executed_at = datetime.fromisoformat(last_executed_at)
                elapsed = (now - last_executed_at).total_seconds()
                if elapsed < cooldown:
                    continue

            # ── evaluate condition ────────────────────────────────────────
            condition_met = self._evaluate_condition(
                step.get("condition", {}),
                portfolio_state,
                step_states,
            )

            if not condition_met:
                # transition back to pending if it was eligible
                if current_status == STATE_ELIGIBLE:
                    step_states[step_id] = {
                        "status": STATE_PENDING,
                        "last_executed_at": state.get("last_executed_at"),
                    }
                continue

            # condition is met – advance state and build action
            new_status = STATE_EXECUTED
            if step.get("once", False):
                new_status = STATE_DONE

            step_states[step_id] = {
                "status": new_status,
                "last_executed_at": now.isoformat(),
            }

            action = self._build_action(step.get("action", {}), portfolio_state, step_id)
            if action is not None:
                actions.append(action)

        return actions

    # ── condition evaluation ──────────────────────────────────────────────

    def _evaluate_condition(
        self,
        condition: dict,
        portfolio: dict[str, Any],
        step_states: dict[str, dict],
    ) -> bool:
        """Return True when *condition* is satisfied by *portfolio*."""

        ctype = condition.get("type", "")

        if ctype == "profit_threshold":
            return self._cond_profit_threshold(condition, portfolio)
        if ctype == "profit_pct":
            return self._cond_profit_pct(condition, portfolio)
        if ctype == "trailing_stop_fall":
            return self._cond_trailing_stop_fall(condition, portfolio)
        if ctype == "profit_rise":
            return self._cond_profit_rise(condition, portfolio)
        if ctype == "drawdown_from_peak":
            return self._cond_drawdown_from_peak(condition, portfolio)
        if ctype == "volatility_spike":
            return self._cond_volatility_spike(condition, portfolio)
        if ctype == "combined":
            return self._cond_combined(condition, portfolio, step_states)

        return False

    # -- individual condition implementations --------------------------------

    @staticmethod
    def _cond_profit_threshold(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when unrealised profit (absolute) >= threshold."""
        threshold = condition.get("threshold", 0)
        profit = portfolio.get("unrealised_profit", 0)
        return profit >= threshold

    @staticmethod
    def _cond_profit_pct(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when profit percentage >= target."""
        target_pct = condition.get("target_pct", 0)
        current_pct = portfolio.get("profit_pct", 0)
        return current_pct >= target_pct

    @staticmethod
    def _cond_trailing_stop_fall(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when price has fallen *fall_pct* from the recorded peak.

        Expects ``condition["fall_pct"]`` as a positive number (e.g. 5 means
        5 % drop).  The portfolio must provide ``peak_value`` and
        ``current_value``.
        """
        fall_pct = condition.get("fall_pct", 0)
        peak = portfolio.get("peak_value", 0)
        current = portfolio.get("current_value", 0)
        if peak <= 0:
            return False
        drop = ((peak - current) / peak) * 100
        return drop >= fall_pct

    @staticmethod
    def _cond_profit_rise(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when profit has risen by at least *rise_pct* since the step
        was first eligible.

        Expects ``condition["rise_pct"]`` and a ``baseline_profit`` stored in
        the portfolio.
        """
        rise_pct = condition.get("rise_pct", 0)
        baseline = portfolio.get("baseline_profit", 0)
        current = portfolio.get("unrealised_profit", 0)
        if baseline <= 0:
            return current >= rise_pct
        pct_change = ((current - baseline) / abs(baseline)) * 100
        return pct_change >= rise_pct

    @staticmethod
    def _cond_drawdown_from_peak(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when drawdown from all-time-high portfolio value >= threshold.

        Expects ``condition["max_drawdown_pct"]`` and the portfolio to provide
        ``all_time_peak`` and ``current_value``.
        """
        max_dd = condition.get("max_drawdown_pct", 0)
        peak = portfolio.get("all_time_peak", 0)
        current = portfolio.get("current_value", 0)
        if peak <= 0:
            return False
        dd = ((peak - current) / peak) * 100
        return dd >= max_dd

    @staticmethod
    def _cond_volatility_spike(condition: dict, portfolio: dict[str, Any]) -> bool:
        """True when current volatility exceeds the threshold.

        ``volatility`` in the portfolio is expected to be annualised or
        normalised – just compare directly.
        """
        threshold = condition.get("threshold", 0)
        current_vol = portfolio.get("volatility", 0)
        return current_vol >= threshold

    def _cond_combined(
        self,
        condition: dict,
        portfolio: dict[str, Any],
        step_states: dict[str, dict],
    ) -> bool:
        """Evaluate a group of sub-conditions with AND / OR logic.

        ``condition`` schema::

            {
                "type": "combined",
                "logic": "and" | "or",
                "conditions": [ <sub-condition>, ... ]
            }
        """
        logic = condition.get("logic", "and").lower()
        sub_conditions = condition.get("conditions", [])

        if not sub_conditions:
            return False

        results = [
            self._evaluate_condition(sub, portfolio, step_states)
            for sub in sub_conditions
        ]

        if logic == "or":
            return any(results)
        return all(results)

    # ── action building ───────────────────────────────────────────────────

    def _build_action(
        self,
        action: dict,
        portfolio: dict[str, Any],
        step_id: str,
    ) -> dict | None:
        """Translate an action spec into an executable instruction dict.

        Returns ``None`` when the action cannot be formed (e.g. insufficient
        funds for a fixed withdrawal).
        """

        atype = action.get("type", "")

        if atype == "withdraw_pct":
            return self._action_withdraw_pct(action, portfolio, step_id)
        if atype == "withdraw_fixed":
            return self._action_withdraw_fixed(action, portfolio, step_id)
        if atype == "convert_to_stablecoin":
            return self._action_convert_to_stablecoin(action, portfolio, step_id)
        if atype == "close_positions":
            return self._action_close_positions(action, portfolio, step_id)

        return None

    @staticmethod
    def _action_withdraw_pct(
        action: dict, portfolio: dict[str, Any], step_id: str,
    ) -> dict:
        """Withdraw *pct* of the current portfolio value (or a specific asset)."""
        pct = action.get("pct", 0)
        if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
            raise ValueError("withdraw_pct requires pct between 0 and 100")
        asset = action.get("asset", "total")
        if asset == "total":
            value = portfolio.get("current_value", 0)
        else:
            holdings = portfolio.get("holdings", {})
            value = holdings.get(asset, {}).get("value", 0)
        amount = round(value * (pct / 100), 2)
        return {
            "step_id": step_id,
            "type": "withdraw",
            "asset": asset,
            "amount": amount,
            "pct": pct,
        }

    @staticmethod
    def _action_withdraw_fixed(
        action: dict, portfolio: dict[str, Any], step_id: str,
    ) -> dict | None:
        """Withdraw a fixed *amount* of *asset* if sufficient balance exists."""
        amount = action.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("withdraw_fixed requires a non-negative amount")
        asset = action.get("asset", "total")
        if asset == "total":
            available = portfolio.get("current_value", 0)
        else:
            holdings = portfolio.get("holdings", {})
            available = holdings.get(asset, {}).get("value", 0)
        if amount > available:
            return None
        return {
            "step_id": step_id,
            "type": "withdraw",
            "asset": asset,
            "amount": amount,
            "pct": None,
        }

    @staticmethod
    def _action_convert_to_stablecoin(
        action: dict, portfolio: dict[str, Any], step_id: str,
    ) -> dict:
        """Convert *pct* (or *amount*) of *asset* to *stablecoin*."""
        asset = action.get("asset")
        stablecoin = action.get("stablecoin", "USDC")
        pct = action.get("pct")
        amount = action.get("amount")

        holdings = portfolio.get("holdings", {})
        asset_value = holdings.get(asset, {}).get("value", 0)

        if pct is not None:
            convert_amount = round(asset_value * (pct / 100), 2)
        elif amount is not None:
            convert_amount = min(amount, asset_value)
        else:
            convert_amount = asset_value

        return {
            "step_id": step_id,
            "type": "convert",
            "from_asset": asset,
            "to_asset": stablecoin,
            "amount": convert_amount,
        }

    @staticmethod
    def _action_close_positions(
        action: dict, portfolio: dict[str, Any], step_id: str,
    ) -> dict:
        """Close one or all open positions.

        ``action["asset"]`` may be a specific asset symbol or ``"all"``.
        """
        target = action.get("asset", "all")
        holdings = portfolio.get("holdings", {})

        if target == "all":
            positions = [
                {"asset": sym, "value": info.get("value", 0)}
                for sym, info in holdings.items()
            ]
        else:
            info = holdings.get(target, {})
            positions = [{"asset": target, "value": info.get("value", 0)}]

        return {
            "step_id": step_id,
            "type": "close_positions",
            "positions": positions,
            "total_value": sum(p["value"] for p in positions),
        }
