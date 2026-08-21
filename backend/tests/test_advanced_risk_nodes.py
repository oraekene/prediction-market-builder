import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from app.services.node_executor import ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.advanced_risk_node_handlers import (
    handle_trailing_stop, handle_tightening_trailing_stop, handle_atr_stop,
    handle_volatility_stop, handle_time_exit, handle_break_even_stop,
    handle_scaling_exit, handle_moving_average_exit,
    handle_daily_loss_limit, handle_weekly_loss_limit, handle_monthly_loss_limit,
    handle_max_position_count, handle_max_gross_exposure, handle_max_net_exposure,
    handle_leverage_limit, handle_sector_exposure_limit, handle_beta_exposure_limit,
    handle_volatility_targeting, handle_stress_test, handle_monte_carlo_risk,
    handle_tail_risk_check, handle_liquidity_risk_check, handle_expected_shortfall_check,
    handle_factor_exposure_check, handle_mcr_check, handle_worst_case_portfolio,
    handle_delta_exposure, handle_gamma_exposure, handle_vega_exposure,
    handle_theta_decay, handle_vanna_exposure, handle_volga_exposure,
    handle_circuit_breaker, handle_slippage_guard, handle_max_consecutive_losses,
    handle_cooldown_period, handle_position_timeout,
    handle_volatility_regime_check, handle_correlation_regime_shift,
    handle_toxicity_detection, handle_order_flow_imbalance,
    handle_risk_parity_allocation, handle_mean_variance_optimization,
    handle_hierarchical_risk_parity,
)


@pytest.fixture
def ctx():
    return ExecutionContext(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 11000, "returns": {}},
        risk_calculator=RiskCalculator(),
        portfolio_manager=PortfolioManager(10000),
    )


# ─── Position Exit Tests ──────────────────────────────────────────────────────


class TestTrailingStop:
    def test_triggers_on_long_position(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.52},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.60}],
            },
            trail_states={},
        )
        node = {"id": "ts1", "type": "trailing_stop", "data": {"trail_pct": 0.05}}
        result = handle_trailing_stop(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1
        assert result["positions"][0]["market_id"] == "m1"

    def test_does_not_trigger_when_within_trail(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.59},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.60}],
            },
            trail_states={},
        )
        node = {"id": "ts2", "type": "trailing_stop", "data": {"trail_pct": 0.05}}
        result = handle_trailing_stop(node, {}, ctx)
        assert result["triggered"] is False


class TestTighteningTrailingStop:
    def test_triggers_on_high_tier(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.50},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
            trail_states={"m1": {"high_water_mark": 0.55}},
        )
        node = {"id": "tts1", "type": "tightening_trailing_stop", "data": {
            "thresholds": [[0.05, 0.03], [0.10, 0.02], [0.20, 0.01]]
        }}
        result = handle_tightening_trailing_stop(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1
        assert "current_tier" in result["positions"][0]

    def test_does_not_trigger_on_first_tier(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.50},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
            trail_states={},
        )
        node = {"id": "tts2", "type": "tightening_trailing_stop", "data": {
            "thresholds": [[0.05, 0.03], [0.10, 0.02]]
        }}
        result = handle_tightening_trailing_stop(node, {}, ctx)
        assert result["triggered"] is False


class TestAtrStop:
    def test_triggers_when_price_below_atr_stop(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.42},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
                "atr_values": [0.04],
            },
        )
        node = {"id": "atr1", "type": "atr_stop", "data": {"atr_multiplier": 2.0}}
        result = handle_atr_stop(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1
        assert result["atr"] == 0.04

    def test_does_not_trigger_when_above_stop(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.50},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
                "atr_values": [0.02],
            },
        )
        node = {"id": "atr2", "type": "atr_stop", "data": {"atr_multiplier": 2.0}}
        result = handle_atr_stop(node, {}, ctx)
        assert result["triggered"] is False


class TestVolatilityStop:
    def test_triggers_when_vol_exceeds_threshold(self):
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.05, 100))},
        )
        node = {"id": "vs1", "type": "volatility_stop", "data": {"vol_threshold": 0.03}}
        result = handle_volatility_stop(node, {}, ctx)
        assert result["triggered"] is True
        assert result["current_vol"] > 0

    def test_does_not_trigger_with_low_vol(self):
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.01, 100))},
        )
        node = {"id": "vs2", "type": "volatility_stop", "data": {"vol_threshold": 0.03}}
        result = handle_volatility_stop(node, {}, ctx)
        assert result["triggered"] is False


class TestTimeExit:
    def test_triggers_when_held_too_long(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "entry_time": old_time}],
            },
        )
        node = {"id": "te1", "type": "time_exit", "data": {"max_hold_days": 30}}
        result = handle_time_exit(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1
        assert result["positions"][0]["hold_days"] >= 30

    def test_does_not_trigger_within_hold_period(self):
        recent_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "entry_time": recent_time}],
            },
        )
        node = {"id": "te2", "type": "time_exit", "data": {"max_hold_days": 30}}
        result = handle_time_exit(node, {}, ctx)
        assert result["triggered"] is False


class TestBreakEvenStop:
    def test_triggers_when_profit_falls_to_buffer(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.502},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
        )
        node = {"id": "be1", "type": "break_even_stop", "data": {"trigger_pct": 0.02, "buffer_pct": 0.005}}
        result = handle_break_even_stop(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1

    def test_does_not_trigger_without_profit(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.49},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
        )
        node = {"id": "be2", "type": "break_even_stop", "data": {"trigger_pct": 0.02, "buffer_pct": 0.005}}
        result = handle_break_even_stop(node, {}, ctx)
        assert result["triggered"] is False


class TestScalingExit:
    def test_triggers_on_high_profit_tier(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.70},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
        )
        node = {"id": "se1", "type": "scaling_exit", "data": {
            "tiers": [{"profit_pct": 0.10, "exit_pct": 33}, {"profit_pct": 0.25, "exit_pct": 50}]
        }}
        result = handle_scaling_exit(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 2

    def test_does_not_trigger_below_first_tier(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.51},
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "side": "buy", "price": 0.50}],
            },
        )
        node = {"id": "se2", "type": "scaling_exit", "data": {
            "tiers": [{"profit_pct": 0.10, "exit_pct": 33}]
        }}
        result = handle_scaling_exit(node, {}, ctx)
        assert result["triggered"] is False


class TestMovingAverageExit:
    def test_triggers_on_bearish_crossover(self):
        prices = [0.50] * 18 + [0.60, 0.48]
        ctx = ExecutionContext(
            portfolio={"price_history": prices},
        )
        node = {"id": "ma1", "type": "moving_average_exit", "data": {"period": 20, "ma_type": "sma"}}
        result = handle_moving_average_exit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["crossover"] == "bearish"

    def test_does_not_trigger_with_insufficient_data(self):
        ctx = ExecutionContext(
            portfolio={"price_history": [0.50, 0.51]},
        )
        node = {"id": "ma2", "type": "moving_average_exit", "data": {"period": 20}}
        result = handle_moving_average_exit(node, {}, ctx)
        assert result["triggered"] is False
        assert result["ma_value"] == 0.0


# ─── Portfolio Limit Tests ────────────────────────────────────────────────────


class TestDailyLossLimit:
    def test_triggers_on_large_daily_loss(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            daily_pnl=-500,
        )
        node = {"id": "dl1", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}}
        result = handle_daily_loss_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["loss_pct"] >= 0.03

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            daily_pnl=-200,
        )
        node = {"id": "dl2", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}}
        result = handle_daily_loss_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestWeeklyLossLimit:
    def test_triggers_on_large_weekly_loss(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            weekly_pnl=-800,
        )
        node = {"id": "wl1", "type": "weekly_loss_limit", "data": {"max_weekly_loss": 0.05}}
        result = handle_weekly_loss_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["loss_pct"] >= 0.05

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            weekly_pnl=-300,
        )
        node = {"id": "wl2", "type": "weekly_loss_limit", "data": {"max_weekly_loss": 0.05}}
        result = handle_weekly_loss_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestMonthlyLossLimit:
    def test_triggers_on_large_monthly_loss(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            monthly_pnl=-1500,
        )
        node = {"id": "ml1", "type": "monthly_loss_limit", "data": {"max_monthly_loss": 0.10}}
        result = handle_monthly_loss_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["loss_pct"] >= 0.10

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            monthly_pnl=-500,
        )
        node = {"id": "ml2", "type": "monthly_loss_limit", "data": {"max_monthly_loss": 0.10}}
        result = handle_monthly_loss_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestMaxPositionCount:
    def test_triggers_when_exceeding_max(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": f"m{i}"} for i in range(12)],
            },
        )
        node = {"id": "mpc1", "type": "max_position_count", "data": {"max_count": 10}}
        result = handle_max_position_count(node, {}, ctx)
        assert result["triggered"] is True
        assert result["count"] == 12

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": f"m{i}"} for i in range(5)],
            },
        )
        node = {"id": "mpc2", "type": "max_position_count", "data": {"max_count": 10}}
        result = handle_max_position_count(node, {}, ctx)
        assert result["triggered"] is False


class TestMaxGrossExposure:
    def test_triggers_when_over_exposed(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 6000},
                    {"market_id": "m2", "size": 5000},
                ],
            },
        )
        node = {"id": "mge1", "type": "max_gross_exposure", "data": {"max_exposure": 1.0}}
        result = handle_max_gross_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["exposure"] > 1.0

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 3000},
                    {"market_id": "m2", "size": 2000},
                ],
            },
        )
        node = {"id": "mge2", "type": "max_gross_exposure", "data": {"max_exposure": 1.0}}
        result = handle_max_gross_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestMaxNetExposure:
    def test_triggers_when_net_exposure_exceeds(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 7000, "side": "buy"},
                    {"market_id": "m2", "size": 1000, "side": "sell"},
                ],
            },
        )
        node = {"id": "mne1", "type": "max_net_exposure", "data": {"max_net_exposure": 0.5}}
        result = handle_max_net_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["net_exposure"] > 0.5

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 3000, "side": "buy"},
                    {"market_id": "m2", "size": 2000, "side": "sell"},
                ],
            },
        )
        node = {"id": "mne2", "type": "max_net_exposure", "data": {"max_net_exposure": 0.5}}
        result = handle_max_net_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestLeverageLimit:
    def test_triggers_when_leverage_exceeds(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 20000, "price": 0.80},
                    {"market_id": "m2", "size": 15000, "price": 0.70},
                ],
            },
        )
        node = {"id": "ll1", "type": "leverage_limit", "data": {"max_leverage": 2.0}}
        result = handle_leverage_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["leverage"] > 2.0

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 5000, "price": 0.50},
                    {"market_id": "m2", "size": 3000, "price": 0.50},
                ],
            },
        )
        node = {"id": "ll2", "type": "leverage_limit", "data": {"max_leverage": 2.0}}
        result = handle_leverage_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestSectorExposureLimit:
    def test_triggers_on_sector_breach(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 4000, "sector": "crypto"},
                    {"market_id": "m2", "size": 4000, "sector": "crypto"},
                ],
            },
        )
        node = {"id": "sel1", "type": "sector_exposure_limit", "data": {
            "sector_limits": {"crypto": 0.50}
        }}
        result = handle_sector_exposure_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["breached_sectors"]) == 1

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 2000, "sector": "crypto"},
                    {"market_id": "m2", "size": 2000, "sector": "stocks"},
                ],
            },
        )
        node = {"id": "sel2", "type": "sector_exposure_limit", "data": {
            "sector_limits": {"crypto": 0.50}
        }}
        result = handle_sector_exposure_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestBetaExposureLimit:
    def test_triggers_on_high_beta(self):
        ctx = ExecutionContext(
            portfolio={"beta": 1.5},
        )
        node = {"id": "bel1", "type": "beta_exposure_limit", "data": {"max_beta": 1.0}}
        result = handle_beta_exposure_limit(node, {}, ctx)
        assert result["triggered"] is True
        assert result["beta"] == 1.5

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"beta": 0.8},
        )
        node = {"id": "bel2", "type": "beta_exposure_limit", "data": {"max_beta": 1.0}}
        result = handle_beta_exposure_limit(node, {}, ctx)
        assert result["triggered"] is False


class TestVolatilityTargeting:
    def test_scales_down_on_high_vol(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.05, 100))},
        )
        node = {"id": "vt1", "type": "volatility_targeting", "data": {"target_vol": 0.02}}
        result = handle_volatility_targeting(node, {}, ctx)
        assert result["scaling_factor"] < 1.0
        assert result["current_vol"] > 0

    def test_scales_up_on_low_vol(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.02, 100))},
        )
        node = {"id": "vt2", "type": "volatility_targeting", "data": {"target_vol": 0.20}}
        result = handle_volatility_targeting(node, {}, ctx)
        assert result["scaling_factor"] > 1.0


class TestStressTest:
    def test_triggers_on_worst_case_breach(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 5000},
                    {"market_id": "m2", "size": 3000},
                ],
            },
        )
        node = {"id": "st1", "type": "stress_test", "data": {
            "max_worst_case_loss": 0.20,
            "scenarios": [
                {"name": "crash", "shocks": {"m1": -0.30, "m2": -0.20}},
                {"name": "mild", "shocks": {"m1": -0.10, "m2": -0.05}},
            ],
        }}
        result = handle_stress_test(node, {}, ctx)
        assert result["triggered"] is True
        assert result["worst_case_loss"] >= 0.20
        assert len(result["scenarios"]) == 2

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 5000},
                ],
            },
        )
        node = {"id": "st2", "type": "stress_test", "data": {
            "max_worst_case_loss": 0.50,
            "scenarios": [{"name": "mild", "shocks": {"m1": -0.05}}],
        }}
        result = handle_stress_test(node, {}, ctx)
        assert result["triggered"] is False


class TestMonteCarloRisk:
    def test_returns_var_metrics(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.02, 100))},
        )
        node = {"id": "mc1", "type": "monte_carlo_risk", "data": {"num_simulations": 500, "confidence": 0.95}}
        result = handle_monte_carlo_risk(node, {}, ctx)
        assert "var_mc" in result
        assert "worst_case" in result
        assert "percentile_5" in result
        assert result["var_mc"] >= 0

    def test_returns_zeros_with_insufficient_data(self):
        ctx = ExecutionContext(
            portfolio={"returns": [0.01]},
        )
        node = {"id": "mc2", "type": "monte_carlo_risk", "data": {"num_simulations": 500}}
        result = handle_monte_carlo_risk(node, {}, ctx)
        assert result["var_mc"] == 0.0
        assert result["worst_case"] == 0.0


class TestTailRiskCheck:
    def test_triggers_on_high_kurtosis(self):
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        returns[0] = -0.15
        returns[1] = 0.15
        ctx = ExecutionContext(portfolio={"returns": returns})
        node = {"id": "tr1", "type": "tail_risk_check", "data": {"max_kurtosis": 4.0, "max_skewness": -0.5}}
        result = handle_tail_risk_check(node, {}, ctx)
        assert result["triggered"] is True
        assert result["kurtosis"] > 4.0

    def test_does_not_trigger_with_normal_distribution(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={"returns": list(np.random.normal(0.001, 0.02, 200))},
        )
        node = {"id": "tr2", "type": "tail_risk_check", "data": {"max_kurtosis": 5.0, "max_skewness": -1.0}}
        result = handle_tail_risk_check(node, {}, ctx)
        assert result["triggered"] is False


class TestLiquidityRiskCheck:
    def test_triggers_on_low_liquidity(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.50, "liquidity": 5000, "spread": 0.01},
        )
        node = {"id": "lr1", "type": "liquidity_risk_check", "data": {"min_liquidity": 10000}}
        result = handle_liquidity_risk_check(node, {}, ctx)
        assert result["triggered"] is True
        assert result["liquidity"] == 5000

    def test_does_not_trigger_with_adequate_liquidity(self):
        ctx = ExecutionContext(
            market={"current_odds": 0.50, "liquidity": 50000, "spread": 0.01},
        )
        node = {"id": "lr2", "type": "liquidity_risk_check", "data": {
            "min_liquidity": 10000, "max_spread_pct": 0.05
        }}
        result = handle_liquidity_risk_check(node, {}, ctx)
        assert result["triggered"] is False


class TestExpectedShortfallCheck:
    def test_triggers_when_es_exceeds_limit(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            risk_calculator=RiskCalculator(),
            portfolio={"returns": list(np.random.normal(-0.01, 0.05, 100))},
        )
        node = {"id": "es1", "type": "expected_shortfall_check", "data": {"confidence": 0.95, "limit": 0.03}}
        result = handle_expected_shortfall_check(node, {}, ctx)
        assert result["triggered"] is True
        assert result["es"] > 0

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            risk_calculator=RiskCalculator(),
            portfolio={"returns": [0.01] * 10},
        )
        node = {"id": "es2", "type": "expected_shortfall_check", "data": {"confidence": 0.95, "limit": 0.10}}
        result = handle_expected_shortfall_check(node, {}, ctx)
        assert result["triggered"] is False


# ─── Diversification Tests ───────────────────────────────────────────────────


class TestFactorExposureCheck:
    def test_triggers_on_factor_breach(self):
        ctx = ExecutionContext(
            portfolio={"factor_exposures": {"momentum": 1.2, "value": 0.3}},
        )
        node = {"id": "fec1", "type": "factor_exposure_check", "data": {
            "max_factor_exposures": {"momentum": 0.8, "value": 0.5}
        }}
        result = handle_factor_exposure_check(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["breached_factors"]) == 1
        assert result["breached_factors"][0]["factor"] == "momentum"

    def test_does_not_trigger_within_limits(self):
        ctx = ExecutionContext(
            portfolio={"factor_exposures": {"momentum": 0.5, "value": 0.3}},
        )
        node = {"id": "fec2", "type": "factor_exposure_check", "data": {
            "max_factor_exposures": {"momentum": 0.8, "value": 0.5}
        }}
        result = handle_factor_exposure_check(node, {}, ctx)
        assert result["triggered"] is False


class TestMcrCheck:
    def test_triggers_on_high_mcr(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            risk_calculator=RiskCalculator(),
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 5000},
                    {"market_id": "m2", "size": 5000},
                ],
                "returns": list(np.random.normal(0.001, 0.03, 100)),
            },
        )
        node = {"id": "mcr1", "type": "mcr_check", "data": {"max_mcr": 0.005}}
        result = handle_mcr_check(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["mcr_values"]) == 2

    def test_does_not_trigger_within_limit(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            risk_calculator=RiskCalculator(),
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1", "size": 5000},
                ],
                "returns": list(np.random.normal(0.001, 0.03, 100)),
            },
        )
        node = {"id": "mcr2", "type": "mcr_check", "data": {"max_mcr": 0.5}}
        result = handle_mcr_check(node, {}, ctx)
        assert result["triggered"] is False


class TestWorstCasePortfolio:
    def test_triggers_on_large_worst_case_loss(self):
        returns = [-0.05, -0.08, -0.10, -0.03, -0.06, -0.04, 0.01, 0.02]
        ctx = ExecutionContext(
            portfolio={"current_capital": 10000, "returns": returns},
        )
        node = {"id": "wcp1", "type": "worst_case_portfolio", "data": {"max_worst_case_loss": 0.05}}
        result = handle_worst_case_portfolio(node, {}, ctx)
        assert result["triggered"] is True
        assert result["worst_case_loss"] >= 0.05

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"current_capital": 10000, "returns": [0.01, 0.02, 0.01, 0.01]},
        )
        node = {"id": "wcp2", "type": "worst_case_portfolio", "data": {"max_worst_case_loss": 0.50}}
        result = handle_worst_case_portfolio(node, {}, ctx)
        assert result["triggered"] is False


# ─── Greeks Tests ─────────────────────────────────────────────────────────────


class TestDeltaExposure:
    def test_triggers_on_high_delta(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"delta": 1.5}},
        )
        node = {"id": "de1", "type": "delta_exposure", "data": {"max_delta": 1.0}}
        result = handle_delta_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["delta"] == 1.5

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"delta": 0.5}},
        )
        node = {"id": "de2", "type": "delta_exposure", "data": {"max_delta": 1.0}}
        result = handle_delta_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestGammaExposure:
    def test_triggers_on_high_gamma(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"gamma": 0.7}},
        )
        node = {"id": "ge1", "type": "gamma_exposure", "data": {"max_gamma": 0.5}}
        result = handle_gamma_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["gamma"] == 0.7

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"gamma": 0.3}},
        )
        node = {"id": "ge2", "type": "gamma_exposure", "data": {"max_gamma": 0.5}}
        result = handle_gamma_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestVegaExposure:
    def test_triggers_on_high_vega(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"vega": 0.6}},
        )
        node = {"id": "ve1", "type": "vega_exposure", "data": {"max_vega": 0.5}}
        result = handle_vega_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["vega"] == 0.6

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"vega": 0.2}},
        )
        node = {"id": "ve2", "type": "vega_exposure", "data": {"max_vega": 0.5}}
        result = handle_vega_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestThetaDecay:
    def test_triggers_on_large_negative_theta(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"theta": -150}},
        )
        node = {"id": "td1", "type": "theta_decay", "data": {"max_theta_loss": 100}}
        result = handle_theta_decay(node, {}, ctx)
        assert result["triggered"] is True
        assert result["theta"] == -150

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"theta": -50}},
        )
        node = {"id": "td2", "type": "theta_decay", "data": {"max_theta_loss": 100}}
        result = handle_theta_decay(node, {}, ctx)
        assert result["triggered"] is False


class TestVannaExposure:
    def test_triggers_on_high_vanna(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"vanna": 0.4}},
        )
        node = {"id": "vn1", "type": "vanna_exposure", "data": {"max_vanna": 0.3}}
        result = handle_vanna_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["vanna"] == 0.4

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"vanna": 0.1}},
        )
        node = {"id": "vn2", "type": "vanna_exposure", "data": {"max_vanna": 0.3}}
        result = handle_vanna_exposure(node, {}, ctx)
        assert result["triggered"] is False


class TestVolgaExposure:
    def test_triggers_on_high_volga(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"volga": 0.5}},
        )
        node = {"id": "vg1", "type": "volga_exposure", "data": {"max_volga": 0.3}}
        result = handle_volga_exposure(node, {}, ctx)
        assert result["triggered"] is True
        assert result["volga"] == 0.5

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"greeks": {"volga": 0.1}},
        )
        node = {"id": "vg2", "type": "volga_exposure", "data": {"max_volga": 0.3}}
        result = handle_volga_exposure(node, {}, ctx)
        assert result["triggered"] is False


# ─── Execution/Operational Tests ──────────────────────────────────────────────


class TestCircuitBreaker:
    def test_triggers_on_daily_loss_breach(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            daily_pnl=-800,
            consecutive_losses=2,
            circuit_breaker_state={"state": "closed"},
        )
        node = {"id": "cb1", "type": "circuit_breaker", "data": {"max_daily_loss": 0.05}}
        result = handle_circuit_breaker(node, {}, ctx)
        assert result["triggered"] is True
        assert result["state"] == "cooldown"

    def test_does_not_trigger_within_limits(self):
        ctx = ExecutionContext(
            portfolio={"initial_capital": 10000},
            daily_pnl=-100,
            consecutive_losses=2,
            circuit_breaker_state={"state": "closed"},
        )
        node = {"id": "cb2", "type": "circuit_breaker", "data": {
            "max_daily_loss": 0.05, "max_consecutive_losses": 5
        }}
        result = handle_circuit_breaker(node, {}, ctx)
        assert result["triggered"] is False
        assert result["state"] == "closed"


class TestSlippageGuard:
    def test_triggers_on_high_slippage(self):
        ctx = ExecutionContext(
            portfolio={"last_trade_slippage": 0.04},
        )
        node = {"id": "sg1", "type": "slippage_guard", "data": {"max_slippage_pct": 0.02}}
        result = handle_slippage_guard(node, {}, ctx)
        assert result["triggered"] is True
        assert result["last_slippage"] == 0.04

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(
            portfolio={"last_trade_slippage": 0.01},
        )
        node = {"id": "sg2", "type": "slippage_guard", "data": {"max_slippage_pct": 0.02}}
        result = handle_slippage_guard(node, {}, ctx)
        assert result["triggered"] is False


class TestMaxConsecutiveLosses:
    def test_triggers_on_streak(self):
        ctx = ExecutionContext(consecutive_losses=6)
        node = {"id": "mcl1", "type": "max_consecutive_losses", "data": {"max_streak": 5}}
        result = handle_max_consecutive_losses(node, {}, ctx)
        assert result["triggered"] is True
        assert result["consecutive_losses"] == 6

    def test_does_not_trigger_within_limit(self):
        ctx = ExecutionContext(consecutive_losses=3)
        node = {"id": "mcl2", "type": "max_consecutive_losses", "data": {"max_streak": 5}}
        result = handle_max_consecutive_losses(node, {}, ctx)
        assert result["triggered"] is False


class TestCooldownPeriod:
    def test_triggers_on_cooldown_threshold(self):
        ctx = ExecutionContext(consecutive_losses=4)
        node = {"id": "cp1", "type": "cooldown_period", "data": {"cooldown_trades": 3}}
        result = handle_cooldown_period(node, {}, ctx)
        assert result["triggered"] is True
        assert result["consecutive_losses"] == 4

    def test_does_not_trigger_below_threshold(self):
        ctx = ExecutionContext(consecutive_losses=1)
        node = {"id": "cp2", "type": "cooldown_period", "data": {"cooldown_trades": 3}}
        result = handle_cooldown_period(node, {}, ctx)
        assert result["triggered"] is False


class TestPositionTimeout:
    def test_triggers_on_oversized_hold(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "entry_time": old_time}],
            },
        )
        node = {"id": "pt1", "type": "position_timeout", "data": {"max_hold_seconds": 86400}}
        result = handle_position_timeout(node, {}, ctx)
        assert result["triggered"] is True
        assert len(result["positions"]) == 1

    def test_does_not_trigger_within_hold_time(self):
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [{"market_id": "m1", "entry_time": recent_time}],
            },
        )
        node = {"id": "pt2", "type": "position_timeout", "data": {"max_hold_seconds": 86400}}
        result = handle_position_timeout(node, {}, ctx)
        assert result["triggered"] is False


# ─── Regime/Market Structure Tests ────────────────────────────────────────────


class TestVolatilityRegimeCheck:
    def test_triggers_on_regime_mismatch(self):
        ctx = ExecutionContext(
            portfolio={"volatility_regime": "high"},
        )
        node = {"id": "vrc1", "type": "volatility_regime_check", "data": {"target_regime": "normal"}}
        result = handle_volatility_regime_check(node, {}, ctx)
        assert result["triggered"] is True
        assert result["current_regime"] == "high"

    def test_does_not_trigger_when_matching(self):
        ctx = ExecutionContext(
            portfolio={"volatility_regime": "normal"},
        )
        node = {"id": "vrc2", "type": "volatility_regime_check", "data": {"target_regime": "normal"}}
        result = handle_volatility_regime_check(node, {}, ctx)
        assert result["triggered"] is False


class TestCorrelationRegimeShift:
    def test_triggers_on_large_shift(self):
        ctx = ExecutionContext(
            portfolio={
                "current_avg_correlation": 0.8,
                "historical_avg_correlation": 0.3,
            },
        )
        node = {"id": "crs1", "type": "correlation_regime_shift", "data": {"correlation_spike_threshold": 0.3}}
        result = handle_correlation_regime_shift(node, {}, ctx)
        assert result["triggered"] is True
        assert result["correlation_shift"] > 0.3

    def test_does_not_trigger_on_small_shift(self):
        ctx = ExecutionContext(
            portfolio={
                "current_avg_correlation": 0.4,
                "historical_avg_correlation": 0.3,
            },
        )
        node = {"id": "crs2", "type": "correlation_regime_shift", "data": {"correlation_spike_threshold": 0.3}}
        result = handle_correlation_regime_shift(node, {}, ctx)
        assert result["triggered"] is False


class TestToxicityDetection:
    def test_triggers_on_high_vpin(self):
        ctx = ExecutionContext(vpin=0.85)
        node = {"id": "td1", "type": "toxicity_detection", "data": {"vpin_threshold": 0.7}}
        result = handle_toxicity_detection(node, {}, ctx)
        assert result["triggered"] is True
        assert result["vpin"] == 0.85

    def test_does_not_trigger_below_threshold(self):
        ctx = ExecutionContext(vpin=0.5)
        node = {"id": "td2", "type": "toxicity_detection", "data": {"vpin_threshold": 0.7}}
        result = handle_toxicity_detection(node, {}, ctx)
        assert result["triggered"] is False


class TestOrderFlowImbalance:
    def test_triggers_on_large_imbalance(self):
        ctx = ExecutionContext(ofi=0.45)
        node = {"id": "ofi1", "type": "order_flow_imbalance", "data": {"imbalance_threshold": 0.3}}
        result = handle_order_flow_imbalance(node, {}, ctx)
        assert result["triggered"] is True
        assert result["ofi"] == 0.45

    def test_does_not_trigger_within_threshold(self):
        ctx = ExecutionContext(ofi=0.15)
        node = {"id": "ofi2", "type": "order_flow_imbalance", "data": {"imbalance_threshold": 0.3}}
        result = handle_order_flow_imbalance(node, {}, ctx)
        assert result["triggered"] is False


# ─── Portfolio Construction Tests ─────────────────────────────────────────────


class TestRiskParityAllocation:
    def test_suggests_weights_inversely_proportional_to_vol(self):
        ctx = ExecutionContext(
            portfolio={
                "current_capital": 10000,
                "positions": [
                    {"market_id": "m1"},
                    {"market_id": "m2"},
                ],
                "position_returns": {
                    "m1": list(np.random.normal(0.001, 0.05, 100)),
                    "m2": list(np.random.normal(0.001, 0.02, 100)),
                },
            },
        )
        node = {"id": "rp1", "type": "risk_parity_allocation", "data": {}}
        result = handle_risk_parity_allocation(node, {}, ctx)
        assert "suggested_weights" in result
        assert len(result["suggested_weights"]) == 2
        assert abs(sum(result["suggested_weights"].values()) - 1.0) < 0.01

    def test_returns_empty_weights_with_no_positions(self):
        ctx = ExecutionContext(portfolio={"current_capital": 10000, "positions": []})
        node = {"id": "rp2", "type": "risk_parity_allocation", "data": {}}
        result = handle_risk_parity_allocation(node, {}, ctx)
        assert result["suggested_weights"] == {}


class TestMeanVarianceOptimization:
    def test_suggests_weights_based_on_risk_aversion(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={
                "position_returns": {
                    "m1": list(np.random.normal(0.002, 0.03, 100)),
                    "m2": list(np.random.normal(0.001, 0.05, 100)),
                },
            },
        )
        node = {"id": "mvo1", "type": "mean_variance_optimization", "data": {"risk_aversion": 1.0}}
        result = handle_mean_variance_optimization(node, {}, ctx)
        assert "suggested_weights" in result
        assert len(result["suggested_weights"]) == 2
        assert abs(sum(result["suggested_weights"].values()) - 1.0) < 0.01

    def test_returns_empty_with_no_data(self):
        ctx = ExecutionContext(portfolio={"position_returns": {}})
        node = {"id": "mvo2", "type": "mean_variance_optimization", "data": {"risk_aversion": 1.0}}
        result = handle_mean_variance_optimization(node, {}, ctx)
        assert result["suggested_weights"] == {}
        assert result["expected_return"] == 0


class TestHierarchicalRiskParity:
    def test_suggests_weights_by_inverse_volatility(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={
                "position_returns": {
                    "m1": list(np.random.normal(0.001, 0.04, 100)),
                    "m2": list(np.random.normal(0.001, 0.02, 100)),
                    "m3": list(np.random.normal(0.001, 0.06, 100)),
                },
            },
        )
        node = {"id": "hrp1", "type": "hierarchical_risk_parity", "data": {}}
        result = handle_hierarchical_risk_parity(node, {}, ctx)
        assert "suggested_weights" in result
        assert len(result["suggested_weights"]) == 3
        assert abs(sum(result["suggested_weights"].values()) - 1.0) < 0.01

    def test_returns_equal_weights_with_two_assets(self):
        np.random.seed(42)
        ctx = ExecutionContext(
            portfolio={
                "position_returns": {
                    "m1": list(np.random.normal(0.001, 0.03, 100)),
                    "m2": list(np.random.normal(0.001, 0.03, 100)),
                },
            },
        )
        node = {"id": "hrp2", "type": "hierarchical_risk_parity", "data": {}}
        result = handle_hierarchical_risk_parity(node, {}, ctx)
        assert "suggested_weights" in result
        assert len(result["suggested_weights"]) == 2
        weights = list(result["suggested_weights"].values())
        assert abs(weights[0] - 0.5) < 0.15
        assert abs(weights[1] - 0.5) < 0.15
