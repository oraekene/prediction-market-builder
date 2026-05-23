# Meta-Strategy Hypothesis Catalog

## 1. Purpose

The meta-strategy GP needs a population of meta-hypotheses to evolve. Each meta-hypothesis is a complete configuration for how a strategy pool should be managed: which strategies to include, how to weight them, when to promote replacements, and how to handle regime changes.

This catalog provides the initial seed population — 25 entries across 10 personality groups. They cover the full range of meta-strategy behaviors from conservative to aggressive, regime-aware to performance-chasing.

## 2. Relationship to Dimension 13 (Meta Strategy)

From the template taxonomy, Dimension 13 is `meta_strategy_mode` with values:

| Value | Description |
|-------|-------------|
| `adaptive_promotion` | Dynamic promotion thresholds based on regime |
| `confluence_gated` | Require multiple strategy confirmations |
| `diversification` | Spread allocation, minimize overlap |
| `performance_chasing` | Favor recent best performers |
| `regime_switching` | Swap strategy sets when regime changes |

Each catalog entry maps to one or more of these modes.

## 3. The 10 Personality Groups

### Group 1: Conservative (3 entries)

**Entry 1: SteadyEddie**
```
Meta mode: adaptive_promotion
Strategy selection: top 3 by Sharpe (minimum 0.5)
Weighting: equal (33% each)
Promotion threshold: Sharpe must exceed current by 0.2
Re-evaluation: every 7 days
Regime handling: ignore (same params across regimes)
Promotion probation: 96 hours
Diversification floor: strategies must have <0.7 correlation
```

**Entry 2: SlowAndSteady**
```
Meta mode: diversification
Strategy selection: top 5 by Sharpe (min 0.3)
Weighting: Sharpe-proportional
Promotion threshold: Sharpe must exceed current by 0.15
Re-evaluation: every 14 days
Regime handling: ignore
Promotion probation: 168 hours (1 week)
Diversification floor: strategies must have <0.5 correlation
```

**Entry 3: CapitalPreserver**
```
Meta mode: adaptive_promotion
Strategy selection: top 2 by Sharpe (min 0.8)
Weighting: equal (50%)
Promotion threshold: Sharpe must exceed current by 0.3
Re-evaluation: every 3 days
Regime handling: if 3 consecutive losing days, switch to cash
Promotion probation: 120 hours
Diversification floor: strategies must have <0.3 correlation
```

### Group 2: Aggressive (3 entries)

**Entry 4: HighOctane**
```
Meta mode: performance_chasing
Strategy selection: top 1 by recent 7-day Sharpe
Weighting: 100% to winner
Promotion threshold: any Sharpe improvement > 0
Re-evaluation: daily
Regime handling: ignore (chase regardless)
Promotion probation: 24 hours
Diversification floor: none (single strategy)
```

**Entry 5: Rotator**
```
Meta mode: regime_switching
Strategy selection: top 2 per detected regime
Weighting: 50% each
Promotion threshold: Sharpe must exceed current by 0.1
Re-evaluation: every 2 days
Regime handling: explicit — rotate strategy set when regime classifier detects shift
Promotion probation: 48 hours
Diversification floor: strategies must have <0.6 correlation
Regime classifier: momentum vs mean-reversion detector
```

**Entry 6: MomentumJunkie**
```
Meta mode: performance_chasing
Strategy selection: top 2 by momentum score (1-week return)
Weighting: momentum-proportional
Promotion threshold: Sharpe must exceed current by 0.05
Re-evaluation: every 12 hours
Regime handling: ignore
Promotion probation: 12 hours
Diversification floor: none
```

### Group 3: Regime-Focused (3 entries)

**Entry 7: RegimeTracker**
```
Meta mode: regime_switching
Strategy selection: regime-specific: trending -> momentum strategies, ranging -> mean reversion
Weighting: equal within regime bucket
Promotion threshold: regime-specific (trending: 0.1, ranging: 0.2)
Re-evaluation: daily
Regime handling: regime classifier with 3 states (trending/ranging/volatile)
Promotion probation: 48 hours
Diversification floor: cross-regime strategies excluded when regime is clear
```

**Entry 8: VolatilityAware**
```
Meta mode: adaptive_promotion
Strategy selection: top 3 by risk-adjusted return (Sharpe / volatility percentile)
Weighting: risk-parity (inverse volatility)
Promotion threshold: risk-adjusted Sharpe improvement > 0.15
Re-evaluation: every 3 days
Regime handling: high vol -> reduce position sizes, favor mean reversion
Promotion probation: 72 hours
Diversification floor: volatility correlation < 0.5
```

**Entry 9: RegimeHedge**
```
Meta mode: regime_switching
Strategy selection: 1 primary + 1 hedge per regime
Weighting: primary 70%, hedge 30%
Promotion threshold: primary 0.15, hedge 0.10
Re-evaluation: weekly
Regime handling: always maintain hedge position in opposite-regime strategy
Promotion probation: 96 hours
Diversification floor: primary and hedge must have negative correlation
```

### Group 4: Diversification-Focused (3 entries)

**Entry 10: MaxDiversity**
```
Meta mode: diversification
Strategy selection: top 8 by diversity score (lowest average pairwise correlation)
Weighting: equal (12.5% each)
Promotion threshold: diversity-weighted Sharpe > current + 0.1
Re-evaluation: every 5 days
Regime handling: ignore (diversification is the hedge)
Promotion probation: 48 hours
Diversification floor: average pairwise correlation < 0.3
```

**Entry 11: Uncorrelated**
```
Meta mode: diversification
Strategy selection: strategies with correlation to portfolio < 0.3
Weighting: equal
Promotion threshold: Sharpe > 0 (any)
Re-evaluation: every 7 days
Regime handling: ignore
Promotion probation: 72 hours
Diversification floor: correlation < 0.3 to every other selected strategy
```

**Entry 12: BucketDiversifier**
```
Meta mode: diversification
Strategy selection: top 2 per strategy type bucket (momentum, mean reversion, breakout, sentiment)
Weighting: equal per bucket (25% each), equal within bucket (12.5% each)
Promotion threshold: bucket-specific (momentum: 0.15, mean reversion: 0.2, etc.)
Re-evaluation: every 4 days
Regime handling: adjust bucket weights based on regime
Promotion probation: 48 hours
Diversification floor: must have at least 1 strategy from each of 4 buckets
```

### Group 5: Confluence-Focused (2 entries)

**Entry 13: ConfluenceSeeker**
```
Meta mode: confluence_gated
Strategy selection: top 3 strategies that most frequently agree
Weighting: equal
Promotion threshold: consensus accuracy > 60%
Re-evaluation: every 3 days
Regime handling: ignore (confluence itself is regime-adaptive)
Promotion probation: 48 hours
Diversification floor: strategies should come from different families (momentum + sentiment + statistical)
Voting rule: at least 2 of 3 must agree
```

**Entry 14: WeightedConsensus**
```
Meta mode: confluence_gated
Strategy selection: top 4 by historical agreement with actual outcome
Weighting: confidence-proportional (based on historical accuracy)
Promotion threshold: weighted consensus accuracy > 65%
Re-evaluation: daily
Regime handling: ignore (weighting adapts automatically)
Promotion probation: 36 hours
Diversification floor: max 2 strategies from same template family
Voting rule: weighted average, threshold 0.5
```

### Group 6: Performance-Chasing (3 entries)

**Entry 15: HotHand**
```
Meta mode: performance_chasing
Strategy selection: top 1 by 3-day Sharpe
Weighting: 100%
Promotion threshold: any positive Sharpe improvement
Re-evaluation: every 6 hours
Regime handling: ignore — chase regardless
Promotion probation: 6 hours
Diversification floor: none
```

**Entry 16: MomentumRanking**
```
Meta mode: performance_chasing
Strategy selection: top 3 by 7-day return
Weighting: rank-proportional (1st: 50%, 2nd: 30%, 3rd: 20%)
Promotion threshold: 7-day return > current + 2%
Re-evaluation: daily
Regime handling: ignore
Promotion probation: 24 hours
Diversification floor: none
```

**Entry 17: RecentForm**
```
Meta mode: performance_chasing
Strategy selection: top 2 by exponentially-weighted recent Sharpe (decay 0.9)
Weighting: proportional to EW Sharpe
Promotion threshold: EW Sharpe improvement > 0.05
Re-evaluation: every 12 hours
Regime handling: ignore
Promotion probation: 24 hours
Diversification floor: low-medium (max pairwise correlation 0.7)
```

### Group 7: ML-Enhanced (2 entries)

**Entry 18: SharpRatio**
```
Meta mode: adaptive_promotion
Strategy selection: top 4 by ML-predicted next-week Sharpe
Weighting: equal
Promotion threshold: predicted Sharpe > current Sharpe + 0.1
Re-evaluation: weekly
Regime handling: regime as ML feature
Promotion probation: 72 hours
Diversification floor: correlation < 0.6
ML model: lightweight gradient boosting on historical strategy performance + regime + market features
```

**Entry 19: MetaLearner**
```
Meta mode: adaptive_promotion
Strategy selection: top 3 by meta-learner score (ensemble of Sharpe, diversity contribution, regime fit)
Weighting: meta-learner proportional
Promotion threshold: meta-learner score > current + 5%
Re-evaluation: every 5 days
Regime handling: regime as meta-learner feature
Promotion probation: 96 hours
Diversification floor: diversity contribution must be positive
ML model: meta-learner trained on historical strategy performance patterns
```

### Group 8: Sentiment-Aware (2 entries)

**Entry 20: SentimentFollower**
```
Meta mode: regime_switching
Strategy selection: positive sentiment -> momentum strategies, negative -> mean reversion/defensive
Weighting: sentiment-weighted (extreme sentiment = higher conviction)
Promotion threshold: regime-dependent (normal: 0.15, extreme: 0.25)
Re-evaluation: every 2 days
Regime handling: sentiment-based regime classification (positive/neutral/negative)
Promotion probation: 48 hours
Diversification floor: sentiment-sourced strategies must be < 50% of pool
```

**Entry 21: SentimentHedge**
```
Meta mode: confluence_gated
Strategy selection: if sentiment diverges from price -> activate hedge (inverse sentiment strategy)
Weighting: base 80%, hedge 20%
Promotion threshold: divergence signal must persist for 3+ days
Re-evaluation: daily during divergence, weekly otherwise
Regime handling: divergence-based regime
Promotion probation: 72 hours
Diversification floor: base and hedge must be negatively correlated when divergence active
```

### Group 9: Tempo-Specialized (2 entries)

**Entry 22: DayTrader**
```
Meta mode: performance_chasing
Strategy selection: top 2 by hourly Sharpe
Weighting: equal
Promotion threshold: hourly Sharpe improvement > 0.05
Re-evaluation: every 4 hours
Regime handling: ignore
Promotion probation: 12 hours
Diversification floor: correlation < 0.5 on hourly timescale
Timeframe: short (minutes to hours)
```

**Entry 23: SwingTrader**
```
Meta mode: adaptive_promotion
Strategy selection: top 3 by daily Sharpe
Weighting: Sharpe-proportional
Promotion threshold: daily Sharpe improvement > 0.1
Re-evaluation: daily
Regime handling: ignore
Promotion probation: 48 hours
Diversification floor: correlation < 0.6 on daily timescale
Timeframe: medium (hours to days)
```

### Group 10: Composite (2 entries)

**Entry 24: MultiTimeframe**
```
Meta mode: confluence_gated
Strategy selection: 1 short-term + 1 medium-term + 1 long-term strategy
Weighting: equal (33% each)
Promotion threshold: all three must improve (separate thresholds per timeframe)
Re-evaluation: daily
Regime handling: ignore (timeframe diversity handles it)
Promotion probation: 72 hours
Diversification floor: must cover 3 distinct timeframes (daily/3d/7d)
Voting rule: all 3 must agree
```

**Entry 25: SwissArmy**
```
Meta mode: diversification
Strategy selection: 1 from each of 4 families (momentum, mean reversion, sentiment, statistical)
Weighting: equal (25% each)
Promotion threshold: family score improvement > 0.2
Re-evaluation: every 3 days
Regime handling: adjust per-family weights based on regime suitability
Promotion probation: 48 hours
Diversification floor: each from a different family
```

## 4. Catalog Coverage Map

| Dimension | Values Covered | Missing |
|-----------|---------------|---------|
| meta_strategy_mode | adaptive_promotion, confluence_gated, diversification, performance_chasing, regime_switching | None |
| strategy_selection | top N by Sharpe, diversity score, ML prediction, regime-specific, agreement | Could add: random, equal-weighted-all |
| weighting_method | equal, proportional (Sharpe, volatility, rank, confidence, momentum) | Could add: fixed, Kelly-optimal |
| promotion_cadence | 6h to 14 days | Could add: market-event-triggered |
| regime_detection | Ignore, momentum/mean-reversion, volatility, sentiment, divergence | Could add: macroeconomic regime |
| diversification | Full set: correlation, bucket, family, timeframe | Could add: geographic |
| risk_handling | Implicit via diversification, explicit via cash switching | Could add: VaR-based, drawdown-based |
| ML integration | Lightweight GB, meta-learner | Could add: RL-based, transformer-based |

## 5. Evolution Path

These 25 entries are seeds. The meta-GP will:
1. **Recombine** them via crossover (swap weighting methods, merge regime handling)
2. **Mutate** parameters (adjust promotion thresholds, change cadence)
3. **Discover gaps** in coverage (e.g., no entry uses VaR-based risk → GP may produce one)
4. **Merge** successful patterns (e.g., sentiment + volatility awareness)
