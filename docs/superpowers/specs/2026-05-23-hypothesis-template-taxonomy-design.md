# Hypothesis Template Taxonomy & Meta-Strategy Integration Design

## 1. Motivation

The current `HYPOTHESIS_TEMPLATES` system (5 static entries in both `autoresearch.py` and `genetic_programming.py`) is a bottleneck that constrains the entire autonomous research loop. Genetic programming mutates only threshold, operator, and feature — it never discovers new *classes* of strategy behavior. This means:

- **No exit management**: Every hypothesis is an entry signal. No take-profit, stop-loss, trailing stop, or time-based exit logic.
- **No position sizing**: No Kelly criterion, fixed fraction, volatility-adjusted, or confidence-weighted sizing.
- **No risk management**: No VaR limits, drawdown guards, correlation filters, or regime-triggered risk reduction.
- **No market microstructure**: No order book imbalance, queue position, fee-aware entry.
- **No cross-market arbitrage**: No divergence/correlation trades, funding rate arb, basis trades.
- **No alternative data**: No news sentiment, social volume, on-chain metrics, weather data.
- **No ML-based signals**: No transformer embeddings, gradient-boosted predictions, cluster-based regime detection.
- **No meta-strategy behaviors**: No pool composition rules, regime-adaptive switching, concurrency limits.

The gap: static templates mean the research loop discovers only which *parameter values* work, never which *kinds* of strategies work.

## 2. Two-Stage Pipeline Architecture (Meta-Strategy Integration)

Meta-strategies require a two-stage evaluation pipeline because they manage a pool of child strategies and produce *pool management decisions* (promote, demote, replace, reweight), not single trade signals.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 1: Portfolio Simulation                     │
│                                                                     │
│  Meta-strategy rules (pool mgmt, regime logic)                      │
│  simulate how a pool of child strategies would evolve over time,    │
│  producing:                                                         │
│    - Signal time series (when to promote/demote/replace)            │
│    - Pool composition snapshots                                     │
│    - Regime transition log                                          │
│                                                                     │
│  Output: PortfolioSignalSeries                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 2: DAG Backtest                             │
│                                                                     │
│  The signal series from Stage 1 is fed through the existing         │
│  GraphExecutor (DAG-based strategy execution) against market        │
│  history to produce trade-level metrics:                            │
│    - PnL, Sharpe, win rate, drawdown                                │
│    - VaR/CVaR (via Monte Carlo bootstrap)                           │
│    - Portfolio-level correlation, concentration                     │
│                                                                     │
│  Output: BacktestResult + MonteCarloResult                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NSGA-II Multi-Objective Scoring                   │
│                                                                     │
│  Combined objective vector (6+ dimensions):                         │
│  [pool_sharpe, pool_diversification, regime_stability,              │
│   market_sharpe, market_win_rate, -market_var_95,                   │
│   tabpfn_probability, hermes_approval]                              │
│                                                                     │
│  Pareto rank determines KEPT/WARN/REVERTED verdict.                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Meta-Strategy Hypothesis Classes

A meta-strategy hypothesis differs from a single-strategy hypothesis. It specifies:

```python
MetaStrategyHypothesis = {
    "pool_rules": {                          # How the pool is managed
        "promotion_threshold": float,        # Min score to promote child
        "demotion_threshold": float,         # Max score before demotion
        "max_active": int,                   # Max concurrently active
        "min_active": int,                   # Min always-active
        "replacement_interval_hours": int,   # How often to rotate
    },
    "regime_logic": {                        # Regime-adaptive behavior
        "regime_triggers": dict[str, str],   # regime -> action mapping
        "transition_smoothness": float,      # 0=instant, 1=gradual
        "hedge_on_regime_change": bool,
    },
    "confluence_config": {                   # Signal aggregation
        "min_votes": int,
        "vote_source": str,                  # "top_n" | "all" | "weighted"
        "staleness_hours": float,
    },
    "risk_limits": {                         # Pool-level risk
        "max_correlation": float,
        "max_concentration": float,
        "max_pool_var_95": float,
    },
    "scoring_weights": dict[str, float],     # How child strategies scored
}
```

### 2.2 Combined Objective Vector

The NSGA-II optimizer receives a 6+ element objective vector:

| Index | Objective | Source | Direction |
|-------|-----------|--------|-----------|
| 0 | `pool_sharpe` | Stage 1 portfolio sim | Maximize |
| 1 | `pool_diversification` | Stage 1 (1 - Herfindahl index) | Maximize |
| 2 | `regime_stability` | Stage 1 (inverse of regime switches) | Maximize |
| 3 | `market_sharpe` | Stage 2 DAG backtest | Maximize |
| 4 | `market_win_rate` | Stage 2 DAG backtest | Maximize |
| 5 | `-market_var_95` | Stage 2 Monte Carlo | Maximize (negate VaR) |
| 6 | `tabpfn_probability` | TabPFN pre-screening | Maximize |
| 7 | `hermes_approval` | Hermes critique (0 or 1) | Maximize |

Meta-strategy hypotheses use objectives 0-2 and 5-7.
Single-strategy hypotheses use objectives 3-7.

## 3. Comprehensive HYPOTHESIS_TEMPLATES Taxonomy

The full taxonomy covers 13 dimensions with 150+ pattern entries. Each entry is classified by `dimension`, `level` (entry/exit/sizing/risk), and `operand_type` (threshold/comparison/range/composite).

### 3.1 Schema Expansion

Current schema:
```python
HYPOTHESIS_TEMPLATES = [
    {
        "template": "Momentum breakout on {feature}",
        "params": {"feature": "odds_momentum_3h", "operator": "gt", "threshold_range": (0.55, 0.75)},
        "regime_affinity": ["trending"],
    },
]
```

Proposed expanded schema:
```python
HYPOTHESIS_TEMPLATES = [
    {
        "id": "momentum_breakout_1",
        "template": "Momentum breakout on {feature}",
        "dimension": "entry",              # One of 13 dimensions
        "level": "entry",                   # entry | exit | sizing | risk | regime | ...
        "params": {
            "feature": {
                "primary": "odds_momentum_3h",
                "alternatives": ["odds_momentum_1h", "odds_momentum_6h", "odds_momentum_24h"],
                "feature_type": "momentum",
            },
            "operator": "gt",
            "threshold_range": (0.55, 0.75),
            "operand_type": "threshold",   # threshold | comparison | range | composite | enumeration
            "comparison_feature": None,     # For comparison-type operands
        },
        "regime_affinity": ["trending"],
        "market_type_affinity": ["binary", "multi", "scalar"],
        "complexity": 1,                    # 1-5 scale for GP nesting
        "tags": ["momentum", "breakout", "trend_following"],
        "mutatable_params": ["threshold", "operator", "feature", "comparison_feature"],
        "crossover_compatible_with": ["entry"],  # Dimension list for valid crossover
    },
]
```

### 3.2 Full Pattern Catalog

Below are all 13 dimensions with their template patterns, organized by level and operand type. Each entry shows the `template` string, the default `operator` (`op`), `threshold_range` (`tr`), `feature` (`f`), and `regime_affinity` (`ra`). Templates marked with `{feature}` are parameterized.

#### Dimension 1: Entry - Momentum

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 1.1 | `Momentum breakout on {feature}` | odds_momentum_3h | gt | (0.55, 0.75) | trending |
| 1.2 | `Momentum divergence entry on {feature}` | odds_momentum_1h | gt | (0.50, 0.65) | trending, volatile |
| 1.3 | `Rate of change acceleration on {feature}` | odds_roc_6h | gt | (0.02, 0.08) | trending |
| 1.4 | `MACD crossover entry on {feature}` | macd_line | gt | (0.0, 0.01) | trending |
| 1.5 | `MACD histogram divergence on {feature}` | macd_histogram | lt | (-0.01, -0.001) | trending, ranging |
| 1.6 | `RSI momentum confirmation on {feature}` | rsi_14 | gt | (60, 75) | trending |
| 1.7 | `RSI oversold bounce on {feature}` | rsi_14 | lt | (25, 40) | ranging, volatile |
| 1.8 | `Stochastic crossover entry on {feature}` | stochastic_k | gt | (20, 30) | ranging |
| 1.9 | `ADX trend strength entry on {feature}` | adx_14 | gt | (25, 40) | trending |
| 1.10 | `Bollinger band momentum entry on {feature}` | bb_position | gt | (0.8, 1.0) | trending, volatile |
| 1.11 | `Price rate of change breakout on {feature}` | price_roc_12h | gt | (0.03, 0.10) | trending |
| 1.12 | `Elder impulse system entry on {feature}` | elder_impulse | gt | (0, 2) | trending, volatile |
| 1.13 | `Chande momentum oscillator entry on {feature}` | cmo_14 | gt | (50, 70) | trending |
| 1.14 | `Donchian channel breakout on {feature}` | donchian_position | gt | (0.9, 1.0) | trending, volatile |

#### Dimension 2: Entry - Mean Reversion

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 2.1 | `Mean reversion on {feature}` | odds_deviation | gt | (0.08, 0.2) | ranging, calm |
| 2.2 | `Bollinger band squeeze reversion on {feature}` | bb_width | lt | (0.01, 0.03) | calm, ranging |
| 2.3 | `RSI overbought reversal on {feature}` | rsi_14 | gt | (70, 85) | ranging |
| 2.4 | `RSI oversold reversal on {feature}` | rsi_14 | lt | (15, 30) | ranging |
| 2.5 | `Z-score extreme reversion on {feature}` | odds_zscore | lt | (-2.0, -1.5) | ranging, calm |
| 2.6 | `Moving average envelope reversion on {feature}` | ma_envelope_position | gt | (0.95, 1.05) | ranging |
| 2.7 | `Fibonacci retracement entry on {feature}` | fib_retracement | lt | (0.382, 0.5) | ranging, trending |
| 2.8 | `Keltner channel reversion on {feature}` | keltner_position | gt | (0.8, 1.0) | ranging |
| 2.9 | `Standard deviation reversion entry on {feature}` | odds_std_dev | gt | (1.5, 2.5) | ranging, calm |
| 2.10 | `Statistical arbitrage reversion on {feature}` | pair_zscore | lt | (-2.0, -1.5) | ranging |
| 2.11 | `Opening price deviation reversion on {feature}` | open_deviation | gt | (0.05, 0.15) | calm, ranging |
| 2.12 | `Volume-weighted average price reversion on {feature}` | vwap_deviation | lt | (-0.03, -0.01) | ranging |

#### Dimension 3: Entry - Volatility

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 3.1 | `Volatility contraction entry on {feature}` | volatility_20h | lt | (0.02, 0.06) | calm, ranging |
| 3.2 | `Volatility expansion breakout on {feature}` | volatility_20h | gt | (0.08, 0.15) | volatile |
| 3.3 | `ATR channel breakout on {feature}` | atr_14 | gt | (0.03, 0.08) | volatile, trending |
| 3.4 | `Bollinger band squeeze entry on {feature}` | bb_width | lt | (0.005, 0.015) | calm |
| 3.5 | `Volatility ratio entry on {feature}` | vol_ratio_10_30 | lt | (0.5, 0.8) | calm, ranging |
| 3.6 | `Implied volatility spike entry on {feature}` | iv_percentile | gt | (80, 95) | volatile |
| 3.7 | `Volatility mean reversion entry on {feature}` | vol_zscore | gt | (1.5, 2.5) | volatile, ranging |
| 3.8 | `Chaikin volatility entry on {feature}` | chaikin_vol | lt | (0.1, 0.3) | calm |
| 3.9 | `Volatility regime change entry on {feature}` | vol_regime_change | gt | (0.5, 0.8) | volatile |
| 3.10 | `Quiet before storm entry on {feature}` | vol_ratio_5_50 | lt | (0.3, 0.6) | calm |

#### Dimension 4: Entry - Volume & Liquidity

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 4.1 | `Volume spike confirmation on {feature}` | volume_spike_ratio | gt | (1.5, 3.0) | volatile, trending |
| 4.2 | `Volume confirmation of breakout on {feature}` | volume_trend | gt | (1.2, 2.0) | trending |
| 4.3 | `Volume divergence signal on {feature}` | volume_price_divergence | lt | (-1.0, -0.5) | ranging, volatile |
| 4.4 | `OBV breakout confirmation on {feature}` | obv_trend | gt | (0.3, 0.7) | trending |
| 4.5 | `Volume-weighted momentum entry on {feature}` | vw_momentum | gt | (0.55, 0.70) | trending |
| 4.6 | `Liquidity depth entry signal on {feature}` | liquidity_depth | gt | (50000, 200000) | calm, ranging |
| 4.7 | `Volume profile high-volume node entry on {feature}` | vp_hvn_position | lt | (0.1, 0.3) | ranging |
| 4.8 | `Volume profile low-volume node entry on {feature}` | vp_lvn_position | gt | (0.7, 0.9) | trending |
| 4.9 | `Accumulation/distribution entry on {feature}` | ad_line | gt | (0.2, 0.5) | trending |
| 4.10 | `Money flow index entry on {feature}` | mfi_14 | lt | (20, 40) | ranging, volatile |
| 4.11 | `Ease of movement entry on {feature}` | eom | gt | (0.1, 0.5) | trending |
| 4.12 | `Volume trend confirmation on {feature}` | volume_ma_ratio | gt | (1.3, 2.5) | trending, volatile |
| 4.13 | `Liquidity vacuum entry on {feature}` | order_book_slope | lt | (0.1, 0.3) | calm, ranging |

#### Dimension 5: Entry - Microstructure

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 5.1 | `Spread contraction scalp on {feature}` | spread_width | lt | (0.01, 0.04) | calm, ranging |
| 5.2 | `Bid-ask imbalance entry on {feature}` | bid_ask_imbalance | gt | (0.3, 0.7) | trending, volatile |
| 5.3 | `Order book depth ratio entry on {feature}` | order_book_ratio | gt | (1.5, 3.0) | trending |
| 5.4 | `Trade intensity entry on {feature}` | trade_intensity | gt | (0.7, 0.9) | volatile |
| 5.5 | `Quote intensity entry on {feature}` | quote_intensity | gt | (0.6, 0.8) | volatile, trending |
| 5.6 | `Microprice momentum entry on {feature}` | microprice | gt | (0.55, 0.65) | trending |
| 5.7 | `Queue position entry on {feature}` | queue_position | gt | (0.7, 0.9) | calm |
| 5.8 | `Order flow imbalance entry on {feature}` | ofi | gt | (0.2, 0.5) | trending, volatile |
| 5.9 | `Tick rule entry on {feature}` | tick_rule | gt | (0.3, 0.5) | trending |
| 5.10 | `Trade sign autocorrelation entry on {feature}` | trade_sign_ac | gt | (0.3, 0.6) | trending |

#### Dimension 6: Exit Management

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 6.1 | `Fixed take-profit exit on {feature}` | entry_multiple | gt | (1.5, 3.0) | trending |
| 6.2 | `Trailing stop exit on {feature}` | peak_drawdown | lt | (-0.05, -0.02) | trending |
| 6.3 | `Time-based exit on {feature}` | holding_period | gt | (24, 72) | calm, ranging |
| 6.4 | `Volatility-adjusted take-profit on {feature}` | vol_adjusted_target | gt | (1.5, 3.0) | volatile |
| 6.5 | `Moving average trailing exit on {feature}` | ma_cross | lt | (0, 0) | trending |
| 6.6 | `Parabolic SAR exit on {feature}` | psar_position | lt | (0, 0) | trending |
| 6.7 | `Chandelier exit on {feature}` | chandelier_position | lt | (0, 0) | trending |
| 6.8 | `Reward-to-risk ratio exit on {feature}` | rr_ratio | lt | (1.5, 2.5) | ranging |
| 6.9 | `Regime change exit on {feature}` | regime_change_prob | gt | (0.6, 0.8) | all |
| 6.10 | `Momentum exhaustion exit on {feature}` | momentum_decay | lt | (0.1, 0.3) | trending |
| 6.11 | `Volatility stop exit on {feature}` | atr_multiple | lt | (2.0, 3.0) | volatile |
| 6.12 | `Break-even exit after profit on {feature}` | breakeven_distance | lt | (0.01, 0.03) | ranging |
| 6.13 | `Partial profit taking at {feature}` | profit_tiers | gt | (3, 5) | trending |

#### Dimension 7: Position Sizing

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 7.1 | `Kelly criterion sizing on {feature}` | win_probability | gt | (0.5, 0.7) | all |
| 7.2 | `Fractional Kelly sizing on {feature}` | kelly_fraction | lt | (0.1, 0.5) | calm |
| 7.3 | `Fixed fraction sizing on {feature}` | risk_per_trade | lt | (0.01, 0.03) | all |
| 7.4 | `Volatility-adjusted sizing on {feature}` | inverse_vol | lt | (0.5, 2.0) | volatile |
| 7.5 | `Confidence-weighted sizing on {feature}` | signal_confidence | gt | (0.6, 0.9) | all |
| 7.6 | `VaR-limited sizing on {feature}` | var_per_trade | lt | (0.01, 0.03) | volatile |
| 7.7 | `Correlation-aware sizing on {feature}` | max_correlation | lt | (0.3, 0.6) | ranging |
| 7.8 | `Regime-adaptive sizing on {feature}` | regime_risk_mult | lt | (0.3, 0.8) | all |
| 7.9 | `Drawdown-based sizing reduction on {feature}` | current_drawdown | gt | (0.05, 0.15) | volatile |
| 7.10 | `Concentration limit sizing on {feature}` | herfindahl | lt | (0.2, 0.4) | all |
| 7.11 | `Equal risk contribution sizing on {feature}` | risk_parity_weight | gt | (0.05, 0.15) | ranging |
| 7.12 | `Expected value sizing on {feature}` | expected_value | gt | (0.02, 0.10) | all |

#### Dimension 8: Risk Management

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 8.1 | `Stop loss at {feature}` | stop_loss_pct | lt | (0.02, 0.08) | all |
| 8.2 | `Maximum drawdown limit on {feature}` | max_drawdown | lt | (0.1, 0.25) | all |
| 8.3 | `VaR-based position limit on {feature}` | portfolio_var_95 | lt | (0.02, 0.05) | volatile |
| 8.4 | `CVaR-based position limit on {feature}` | portfolio_cvar | lt | (0.03, 0.06) | volatile |
| 8.5 | `Correlation filter on {feature}` | pair_correlation | lt | (0.5, 0.7) | ranging |
| 8.6 | `Max concentration limit on {feature}` | concentration_ratio | lt | (0.2, 0.4) | all |
| 8.7 | `Regime-triggered risk reduction on {feature}` | regime_risk_score | gt | (0.6, 0.8) | volatile |
| 8.8 | `Max open positions on {feature}` | max_positions | lt | (3, 10) | all |
| 8.9 | `Max correlation to portfolio on {feature}` | portfolio_correlation | lt | (0.5, 0.7) | ranging |
| 8.10 | `Leverage limit on {feature}` | current_leverage | lt | (1.5, 3.0) | volatile |
| 8.11 | `Minimum Sharpe for allocation on {feature}` | strategy_sharpe | gt | (0.5, 1.0) | all |
| 8.12 | `Maximum slippage tolerance on {feature}` | expected_slippage | lt | (0.005, 0.02) | volatile, calm |
| 8.13 | `Gap risk protection on {feature}` | gap_probability | lt | (0.05, 0.15) | volatile |

#### Dimension 9: Regime Detection & Adaptation

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 9.1 | `Regime change entry signal on {feature}` | regime_change_signal | gt | (0.5, 0.7) | all |
| 9.2 | `Trending market filter on {feature}` | trend_strength | gt | (25, 35) | trending |
| 9.3 | `Ranging market filter on {feature}` | choppiness_index | gt | (50, 70) | ranging |
| 9.4 | `Volatile market filter on {feature}` | volatility_regime | gt | (0.6, 0.8) | volatile |
| 9.5 | `Hurst exponent trend filter on {feature}` | hurst_exponent | gt | (0.55, 0.75) | trending |
| 9.6 | `Hurst exponent mean-reversion filter on {feature}` | hurst_exponent | lt | (0.25, 0.45) | ranging |
| 9.7 | `Entropy regime detection on {feature}` | entropy_20h | lt | (0.3, 0.5) | ranging |
| 9.8 | `Hidden Markov model regime entry on {feature}` | hmm_regime | gt | (0.6, 0.8) | all |
| 9.9 | `Volatility clustering entry on {feature}` | vol_cluster | gt | (0.5, 0.7) | volatile |
| 9.10 | `Autocorrelation regime filter on {feature}` | autocorr_20h | lt | (0.3, 0.5) | ranging |
| 9.11 | `Seasonal pattern entry on {feature}` | seasonal_factor | gt | (0.55, 0.65) | ranging |
| 9.12 | `Time-of-day regime bias on {feature}` | tod_bias | gt | (0.55, 0.65) | all |

#### Dimension 10: Statistical Arbitrage

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 10.1 | `Pair trading z-score entry on {feature}` | pair_zscore | lt | (-2.0, -1.5) | ranging |
| 10.2 | `Cross-market divergence entry on {feature}` | cross_market_zscore | lt | (-2.0, -1.5) | ranging |
| 10.3 | `ETF premium discount entry on {feature}` | etf_premium | gt | (0.5, 1.0) | volatile |
| 10.4 | `Cointegration pair entry on {feature}` | coint_residual | lt | (-1.5, -1.0) | ranging |
| 10.5 | `Correlation breakdown entry on {feature}` | corr_breakdown | lt | (0.3, 0.5) | volatile |
| 10.6 | `Stochastic spread entry on {feature}` | spread_ou_residual | lt | (-1.5, -1.0) | ranging |
| 10.7 | `Kalman filter hedge ratio entry on {feature}` | kalman_spread | lt | (-2.0, -1.5) | ranging |
| 10.8 | `Rolling correlation divergence on {feature}` | rolling_corr_change | lt | (-0.3, -0.1) | volatile |
| 10.9 | `Cross-asset momentum spillover on {feature}` | spillover_zscore | gt | (1.5, 2.5) | trending |
| 10.10 | `Synthetic arbitrage entry on {feature}` | synthetic_mispricing | gt | (0.01, 0.03) | ranging |
| 10.11 | `Calendar spread entry on {feature}` | calendar_spread | lt | (-0.02, -0.01) | ranging |
| 10.12 | `Decay factor arbitrage on {feature}` | decay_arb_signal | gt | (0.015, 0.025) | ranging |

#### Dimension 11: Alternative Data Signals

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 11.1 | `News sentiment entry on {feature}` | news_sentiment | gt | (0.3, 0.7) | volatile, trending |
| 11.2 | `Social volume surge entry on {feature}` | social_volume_z | gt | (1.5, 3.0) | volatile |
| 11.3 | `News velocity entry on {feature}` | news_velocity | gt | (0.5, 0.8) | volatile |
| 11.4 | `Social sentiment divergence on {feature}` | social_sentiment_change | lt | (-0.3, -0.1) | ranging, volatile |
| 11.5 | `On-chain transaction volume entry on {feature}` | tx_volume_z | gt | (1.5, 2.5) | trending |
| 11.6 | `Whale wallet activity entry on {feature}` | whale_tx_count | gt | (1.5, 3.0) | trending |
| 11.7 | `Smart money flow entry on {feature}` | smart_money_ratio | gt | (1.2, 2.0) | trending |
| 11.8 | `Developer activity signal on {feature}` | dev_commit_velocity | gt | (0.5, 0.8) | trending |
| 11.9 | `Search trend divergence on {feature}` | search_trend_z | lt | (-1.5, -0.5) | ranging |
| 11.10 | `Influencer mention spike on {feature}` | influencer_mentions | gt | (2.0, 5.0) | volatile |
| 11.11 | `Regulatory news impact on {feature}` | regulatory_sentiment | lt | (-0.5, -0.2) | volatile |
| 11.12 | `Macroeconomic indicator entry on {feature}` | macro_indicator_z | gt | (1.0, 2.0) | trending |
| 11.13 | `Earnings surprise entry on {feature}` | earnings_surprise | gt | (0.5, 1.0) | trending |
| 11.14 | `Weather-based prediction entry on {feature}` | weather_anomaly | gt | (1.0, 2.0) | ranging |
| 11.15 | `Polling data shift entry on {feature}` | polling_momentum | gt | (0.03, 0.08) | trending |
| 11.16 | `Market sentiment index on {feature}` | sentiment_index | lt | (0.2, 0.4) | ranging |
| 11.17 | `Narrative shift detection on {feature}` | narrative_shift_score | gt | (0.6, 0.8) | volatile |
| 11.18 | `FOMC/event probability impact on {feature}` | event_prob_change | gt | (0.05, 0.15) | volatile |

#### Dimension 12: Machine Learning Signals

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 12.1 | `Transformer embedding similarity entry on {feature}` | embedding_similarity | gt | (0.6, 0.8) | all |
| 12.2 | `Gradient boosted prediction entry on {feature}` | xgb_prediction | gt | (0.55, 0.75) | all |
| 12.3 | `Clustering regime label entry on {feature}` | cluster_label | gt | (0.5, 0.7) | all |
| 12.4 | `TabPFN meta-learning entry on {feature}` | tabpfn_prob | gt | (0.55, 0.80) | all |
| 12.5 | `Anomaly detection reversal on {feature}` | anomaly_score | gt | (1.5, 3.0) | volatile |
| 12.6 | `LSTM prediction divergence on {feature}` | lstm_divergence | lt | (-0.05, -0.02) | trending |
| 12.7 | `Autoencoder reconstruction error entry on {feature}` | ae_reconstruction_error | gt | (1.5, 3.0) | volatile |
| 12.8 | `Random forest feature importance entry on {feature}` | rf_importance | gt | (0.6, 0.8) | all |
| 12.9 | `KNN regime proximity entry on {feature}` | knn_regime_proximity | gt | (0.7, 0.9) | ranging |
| 12.10 | `Bayesian probability update entry on {feature}` | bayesian_prob | gt | (0.55, 0.70) | all |
| 12.11 | `Markov chain state entry on {feature}` | markov_state_prob | gt | (0.5, 0.7) | ranging |
| 12.12 | `Ensemble confidence entry on {feature}` | ensemble_confidence | gt | (0.6, 0.8) | all |
| 12.13 | `Attention-weighted signal on {feature}` | attention_weight | gt | (0.6, 0.8) | all |
| 12.14 | `Online learning prediction drift on {feature}` | online_prediction_drift | gt | (0.05, 0.15) | volatile |

#### Dimension 13: Meta-Strategy & Pool Management

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 13.1 | `Top performer promotion on {feature}` | child_sharpe_rank | lt | (2, 5) | all |
| 13.2 | `Underperformer demotion on {feature}` | child_score_decay | gt | (0.3, 0.5) | all |
| 13.3 | `Diversification-based replacement on {feature}` | pool_correlation | gt | (0.7, 0.8) | ranging |
| 13.4 | `Regime-adaptive pool rotation on {feature}` | regime_change_signal | gt | (0.5, 0.7) | all |
| 13.5 | `Performance-based pool reweighting on {feature}` | weight_decay_factor | lt | (0.05, 0.2) | all |
| 13.6 | `Confluence-weighted aggregation on {feature}` | min_vote_threshold | lt | (3, 6) | all |
| 13.7 | `Probation-based strategy filtering on {feature}` | probation_win_rate | gt | (0.45, 0.55) | all |
| 13.8 | `Confidence-interval based promotion on {feature}` | score_ci_lower | gt | (0.5, 0.7) | all |
| 13.9 | `Stale strategy replacement on {feature}` | days_since_update | gt | (7, 30) | all |
| 13.10 | `Risk-budget rebalancing on {feature}` | risk_budget_deviation | gt | (0.2, 0.4) | all |
| 13.11 | `Correlation regime filter on {feature}` | avg_pair_correlation | gt | (0.5, 0.7) | ranging |
| 13.12 | `Max drawdown pool protection on {feature}` | pool_drawdown | gt | (0.1, 0.2) | volatile |
| 13.13 | `Adaptive min active strategies on {feature}` | market_opportunity | gt | (0.5, 0.7) | all |
| 13.14 | `Strategy lifecycle replacement on {feature}` | strategy_age_days | gt | (14, 60) | all |
| 13.15 | `Sharpe decay rotation on {feature}` | sharpe_decay_rate | lt | (0.05, 0.15) | all |

#### Dimension 14: Hybrid / Composite Signals

| # | Template | f | op | tr | ra |
|---|----------|---|----|----|----|
| 14.1 | `Momentum + volume confirmation on {feature}` | momentum_volume_composite | gt | (0.6, 0.8) | trending |
| 14.2 | `Reversion + volatility filter on {feature}` | reversion_vol_composite | lt | (0.3, 0.5) | ranging |
| 14.3 | `Breakout + volume surge on {feature}` | breakout_volume_composite | gt | (0.6, 0.8) | volatile |
| 14.4 | `Trend + sentiment alignment on {feature}` | trend_sentiment_composite | gt | (0.6, 0.8) | trending |
| 14.5 | `Mean reversion + sentiment extreme on {feature}` | reversion_sentiment_composite | lt | (0.3, 0.5) | ranging |
| 14.6 | `Volatility contraction + low-volume on {feature}` | vol_liquidity_composite | lt | (0.3, 0.5) | calm |
| 14.7 | `Microstructure + momentum combo on {feature}` | micro_momentum_composite | gt | (0.6, 0.8) | trending |
| 14.8 | `Regime + risk-adjusted position on {feature}` | regime_risk_composite | gt | (0.5, 0.7) | all |
| 14.9 | `Multi-feature ensemble entry on {feature}` | ensemble_vote_count | gt | (3, 7) | all |
| 14.10 | `ML prediction + market structure on {feature}` | ml_structure_composite | gt | (0.6, 0.8) | all |

## 4. Template Discovery: From Static to Dynamic

The expanded taxonomy enables a new autonomous template discovery loop. The GP can now:

### 4.1 Template Mutation

When a `HypothesisIndividual` has `template` from Dimension 1 (momentum entry), mutation can:
- **Same-dimension swap**: Replace with a different Dimension 1 template (e.g., MACD crossover instead of RSI momentum)
- **Cross-dimension import**: Replace with a template from a compatible dimension (e.g., swap entry template for exit template with same underlying logic)
- **Dimension upgrade**: Combine entry + exit into a composite (Dimension 14)
- **Dimension downgrade**: Split composite into atomic components

### 4.2 Template Crossover

Valid crossover must respect dimension compatibility:

```python
CROSSOVER_COMPATIBILITY = {
    "entry": ["entry", "hybrid"],          # entry × entry = entry, entry × exit = hybrid
    "exit": ["exit", "hybrid"],
    "sizing": ["sizing", "risk"],
    "risk": ["risk", "sizing"],
    "regime": ["regime", "entry", "exit"], # regime info feeds entry/exit
    "microstructure": ["microstructure", "entry"],
    "stat_arb": ["stat_arb", "entry", "exit"],
    "alt_data": ["alt_data", "entry", "exit"],
    "ml": ["ml", "entry", "exit", "regime"],
    "meta": ["meta"],
    "hybrid": ["hybrid", "entry", "exit"],
}
```

### 4.3 Hermes-Driven Template Creation

When the LLM (Hermes) proposes a hypothesis the system hasn't seen before, it should create a new template entry:

```
Hermes suggests: "Combine spread contraction with volume spike for low-liquidity scalp"

→ Parse into template: "Spread contraction + volume spike scalp on {feature}"
→ Assign dimension: "hybrid"
→ Assign regime_affinity: ["calm"]
→ Add to HYPOTHESIS_TEMPLATES
→ Tag with ["microstructure", "volume", "scalp"]
→ Track performance in template_stats database
```

```python
async def _hermes_create_template(self, hermes_suggestion: str) -> dict | None:
    """Parse Hermes LLM suggestion into a new HYPOTHESIS_TEMPLATES entry."""
    prompt = f"""
    Convert this trading hypothesis into a structured template entry:

    Hypothesis: "{hermes_suggestion}"

    Return JSON with:
    - template: str (use {{feature}} placeholder)
    - dimension: str (one of: entry, exit, sizing, risk, regime, stat_arb,
                       microstructure, alt_data, ml, meta, hybrid)
    - level: str
    - default_operator: "gt" or "lt"
    - threshold_range: [low, high]
    - regime_affinity: list[str]
    - tags: list[str]
    """
    response = await self.hermes_plugin.process_message(prompt, ...)
    return self._parse_template_json(response)
```

### 4.4 Template Performance Tracking

New table to track which templates actually work:

```sql
CREATE TABLE template_stats (
    template_id VARCHAR(64) PRIMARY KEY,
    dimension VARCHAR(32),
    n_trials INT DEFAULT 0,
    n_kept INT DEFAULT 0,
    n_warn INT DEFAULT 0,
    avg_composite_score FLOAT DEFAULT 0.0,
    avg_sharpe FLOAT DEFAULT 0.0,
    avg_win_rate FLOAT DEFAULT 0.0,
    best_regime VARCHAR(16),
    worst_regime VARCHAR(16),
    created_at TIMESTAMP DEFAULT NOW(),
    last_tested_at TIMESTAMP
);
```

This lets the GP bias selection toward templates that historically perform well in the current regime.

## 5. Genetic Programming Enhancements

### 5.1 New GP Operators

| Operator | Current | Proposed |
|----------|---------|----------|
| **Threshold mutation** | ±0.05, clamped | Variable step: ±0.01 for fine, ±0.2 for coarse |
| **Operator flip** | 30% chance | Regime-adaptive: higher flip rate in ranging regimes |
| **Feature swap** | 20% chance, random top feature | Feature importance-weighted selection |
| **Template swap** | 10% chance, random template | Dimension-compatible swap with template_stats bias |
| **Dimension crossover** | None | Cross-entire-dimension between individuals |
| **Template creation** | None | Hermes-driven dynamic template generation |

### 5.2 Dynamic Feature Space

The `feature` field in each template is currently limited to 3-4 hardcoded features. The enhanced system pulls from a live feature registry:

```python
LIVE_FEATURES = {
    # Existing features
    "odds": {"type": "scalar", "range": (0, 1)},
    "odds_momentum_3h": {"type": "momentum", "range": (-1, 1)},
    "odds_deviation": {"type": "deviation", "range": (0, 1)},
    "volatility_20h": {"type": "volatility", "range": (0, 1)},
    "volume_spike_ratio": {"type": "ratio", "range": (0, 10)},
    "spread_width": {"type": "microstructure", "range": (0, 1)},

    # New microstructure features
    "bid_ask_imbalance": {"type": "microstructure", "range": (-1, 1)},
    "order_book_ratio": {"type": "microstructure", "range": (0, 5)},
    "trade_intensity": {"type": "activity", "range": (0, 1)},
    "microprice": {"type": "microstructure", "range": (0, 1)},
    "queue_position": {"type": "microstructure", "range": (0, 1)},
    "ofi": {"type": "order_flow", "range": (-1, 1)},

    # New statistical features
    "odds_zscore": {"type": "standardized", "range": (-5, 5)},
    "pair_zscore": {"type": "standardized", "range": (-5, 5)},
    "coint_residual": {"type": "residual", "range": (-3, 3)},
    "cross_market_zscore": {"type": "standardized", "range": (-5, 5)},

    # New regime features
    "regime_change_signal": {"type": "probability", "range": (0, 1)},
    "trend_strength": {"type": "adx", "range": (0, 100)},
    "choppiness_index": {"type": "index", "range": (0, 100)},
    "hurst_exponent": {"type": "exponent", "range": (0, 1)},
    "entropy_20h": {"type": "entropy", "range": (0, 1)},
    "hmm_regime": {"type": "probability", "range": (0, 1)},

    # New alt-data features
    "news_sentiment": {"type": "sentiment", "range": (-1, 1)},
    "social_volume_z": {"type": "zscore", "range": (-3, 3)},
    "news_velocity": {"type": "rate", "range": (0, 5)},

    # New ML features
    "embedding_similarity": {"type": "similarity", "range": (0, 1)},
    "xgb_prediction": {"type": "probability", "range": (0, 1)},
    "anomaly_score": {"type": "score", "range": (0, 5)},
    "ensemble_confidence": {"type": "confidence", "range": (0, 1)},

    # Meta-strategy features
    "child_sharpe_rank": {"type": "rank", "range": (1, 20)},
    "pool_correlation": {"type": "correlation", "range": (-1, 1)},
    "pool_drawdown": {"type": "drawdown", "range": (0, 1)},
    "strategy_age_days": {"type": "duration", "range": (0, 365)},
}
```

Each template's `params.feature.alternatives` is dynamically populated from `LIVE_FEATURES` filtered by `feature_type` compatibility. The GP can swap a template's feature to any alternative of a compatible type.

## 6. Gap Analysis: What's Missing vs. Original Autoresearch

The original karpathy/autoresearch has a `program.md` mechanism — a human-editable directive file that tells the LLM what to optimize (e.g., "minimize val_bpb on a transformer"). The LLM can also *modify* program.md when it discovers the problem statement was wrong. This gives the user direction over what the research loop works on.

Our pi-autoresearch has **none of this**. Key gaps:

| Feature | Original autoresearch | Our pi-autoresearch |
|---------|----------------------|---------------------|
| User direction file (`program.md`) | Human writes natural-language goals in `program.md` | No equivalent — only accepts structured `climate`, `feature_importance`, `preset` params |
| LLM can modify direction | LLM can rewrite `program.md` when constraints are wrong | Not possible — no direction file exists |
| Unconstrained hypothesis space | LLM generates any idea by editing `train.py` directly | All hypotheses must match a HYPOTHESIS_TEMPLATES entry |
| Novelties feed back into system | LLM discovers novel approaches by modifying code | GP mutates template parameters but never discovers new template *classes* |
| Reproducibility by code commit | Each experiment is a git commit of actual code changes | Experiments write JSON files — no code-level reproducibility |

## 7. Hypothesis Generation Modes & User Direction

The current system has exactly one mode: constrained template sampling. We introduce three explicit user-selectable modes to cover the full spectrum from beginner-friendly to expert-unconstrained.

### 7.1 Three-Mode Selector

```python
class HypothesisMode(str, enum.Enum):
    CONSTRAINED_ALL = "constrained_all"           # All 150+ templates in catalog
    CONSTRAINED_SELECTED = "constrained_selected"  # User picks a subset
    UNCONSTRAINED = "unconstrained"                # LLM generates free-form strategies
```

**Mode switching behavior:**
- Each mode maintains a separate GP population. Switching modes resets the evolution history (the old population is stored for comparison but not mixed).
- When switching away from `unconstrained`, the top 3 KEPT strategies can optionally be extracted into new template entries via `_hermes_create_template()`.
- Sessions are forked on mode switch — the user can toggle between sessions to compare results.

#### 7.1.1 CONSTRAINED_ALL — All Templates

The full 150+ template catalog is active. The GP selects from the pool with regime-aware pre-filtering.

- **Staged template introduction**: GP starts with a curated 20-template starter pack. Each iteration, 5 more templates are introduced until the full catalog is reached. This prevents the GP from being overwhelmed in early generations.
- **Regime pre-filter**: Before GP selection, templates are filtered to match the current market regime. At any given time the effective pool is ~30-50 templates, not 150.
- **Adaptive generation count**: If composite_score std across the population remains high after default generations, more generations are run automatically.

#### 7.1.2 CONSTRAINED_SELECTED — User-Picked Templates

The user manually selects which templates to include in the GP pool.

- **Regime compatibility warning**: When the user selects templates, the system shows which regime they favor vs. the current market regime. Non-blocking — user can proceed informed.
- **Template completion suggestion**: If the user picks only entry templates, the system suggests adding an exit template. "Strategies with entry AND exit rules perform 40% better on average."
- **Auto-promotion to CONSTRAINED_ALL**: After 10+ iteration cycles, if the selected subset consistently underperforms the hypothetical full-catalog baseline (measured by avg_composite_score), the system suggests switching.
- **Selection UI**: Category browser by dimension + regime_affinity, with search and per-template performance preview (from template_stats).

#### 7.1.3 UNCONSTRAINED — LLM Generates Anything

No templates at all. The LLM receives market context (`climate`, `feature_importance`, market snapshot) and generates complete strategies as structured JSON.

- **Structured output schema**: The LLM must output strategies in a normalized format (`{entry_trigger, exit_condition, sizing_rule, risk_limit}`) so they can be evaluated through the standard Monte Carlo → NSGA-II pipeline.
- **LLM-as-GP**: Instead of template-based mutation/crossover, the LLM is used as the mutation operator. Prompts include: "Here are the top 3 strategies from last iteration. Generate 5 variations: change one parameter, combine two strategies, or try something completely different."
- **Template extraction on KEPT**: When an unconstrained strategy scores KEPT, it's extracted back into a template entry and added to the catalog for future GP evolution.

### 7.2 User Direction (program.md)

A new optional feature inspired directly by karpathy/autoresearch's `program.md`.

**Data model:**
```python
class ResearchSession(Base):
    __tablename__ = "research_sessions"
    # Existing fields...
    program_prompt: str | None = None    # Optional user direction text
    program_modifiable: bool = False      # Toggle: can LLM modify program_prompt?
    hypothesis_mode: str = "constrained_all"  # One of the three modes
```

**Behavior:**

1. **Optional**: If `program_prompt` is None, behavior is as today — no user direction, system generates autonomously.
2. **Set by user**: The user writes a natural-language directive (e.g., "Focus on volatility breakout strategies with tight stop-losses").
3. **LLM can modify (toggle)**: If `program_modifiable=True`, the LLM/Hermes can rewrite `program_prompt` when it determines the constraints are incorrect or suboptimal. The original is preserved in an audit log.
4. **Constrained mode interaction**: If `program_prompt` says "focus on momentum" in `CONSTRAINED_ALL` mode, the template list is filtered to only momentum-dimension entries. Even if momentum underperforms, the system respects the user's direction and reports honest results.
5. **Unconstrained mode interaction**: If `program_prompt` is set in `UNCONSTRAINED` mode, it's passed as the system prompt to the LLM for hypothesis generation.

**Audit log:**
```sql
CREATE TABLE program_prompt_audit (
    id UUID PRIMARY KEY,
    session_id VARCHAR(64) REFERENCES research_sessions(id),
    prompt_text TEXT NOT NULL,
    was_modified_by_llm BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Analytics insight**: After each iteration, the system shows "Your constraint cost you X Sharpe vs. the unconstrained alternative" so the user can see the impact of their direction.

### 7.3 Beginner Default Configuration

The recommended beginner default is `CONSTRAINED_ALL` with the **curated starter pack** (~20 templates), not the full 150+ catalog.

**Starter pack composition:**
| Count | Dimension | Templates |
|-------|-----------|-----------|
| 3 | Momentum entry | Breakout, MACD crossover, ADX confirmation |
| 3 | Mean reversion entry | Z-score, RSI oversold, Bollinger squeeze |
| 2 | Volatility entry | Contraction, expansion breakout |
| 1 | Volume entry | Volume spike confirmation |
| 2 | Exit management | Fixed take-profit, trailing stop |
| 1 | Position sizing | Kelly criterion |
| 1 | Risk management | Stop-loss |
| 2 | Regime detection | Trend strength, choppiness index |
| 1 | Statistical arbitrage | Pair trading z-score |
| 2 | Alternative data | News sentiment, social volume surge |
| 2 | Hybrid | Momentum+volume, reversion+volatility |

This gives fast GP convergence (visible improvement within 5-10 iterations) while demonstrating diversity. The full 150+ catalog toggle is available in Settings/Advanced mode.

## 8. Tradeoff Analysis & Practical Solutions

### 8.1 Unconstrained LLM Mode — Practical Fixes

#### Winner's Curse Problem

The LLM occasionally proposes brilliant novel strategies but mostly produces garbage. Template quick-rejection via TabPFN can't pre-screen free-text descriptions.

**Fixes:**

1. **Structured LLM output schema**: Force the LLM to output strategies in the same format as template hypotheses — a normalized JSON shape: `{feature, operator, threshold, entry_logic, exit_logic, sizing}`. This lets TabPFN quick-rejection work on the feature vector. The LLM fills in values instead of sampling from templates; the same evaluation pipeline runs unchanged.

2. **Two-pass LLM**: First pass generates 10+ raw strategy ideas. Second pass scores/critiques them itself to pick the top 3 for backtesting. The LLM acts as its own pre-filter before hitting the expensive Monte Carlo step. This filters obvious garbage before it wastes compute.

3. **Hybrid guard**: Run unconstrained strategies through a cheap heuristic filter before TabPFN: must specify entry trigger, must specify exit condition, sizing must be between 0-100%. Reject anything that doesn't parse.

#### Reproducibility Collapse

LLM-generated strategies are conversation transcripts — different model versions, temperatures, and prompts produce different strategies. Templates guarantee full reproducibility.

**Fixes:**

1. **Freeze LLM config in session**: Store the exact model, temperature, top_p, and system prompt used for each unconstrained iteration. All strategies from that session are stored with their generation context metadata.

2. **Canonical strategy encoding**: Force unconstrained output into a normalized JSON shape that can be hashed. Two strategies are "the same" if their canonical JSON hashes match, regardless of how the LLM phrased them.

3. **Version-pinned LLM inference**: Use a specific pinned model version for unconstrained generation. If the model updates, start a new session — don't mix generations from different model versions in the same evolutionary lineage.

#### GP Incompatibility

The current GP operators (`mutation()`, `crossover()`) assume `{template, feature, operator, threshold}` shape. Unconstrained strategies don't fit this.

**Fixes:**

1. **LLM-as-GP**: Don't try to mix unconstrained strategies with template-based GP at all. Use the LLM itself as the mutation operator: "Here are the top 3 strategies from last iteration. Generate 5 variations — change one parameter, combine two, or try something completely different." This gives evolution-like behavior without needing structured mutation operators.

2. **Separate unconstrained population**: Maintain a separate `UnconstrainedPopulation` that stores full strategy specs. A parallel mutation/crossover strategy using LLM prompts for "mutation" and strategy field mixing for "crossover."

3. **Template extraction on KEPT** (bridge solution): When an unconstrained strategy scores KEPT, extract its essence into a new template entry. Parse the successful strategy → identify which fields drive performance → generate a template description → add to the DB-backed template pool. The GP can then evolve this extracted template in future iterations. This bridges unconstrained exploration with GP exploitation.

### 8.2 Autonomous Template Creation — Practical Fixes

#### Template Explosion

Each LLM suggestion adds a new template entry. After 100 iterations the pool may have 500+ templates, degrading GP tournament selection.

**Fixes:**

1. **Soft pool cap with LRU eviction**: Max 200 templates. On creation, if at cap, evict the template with the lowest `n_trials * avg_composite_score` (least-performing, least-tested).

2. **Regime-aware archival**: Don't delete templates — archive them. A template that underperforms in trending regime might excel in ranging. Before pruning, check if the template has been tested in >2 regimes. If not, keep it.

3. **Trial quota**: A template gets 10 trials minimum before pruning eligibility. Ensures statistical significance before discard decisions.

4. **Per-iteration template budget**: The GP selects from a random subset of the pool per generation (e.g., 30 random templates out of 200). This reduces tournament selection degradation without needing to prune.

#### Deduplication Is Hard

Two templates with different descriptions might be semantically identical.

**Fixes:**

1. **Embedding-based dedup**: Use a lightweight embedding model (sentence-transformers or the LLM itself) to compute cosine similarity between new template descriptions and existing ones. Similarity > 0.85 → flag as duplicate and reject or merge.

2. **Template signature hash**: Hash on `{dimension, feature_type, operator, operand_type}`. If a new template has the same structural signature as an existing one, it's a duplicate regardless of description wording.

3. **LLM dedup at creation time**: When the LLM proposes a new template, also prompt it: "Given the existing templates [list], is this proposal novel or already covered?" Reject if redundant.

#### Feature Availability Validation

The LLM says "use spread_width" but the feature doesn't exist in LIVE_FEATURES.

**Fixes:**

1. **LLM guided by feature catalog**: Before asking the LLM to propose templates, give it the LIVE_FEATURES catalog. Constrain it to choose features from known entries.

2. **Fallback feature on validation failure**: If the LLM's chosen feature doesn't exist, auto-map to the closest known feature by type (e.g., "bid_ask_spread_1m" → "spread_width") with a warning logged.

3. **Feature creation pathway**: If the LLM proposes a feature not in LIVE_FEATURES but it's plausible (e.g., a derived ratio the system could compute), create a derived feature entry and mark it as "pending data source implementation." The template is held in a "pending" state until the feature pipeline is wired.

### 8.3 Custom User Templates — Practical Fixes

#### Schema Complexity

The expanded template schema has 15+ fields. A full form overwhelms non-technical users.

**Fixes:**

1. **Two-tier form**: Simple mode = template description string + dropdown for dimension. Auto-populate sensible defaults for everything else (operator=gt, threshold_range=(0.4, 0.7), regime_affinity=all). Advanced mode = full schema editor with all fields visible.

2. **Template wizard**: Step-through guided creation: Step 1: "What kind of strategy?" (entry/exit/sizing/risk). Step 2: "What pattern?" (momentum/reversion/volatility/etc) — auto-fills feature and operator defaults. Step 3: "Adjust threshold range" with slider. Step 4: Review summary.

3. **Default from similar**: When the user starts typing a template description, search existing templates and offer "Start from this template" with explanation of defaults.

#### Support Burden

"My custom template isn't working" — is it the concept, the threshold range, the feature, or the GP?

**Fixes:**

1. **Template analytics dashboard**: Per-template view showing n_trials, avg_sharpe, best_regime, worst_regime, comparison to pool average. "Your template is performing 20% below the pool average in trending regimes."

2. **Template health checks**: Before adding a template, run 3 quick validations: (1) feature exists in LIVE_FEATURES, (2) threshold_range is within feature's valid range, (3) regime_affinity entries are valid enum values. Fail fast with specific error messages and fix suggestions.

3. **Auto-adjust suggestions**: After 10 trials with avg_composite_score below 0.3, suggest parameter adjustments: "Try widening the threshold range or changing the operator."

### 8.4 Three-Mode Selector — Practical Fixes

#### Mode Switching Is Treacherous

Switching modes resets evolution history. The GP population from one mode is incompatible with another.

**Fixes:**

1. **Separate GP populations per mode**: A mode switch resets the GP population. The system explains: "Switching modes will reset your evolution history. You can compare results across modes in the analytics view." All past mode populations are stored for comparison.

2. **Mode migration option**: Offer "migrate top 3 performers from previous mode" when switching. Best strategies are extracted and converted to the new mode's representation (unconstrained → template extraction).

3. **Fork sessions on mode switch**: Each mode switch creates a forked session. The user can toggle between sessions to compare results. Clean data model — each session has `{mode, population, hypothesis_mode}`.

#### Convergence Problems Per Mode

| Mode | Problem | Fix |
|------|---------|-----|
| `CONSTRAINED_ALL` (150+ templates) | GP needs more generations; beginners see poor early results | Staged template introduction (20 → +5 per iteration); regime pre-filter keeps effective pool ~30-50; adaptive generation count when convergence is slow |
| `UNCONSTRAINED` | No evolution — each iteration starts from zero | LLM seeding with past KEPT strategies; partial constraint injection (LLM must output 4-field structured spec); importance sampling from prior successful iterations |
| `CONSTRAINED_SELECTED` | User picks templates incompatible with market regime | Regime compatibility warning; template completion suggestion (e.g., "you picked entries but no exits"); auto-suggest full catalog after consistent underperformance |

### 8.5 Constraint Leakage — The Hardest Architectural Problem

The core issue: three parallel hypothesis representations with incompatible shapes.

| Representation | Shape | GP Operators Work? |
|---------------|-------|-------------------|
| Template hypothesis | `{template, feature, operator, threshold}` | Yes — mutation/crossover on fields |
| LLM unconstrained | `{entry_trigger, exit_condition, sizing, risk}` (free-text fields) | No — different field set |
| Custom user template | Same as template hypothesis | Yes |

The downstream pipeline (Monte Carlo → NSGA-II → verdict) doesn't care about shape — it just needs a backtestable config. The constraint is in the GP operators. Three solutions from simplest to most comprehensive:

#### Fix A (Recommended): Unify Behind StrategySpec

**Create `StrategySpec` as the universal container:**

```python
@dataclass
class StrategySpec:
    entry: EntryRule          # {type, feature, operator, threshold}
    exit: ExitRule            # {type, param_value}
    sizing: SizingRule        # {type, value}
    risk: RiskRule            # {type, limit}

    source: str               # "template" | "llm_unconstrained" | "user_custom"
    template_id: str | None   # If derived from a template
    generation: int
    parent_ids: list[str]     # GP lineage tracking
```

**All evaluation pipeline operates on `StrategySpec` only.** The hypothesis generation layer produces `StrategySpec`s from whatever source. Three generators, one unified output format:

```
TemplateHypothesisGenerator  → populates entry/exit/sizing/risk from template defaults
LLMHypothesisGenerator       → LLM fills all 4 fields as structured JSON
UserCustomGenerator          → user's template populates the fields
```

**GP operators work on StrategySpec fields, not template strings:**

```python
def mutate_strategy(spec: StrategySpec) -> StrategySpec:
    if random() < 0.3:
        spec.entry.operator = flip(spec.entry.operator)
    if random() < 0.2:
        spec.sizing.value *= random.uniform(0.8, 1.2)
    return spec
```

**Single unified population. Single GP. Single evaluation pipeline.** A StrategySpec from a template can crossover with one from the LLM — crossover operates on field swaps, not template strings. The `source` field is metadata only — never used for routing.

#### Fix B: LLM-as-Mutation-Operator (Alternative)

If unification is too complex, don't fight the representation difference. **Let the LLM be the mutation operator for unconstrained mode**, not the GP:

```
LLM generates StrategySpec_A → Monte Carlo → scores 1.5
LLM generates StrategySpec_B → Monte Carlo → scores 0.8
LLM prompted: "Here is A (score 1.5) and B (score 0.8). 
              Generate C by mutating A's exit rule."
```

The LLM both generates and evolves unconstrained strategies. No GP operators needed for this track. Template-based strategies still use the standard GP. Two parallel tracks, never mixed.

**Downside**: Expensive LLM calls per mutation. Only viable as a premium high-effort mode.

#### Fix C: Template Extraction Bridge (Recommended as Phase 2 enhancement to Fix A)

After Fix A is operational, add:

**On KEPT from any source → auto-create template from the StrategySpec:**

1. Parse the successful `StrategySpec` → identify which fields drive performance (via ablation: remove each field and re-evaluate)
2. Generate a template description: "LLM-discovered: volume-confirmed momentum entry with trailing exit"
3. Add to the template_stats-backed template pool
4. The GP can now evolve this extracted template in future iterations

This bridges both worlds: unconstrained mode explores novel spaces, but all discoveries get captured back into the GP-evolvable template pool for cheap iteration.

#### Recommended Architecture Summary

| Component | Template Mode | Unconstrained Mode |
|-----------|---------------|-------------------|
| Generator | Samples template, fills StrategySpec | LLM fills StrategySpec fields as structured JSON |
| GP Operators | mutate/crossover on entry, exit, sizing, risk fields | Same operators on same StrategySpec fields |
| Evaluation | Monte Carlo → NSGA-II → verdict | Same pipeline |
| Persistence | StrategySpec + template_id | StrategySpec + full LLM prompt stored |
| Template feedback | template_stats tracking | Template extraction on KEPT |

## 9. Updated Implementation Plan

### Phase 1: Schema & Data Layer (Estimated: 3-4 sessions)

1. Create `template_stats` model (`backend/app/models/template_stats.py`)
2. Create `program_prompt_audit` model (`backend/app/models/program_prompt_audit.py`)
3. Add `program_prompt`, `program_modifiable`, `hypothesis_mode` fields to `ResearchSession`
4. Expand `HYPOTHESIS_TEMPLATES` schema in both `autoresearch.py` and `genetic_programming.py`
5. Create `LIVE_FEATURES` registry
6. Add `StrategySpec` dataclass as universal container
7. Migrate existing HypothesisIndividual → StrategySpec

### Phase 2: Template Management (Estimated: 3-4 sessions)

1. Add `_hermes_create_template()` to `HermesResearchPlugin`
2. Add template performance tracking to `AutoresearchService`
3. Update `_generate_hypotheses()` to select templates with regime-aware bias
4. Add template creation endpoint (`POST /api/research/templates`)
5. Add template dedup (embedding similarity or signature hash)
6. Add soft pool cap with LRU eviction

### Phase 3: Three-Mode System & User Direction (Estimated: 3-4 sessions)

1. Implement `CONSTRAINED_ALL` mode with staged template introduction
2. Implement `CONSTRAINED_SELECTED` mode with regime compatibility warning
3. Implement `UNCONSTRAINED` mode with structured LLM output schema
4. Implement `program_prompt` as user direction file
5. Implement `program_modifiable` toggle
6. Add mode switching logic with session forking
7. Add `POST /api/research/sessions/{id}/mode` endpoint

### Phase 4: GP Enhancement (Estimated: 3-4 sessions)

1. Add dimension-aware crossover/mutation to `genetic_programming.py`
2. Migrate GP operators from template-string-based to StrategySpec-field-based
3. Add dynamic feature pool to `HypothesisIndividual`
4. Add template_stats-weighted tournament selection
5. Add Hermes-driven template creation to evolution pipeline
6. Add LLM-as-mutation-operator for unconstrained track
7. Add template extraction bridge (unconstrained KEPT → template entry)

### Phase 5: Meta-Strategy Integration (Estimated: 3-4 sessions)

1. Create PortfolioSimulator for Stage 1 evaluation
2. Create MetaStrategyHypothesisProvider
3. Extend NSGA-II objective vector to 6+ dimensions
4. Wire two-stage pipeline into `run_iteration()`
5. Add `POST /api/research/sessions/{id}/hypotheses` endpoint for template catalog

### Phase 6: Testing & Validation (Estimated: 3-4 sessions)

1. Unit tests for expanded templates and schema validation
2. Unit tests for dimension-aware GP operators
3. Unit tests for StrategySpec unification
4. Unit tests for three-mode selection switching
5. Unit tests for program_prompt audit logging
6. Integration tests for unconstrained LLM generation
7. Integration tests for autonomous template creation
8. Integration tests for two-stage pipeline
9. Integration tests for template extraction bridge
10. Performance benchmarks

## 10. Dependencies & Risks

### New Dependencies
- No new Python packages required (uses existing numpy, random, asyncio, sentence-transformers)
- Sentence-transformers recommended for embedding-based template dedup (optional, graceful degradation to signature-hash dedup)
- Hermes plugin must be available for autonomous template creation and unconstrained mode (optional, graceful degradation)

### Risks

| Risk | Mitigation |
|------|------------|
| Template explosion (too many templates, poor selection) | Soft pool cap (200) with LRU eviction; template_stats tracking biases GP toward proven templates; per-iteration random subset selection |
| Hermes hallucinates invalid templates | JSON schema validation on Hermes output; feature existence check against LIVE_FEATURES; fallback to manual template creation if parsing fails |
| Two-stage pipeline doubles compute time | Cache Stage 1 PortfolioSimulation results; only re-run Stage 2 when pool composition changes |
| Feature registry incompatible with actual market data | Lazy feature validation; `_build_feature_vector` reports missing features via soft fail; fallback feature mapping for close matches |
| Unconstrained mode produces junk (winner's curse) | Two-pass LLM (generate then self-filter); structured output schema forces evaluatable format; cheap heuristic guard before TabPFN |
| Mode switch resets all progress | Separate GP populations per mode stored for comparison; optional "migrate top 3" conversion on switch; session forking enables side-by-side comparison |
| program_prompt creates suboptimal constraints | Toggle to allow LLM to modify; analytics insight shows cost of constraint vs. unconstrained alternative; audit log preserves all versions |
| LLM cost for unconstrained mode | Each unconstrained iteration costs 1+ LLM calls (generation + optional self-filter). Configurable per-session LLM budget. Falls back to template mode if budget exhausted |

## 11. Future Work

- **Template pruning**: Remove templates with `n_trials > 20` and `keep_rate < 0.1` and `avg_sharpe < 0`
- **Transfer learning**: Export template_stats across sessions when market conditions are similar
- **Visual template studio**: Frontend UI for browsing, creating, and testing templates
- **Template composition DSL**: Allow templates to be composed as `(entry AND volume_confirmation) OR (sentiment AND regime_filter)`
- **Auto feature engineering**: GP that generates derived features (ratios, differences, log transforms) and adds them to LIVE_FEATURES
- **Cross-session evolution**: Allow GP populations and template_stats to carry over between sessions when regime conditions match
- **Multi-LLM strategy generation**: Use different LLM providers/prompts in unconstrained mode and compare which produces better strategies
- **program_prompt templates**: Pre-built program_prompt templates for common research goals ("minimize drawdown," "maximize win rate," "find regime-robust strategies")
