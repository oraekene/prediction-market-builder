from __future__ import annotations

import logging
import random
from typing import Any

import numpy as np

from app.services.backtester import BacktestResult
from app.ai.tabpfn_service import TabPFNService
from app.ai.pi_autoresearch.nsgaii import nsga2_optimize
from app.ai.pi_autoresearch.monte_carlo import monte_carlo_backtest
from app.ai.pi_autoresearch.genetic_programming import evolve_population

logger = logging.getLogger(__name__)

HYPOTHESIS_TEMPLATES = [
    {
        "template": "Momentum breakout on {feature}",
        "params": {"feature": "odds_momentum_3h", "operator": "gt", "threshold_range": (0.55, 0.75)},
        "regime_affinity": ["trending"],
    },
    {
        "template": "Mean reversion on {feature}",
        "params": {"feature": "odds_deviation", "operator": "gt", "threshold_range": (0.08, 0.2)},
        "regime_affinity": ["ranging", "calm"],
    },
    {
        "template": "Volatility contraction entry on {feature}",
        "params": {"feature": "volatility_20h", "operator": "lt", "threshold_range": (0.02, 0.06)},
        "regime_affinity": ["calm", "ranging"],
    },
    {
        "template": "Volume spike confirmation on {feature}",
        "params": {"feature": "volume_spike_ratio", "operator": "gt", "threshold_range": (1.5, 3.0)},
        "regime_affinity": ["volatile", "trending"],
    },
    {
        "template": "Spread contraction scalp on {feature}",
        "params": {"feature": "spread_width", "operator": "lt", "threshold_range": (0.01, 0.04)},
        "regime_affinity": ["calm", "ranging"],
    },
]


class AutoresearchService:
    def __init__(
        self,
        tabpfn_service: TabPFNService | None = None,
        experiment_tracker: Any = None,
        hermes_plugin: Any = None,
    ):
        self.tabpfn = tabpfn_service or TabPFNService()
        self.experiment_tracker = experiment_tracker
        self.hermes_plugin = hermes_plugin

    async def run_iteration(
        self,
        strategy_id: str,
        market_history: list[dict[str, Any]],
        climate: dict[str, Any],
        feature_importance: dict[str, float] | None = None,
        alpha_vector: dict[str, Any] | None = None,
        past_results: list[dict[str, Any]] | None = None,
        preset: str = "sharpe_max",
        session_id: str | None = None,
        enable_genetic: bool = False,
    ) -> dict[str, Any]:
        hypotheses = await self._generate_hypotheses(
            climate=climate,
            feature_importance=feature_importance or {},
            alpha_vector=alpha_vector,
            past_results=past_results or [],
            enable_genetic=enable_genetic,
        )

        market_snapshot = market_history[-1] if market_history else {"current_odds": 0.5}
        surviving = await self._quick_rejection(hypotheses, market_snapshot)

        if not surviving:
            return {
                "iteration": -1,
                "hypothesis": "No hypothesis passed quick rejection",
                "verdict": "SKIPPED",
                "composite_score": 0.0,
                "mc_result": None,
                "pareto_front": [],
            }

        evaluated: list[dict[str, Any]] = []
        for h in surviving:
            mc_result = await monte_carlo_backtest(
                {"threshold": h["threshold"], "operator": h["operator"], "side": "yes"},
                market_history,
                n=50,
            )
            tabpfn_result = await self.tabpfn.validate_signal(
                market_data=market_snapshot,
                regime_vector=[climate.get("metrics", {}).get("volatility", 0.5)],
            )
            objectives = [
                mc_result.mean_sharpe,
                mc_result.mean_win_rate,
                -abs(mc_result.var_95),
                tabpfn_result.get("probability", 0.5),
            ]
            evaluated.append({
                "hypothesis": h,
                "mc_result": mc_result,
                "tabpfn_result": tabpfn_result,
                "objectives": objectives,
            })

        ranked = nsga2_optimize(
            [e["hypothesis"] for e in evaluated],
            [e["objectives"] for e in evaluated],
        )

        best_eval = evaluated[0]
        best = best_eval["hypothesis"]
        mc_result = best_eval["mc_result"]
        tabpfn_result = best_eval["tabpfn_result"]

        pareto_rank = ranked[0].rank if ranked else 0
        composite_score = self._compute_composite_score(
            mc_result, mc_result.mean_sharpe, tabpfn_result, preset=preset
        )
        verdict = self._determine_verdict(composite_score, pareto_rank)

        tabpfn_features = self._build_feature_vector(market_snapshot, climate, best)

        git_commit_hash = None
        if verdict == "KEPT" and self.experiment_tracker and session_id:
            try:
                exp_result = {
                    "session_id": session_id,
                    "iteration": 1,
                    "hypothesis": best.get("description", "unknown"),
                    "composite_score": composite_score,
                    "verdict": verdict,
                    "mc_stats": mc_result.to_dict(),
                    "pareto_rank": pareto_rank,
                }
                git_commit_hash = await self.experiment_tracker.commit_experiment(exp_result)
            except Exception as exc:
                logger.warning("Experiment commit failed: %s", exc)

        hermes_critique = None
        if self.hermes_plugin and self.hermes_plugin.available:
            try:
                hermes_critique = await self.hermes_plugin.critique_result({
                    "hypothesis": best.get("description", "unknown"),
                    "composite_score": composite_score,
                    "verdict": verdict,
                })
            except Exception as exc:
                logger.warning("Hermes critique failed: %s", exc)

        return {
            "iteration": 1,
            "hypothesis": best.get("description", "unknown"),
            "hypothesis_prompt": "",
            "backtest_config": {"threshold": best["threshold"], "operator": best["operator"]},
            "backtest_trades": 0,
            "backtest_win_rate": round(mc_result.mean_win_rate, 4),
            "backtest_sharpe": round(mc_result.mean_sharpe, 4),
            "backtest_max_drawdown": round(abs(mc_result.var_95), 4),
            "backtest_total_pnl": round(mc_result.mean_total_pnl, 2),
            "tabpfn_probability": tabpfn_result.get("probability", 0.5),
            "tabpfn_confidence": tabpfn_result.get("confidence", 0.0),
            "tabpfn_features": tabpfn_features,
            "composite_score": round(composite_score, 4),
            "verdict": verdict,
            "git_commit_hash": git_commit_hash,
            "mc_result": mc_result.to_dict(),
            "mc_var_95": round(mc_result.var_95, 4),
            "mc_cvar_95": round(mc_result.cvar_95, 4),
            "pareto_rank": pareto_rank,
            "pareto_front": [
                {
                    "hypothesis": e["hypothesis"].get("description", "unknown"),
                    "threshold": e["hypothesis"].get("threshold"),
                    "operator": e["hypothesis"].get("operator"),
                    "pareto_rank": ranked[i].rank if i < len(ranked) else None,
                }
                for i, e in enumerate(evaluated)
            ],
            "hermes_critique": hermes_critique,
        }

    async def _generate_hypotheses(
        self,
        climate: dict[str, Any],
        feature_importance: dict[str, float],
        alpha_vector: dict[str, Any] | None = None,
        past_results: list[dict[str, Any]] | None = None,
        enable_genetic: bool = False,
        n: int = 5,
    ) -> list[dict[str, Any]]:
        regime = climate.get("regime", "calm")
        top_features = sorted(feature_importance.items(), key=lambda x: -x[1])[:3] if feature_importance else []
        top_feature_names = [f[0] for f in top_features]

        kept_count = len([r for r in (past_results or []) if r.get("verdict") == "KEPT"])
        if enable_genetic and kept_count >= 2 and top_feature_names:
            try:
                return evolve_population(
                    past_results=past_results or [],
                    top_features=top_feature_names,
                    pop_size=n,
                )
            except Exception as exc:
                logger.warning("Genetic evolution failed, falling back to templates: %s", exc)

        matched_templates = [
            t for t in HYPOTHESIS_TEMPLATES
            if regime in t["regime_affinity"] or "calm" in t["regime_affinity"]
        ]
        if not matched_templates:
            matched_templates = HYPOTHESIS_TEMPLATES

        selected = random.sample(matched_templates, min(n, len(matched_templates)))
        hypotheses = []
        for t in selected:
            lo, hi = t["params"]["threshold_range"]
            threshold = round(random.uniform(lo, hi), 3)
            hypotheses.append({
                "description": t["template"].format(feature=top_feature_names[0] if top_feature_names else "odds"),
                "template": t["template"],
                "feature": top_feature_names[0] if top_feature_names else "odds",
                "operator": t["params"]["operator"],
                "threshold": threshold,
                "regime_affinity": t["regime_affinity"],
            })

        if self.hermes_plugin and self.hermes_plugin.available:
            try:
                hermes_hypotheses = await self.hermes_plugin.propose_hypotheses(
                    climate=climate,
                    feature_importance=feature_importance,
                    top_features=top_feature_names,
                    n=2,
                )
                for h in hermes_hypotheses:
                    hypotheses.append({
                        "description": h,
                        "template": "Hermes proposal: {feature}",
                        "feature": top_feature_names[0] if top_feature_names else "odds",
                        "operator": random.choice(["gt", "lt"]),
                        "threshold": round(random.uniform(0.4, 0.7), 3),
                        "regime_affinity": [regime],
                    })
            except Exception as exc:
                logger.warning("Hermes hypothesis generation failed: %s", exc)

        return hypotheses

    async def _quick_rejection(
        self,
        hypotheses: list[dict[str, Any]],
        market_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        surviving = []
        for h in hypotheses:
            try:
                features = self._build_feature_vector(market_snapshot, {}, h)
                df = _dict_to_df(features)
                prob = await self.tabpfn.predict_probability(df)
                if prob >= 0.55:
                    surviving.append(h)
            except Exception as exc:
                logger.warning("Quick rejection failed for hypothesis %s: %s", h.get("description"), exc)
                surviving.append(h)
        return surviving

    def _build_feature_vector(
        self,
        market_snapshot: dict[str, Any],
        climate: dict[str, Any],
        hypothesis: dict[str, Any],
    ) -> dict[str, float]:
        vector = {
            "odds": market_snapshot.get("current_odds", 0.5),
            "volume": market_snapshot.get("volume", 0) / 1_000_000,
            "liquidity": market_snapshot.get("liquidity", 0) / 1_000_000,
            "spread": (market_snapshot.get("ask", 0) or 0) - (market_snapshot.get("bid", 0) or 0),
            "participants": market_snapshot.get("participants", 0) / 1000,
            "hypothesis_threshold": hypothesis.get("threshold", 0.5),
        }
        metrics = climate.get("metrics", {})
        vector["volatility"] = metrics.get("volatility", 0.5)
        vector["autocorrelation"] = metrics.get("autocorrelation", 0.0)
        return vector

    def _compute_composite_score(
        self,
        backtest_result: Any,
        sharpe: float,
        tabpfn_result: dict[str, Any],
        preset: str = "sharpe_max",
    ) -> float:
        """Blend backtest quality, Sharpe and TabPFN confidence into one score.

        Accepts either a BacktestResult (win_rate/total_pnl) or an MC result
        object exposing mean_win_rate / mean_total_pnl.
        """
        win_rate: float = 0.0
        for attr in ("win_rate", "mean_win_rate"):
            value = getattr(backtest_result, attr, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                win_rate = float(value)
                break
        if not isinstance(sharpe, (int, float)) or isinstance(sharpe, bool):
            sharpe = 0.0
        normalized_sharpe = float(np.clip(sharpe / 2.0, 0.0, 1.0))
        tabpfn_prob = tabpfn_result.get("probability", 0.5)
        if not isinstance(tabpfn_prob, (int, float)):
            tabpfn_prob = 0.5
        if preset == "win_rate_max":
            return 0.7 * win_rate + 0.3 * tabpfn_prob
        if preset == "risk_adjusted":
            return 0.5 * normalized_sharpe + 0.2 * win_rate + 0.3 * tabpfn_prob
        return 0.6 * normalized_sharpe + 0.1 * win_rate + 0.3 * tabpfn_prob

    def _determine_verdict(self, score: float, pareto_rank: int = 0) -> str:
        if pareto_rank == 0 and score >= 0.6:
            return "KEPT"
        if pareto_rank <= 1 and score >= 0.45:
            return "WARN"
        return "REVERTED"


def _dict_to_df(d: dict[str, float]):
    import pandas as pd
    return pd.DataFrame([d])
