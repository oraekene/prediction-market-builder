# Strategy Templates — Node Reference & Patterns

## Node Type Reference

### Data Source Nodes

#### polymarket_source

Fetches markets from Polymarket CLOB API.

```json
{"type": "polymarket_source", "config": {"market_id": "0x123..."}}
// Output: {"markets": [...], "count": 3, "platform": "polymarket"}
```

#### kalshi_source

Fetches markets from Kalshi REST API.

```json
{"type": "kalshi_source", "config": {"market_id": "KXBTD-24"}}
// Output: {"markets": [...], "count": 3, "platform": "kalshi"}
```

#### drift_source

Fetches markets from Drift Protocol API.

```json
{"type": "drift_source", "config": {"market_id": "BTC-PERP"}}
// Output: {"markets": [...], "count": 3, "platform": "drift"}
```

#### web_search

Searches the web via DuckDuckGo.

```json
{"type": "web_search", "config": {"query": "bitcoin news today", "max_results": 5}}
// Output: {"results": [...], "count": 5}
```

#### news_source

Fetches news articles via NewsAPI.

```json
{"type": "news_source", "config": {"query": "crypto regulation", "max_results": 5}}
// Output: {"articles": [...], "count": 5}
```

### Condition Nodes

#### threshold_condition

Compares a market field using an operator.

```json
{"type": "threshold_condition",
 "config": {"field": "current_odds", "operator": "gt", "threshold": 0.6}}
// Output: {"triggered": true, "value": 0.65, "threshold": 0.6}
```

| Operator | Description |
|----------|-------------|
| `lt` | Less than threshold |
| `gt` | Greater than threshold |
| `between` | Between threshold and threshold_high |
| `outside` | Outside threshold and threshold_high |

#### time_condition

Time-based gate.

```json
{"type": "time_condition",
 "config": {"condition": "after", "target": "2026-06-01T00:00:00Z"}}
// Output: {"triggered": true, "now": "2026-05-25T...", "target": "2026-06-01T00:00:00Z"}
```

| Condition | Description |
|-----------|-------------|
| `before` | Triggered before target time |
| `after` | Triggered after target time |
| `between` | Triggered between start and end times |

#### and_or_gate

Logic gate combining upstream conditions.

```json
{"type": "and_or_gate",
 "config": {"gate_type": "and"}}
// Output: {"triggered": true, "gate_type": "and", "upstream_count": 2}
```

| Gate | Behavior |
|------|----------|
| `and` | True if all upstream outputs are triggered |
| `or` | True if any upstream output is triggered |
| `xor` | True if exactly one upstream output is triggered |
| `nand` | True unless all upstream outputs are triggered |

#### branch

Conditional branch — only activates when upstream condition is met.

```json
{"type": "branch",
 "config": {"branch_if": true}}
// Output: {"activated": true, "condition_triggered": true, "branch_if": true, "output": {...}}
```

#### sentiment_filter

Analyzes text sentiment.

```json
{"type": "sentiment_filter",
 "config": {"threshold": 0.5}}
// Output: {"triggered": true, "sentiment": 0.75, "label": "positive", "text_preview": "..."}
```

### AI Signal Nodes

#### tabpfn_signal

Validates trading signals using TabPFN (Prior-Data Fitted Networks).

```json
{"type": "tabpfn_signal",
 "config": {"signal_features": {"probability": 0.65, "confidence": 0.8}}}
// Output: {"verdict": "CONFIRMED"}
```

| Verdict | Meaning |
|---------|---------|
| `CONFIRMED` | Signal validated by TabPFN |
| `REJECTED` | Signal rejected |
| `UNAVAILABLE` | TabPFN service not available |
| `ERROR` | Processing error |

#### toto2_climate

Assesses market regime (volatility, trend, anomaly).

```json
{"type": "toto2_climate", "config": {}}
// Output: {"regime": "low_volatility", "volatility": 0.15, "trend": 0.02,
//  "anomaly_score": 0.1, "volatility_surface": {...}}
```

#### bayesian_inference

Updates probability using Bayes' theorem.

```json
{"type": "bayesian_inference",
 "config": {"prior": 0.5, "likelihood_true": 0.8, "likelihood_false": 0.3}}
// Output: {"posterior": 0.727, "prior": 0.5, "likelihood_true": 0.8, "likelihood_false": 0.3, "evidence": 0.55}
```

#### monte_carlo

Runs Monte Carlo simulation on strategy outcomes.

```json
{"type": "monte_carlo",
 "config": {"trials": 1000, "win_probability": 0.6, "avg_win": 100, "avg_loss": 50}}
// Output: {"mean": 40.0, "win_probability": 0.85, "percentiles": {"p5": -50, "p25": 10, "p75": 80, "p95": 150}}
```

#### shap_explainability

SHAP explanation of a TabPFN signal.

```json
{"type": "shap_explainability", "config": {}}
// Output: {"explanation": {"contributions": {...}, "mean_abs_importance": {...},
//   "ranking": [...], "output_value": 0.65}}
```

#### shap_feature_importance

Filters features by importance threshold.

```json
{"type": "shap_feature_importance",
 "config": {"threshold": 0.05}}
// Output: {"triggered": true, "top_features": [...], "importance": {...},
//   "ranking": [...], "output_value": 0.65}
```

### Risk Nodes

#### var_check

Checks Value-at-Risk against limit.

```json
{"type": "var_check",
 "config": {"confidence": 0.95, "var_limit": 200}}
// Output: {"triggered": true, "var": 150, "es": 220, "confidence": 0.95, "limit": 200}
```

#### drawdown_monitor

Monitors current drawdown against maximum allowed.

```json
{"type": "drawdown_monitor", "config": {}}
// Output: {"triggered": true, "drawdown": 0.03, "max_drawdown": 0.15}
```

#### correlation_check

Checks portfolio correlation against maximum.

```json
{"type": "correlation_check",
 "config": {"max_correlation": 0.7}}
// Output: {"triggered": true, "correlation": 0.45, "max_correlation": 0.7}
```

#### concentration_check

Checks portfolio concentration (Herfindahl-Hirschman Index).

```json
{"type": "concentration_check",
 "config": {"max_concentration": 0.4}}
// Output: {"triggered": false, "concentration": 0.45, "max_concentration": 0.4}
```

#### position_sizer

Calculates position size using Kelly, fixed, or volatility method.

```json
{"type": "position_sizer",
 "config": {"method": "kelly", "kelly_fraction": 0.25}}
```

| Method | Description | Config |
|--------|-------------|--------|
| `kelly` | Kelly Criterion (default) | `kelly_fraction` (0–1) |
| `fixed` | Fixed fraction | `fixed_fraction` (default 0.02) |
| `volatility` | Volatility-adjusted | Adjusts base by volatility regime |

```json
// Output: {"suggested_size": 0.05, "method": "kelly", "approved": true}
```

#### stop_loss

Per-position stop-loss check.

```json
{"type": "stop_loss",
 "config": {"stop_loss_pct": 0.1}}
// Output: {"triggered": false, "stop_loss": 0.1, "positions": []}
```

#### take_profit

Per-position take-profit check.

```json
{"type": "take_profit",
 "config": {"take_profit_pct": 0.2}}
// Output: {"triggered": true, "take_profit": 0.2, "positions": [{"market_id": "str", "gain_pct": 0.25}]}
```

#### min_confidence

Checks signal confidence threshold.

```json
{"type": "min_confidence",
 "config": {"min_confidence": 0.6}}
// Output: {"triggered": true, "confidence": 0.8, "min_confidence": 0.6}
```

### Action Nodes

#### place_bet

Place a trade on the exchange.

```json
{"type": "place_bet",
 "config": {"side": "buy", "type": "market", "time_in_force": "GTC"}}
// Output: {"action": "place_bet", "approved": true, "platform": "polymarket",
//   "market_id": "str", "side": "buy", "size": 0.05, "type": "market"}
```

#### reject_action

Rejects the trade.

```json
{"type": "reject_action", "config": {}}
// Output: {"approved": false, "suggested_size": 0, "violations": ["rule_rejected"]}
```

#### approve_action

Approves the trade.

```json
{"type": "approve_action", "config": {}}
// Output: {"approved": true, "suggested_size": 0, "violations": ["rule_approved"]}
```

#### alert_action

Fires an alert.

```json
{"type": "alert_action",
 "config": {"message": "Drawdown limit approaching", "severity": "warning"}}
// Output: {"action": "alert", "message": "Drawdown limit approaching",
//   "severity": "warning", "approved": true}
```

#### hedge_action

Suggests hedging trades.

```json
{"type": "hedge_action", "config": {}}
// Output: {"hedges": [...], "hedge_ratio": 0.5}
```

#### rebalance_action

Suggests rebalancing trades.

```json
{"type": "rebalance_action", "config": {}}
// Output: {"trades": [...]}
```

#### webhook

Sends data to an external URL.

```json
{"type": "webhook",
 "config": {"url": "https://hooks.slack.com/...", "method": "POST"}}
// Output: {"sent": true, "status_code": 200, "response": "ok"}
```

### Utility Nodes

#### forward

Passes through upstream value.

```json
{"type": "forward", "config": {}}
// Output: {"forwarded": true, ...upstream_output}
```

#### performance

Reads a performance metric from the context.

```json
{"type": "performance",
 "config": {"metric": "sharpe_ratio"}}
// Output: {"value": 1.245, "metric": "sharpe_ratio"}
```

#### backtest

Runs a simulated backtest.

```json
{"type": "backtest",
 "config": {"initial_capital": 10000, "steps": 100}}
// Output: {"total_trades": 12, "win_rate": 0.583, "total_pnl": 850,
//   "return_pct": 8.5, "final_capital": 10850}
```

---

## Template Patterns

### 1. Momentum Following

Triggers when odds cross above a threshold — simple trend following.

```json
{
  "name": "Momentum Following",
  "description": "Buy when market odds cross above 0.6 threshold",
  "tags": ["momentum", "trend"],
  "config": {
    "nodes": [
      {"id": "src", "type": "polymarket_source", "config": {}},
      {"id": "cond", "type": "threshold_condition",
       "config": {"field": "current_odds", "operator": "gt", "threshold": 0.6}},
      {"id": "sizer", "type": "position_sizer",
       "config": {"method": "kelly", "kelly_fraction": 0.25}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "src", "target": "cond"},
      {"source": "cond", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ],
    "risk_profile": {
      "max_position_size": 0.2,
      "max_drawdown": 0.15,
      "stop_loss": 0.1,
      "kelly_fraction": 0.25,
      "min_confidence": 0.6
    }
  }
}
```

### 2. Mean Reversion

Bet against extreme odds — buy when oversold, sell when overbought.

```json
{
  "name": "Mean Reversion",
  "description": "Buy when odds are oversold, sell when overbought",
  "tags": ["mean-reversion", "contrarian"],
  "config": {
    "nodes": [
      {"id": "src", "type": "kalshi_source", "config": {}},
      {"id": "regime", "type": "toto2_climate", "config": {}},
      {"id": "buy_cond", "type": "threshold_condition",
       "config": {"field": "current_odds", "operator": "lt", "threshold": 0.3}},
      {"id": "sell_cond", "type": "threshold_condition",
       "config": {"field": "current_odds", "operator": "gt", "threshold": 0.7}},
      {"id": "buy_gate", "type": "and_or_gate", "config": {"gate_type": "and"}},
      {"id": "sell_gate", "type": "and_or_gate", "config": {"gate_type": "and"}},
      {"id": "sizer", "type": "position_sizer", "config": {"method": "volatility"}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "src", "target": "regime"},
      {"source": "src", "target": "buy_cond"},
      {"source": "src", "target": "sell_cond"},
      {"source": "regime", "target": "buy_gate"},
      {"source": "buy_cond", "target": "buy_gate"},
      {"source": "buy_gate", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ]
  }
}
```

### 3. Volatility Breakout

Trade when volatility exceeds a threshold (regime change).

```json
{
  "name": "Volatility Breakout",
  "description": "Trade market when volatility spikes above threshold",
  "tags": ["volatility", "breakout"],
  "config": {
    "nodes": [
      {"id": "src", "type": "drift_source", "config": {}},
      {"id": "climate", "type": "toto2_climate", "config": {}},
      {"id": "cond", "type": "threshold_condition",
       "config": {"field": "volatility", "operator": "gt", "threshold": 0.3}},
      {"id": "var", "type": "var_check", "config": {"confidence": 0.95, "var_limit": 300}},
      {"id": "gate", "type": "and_or_gate", "config": {"gate_type": "and"}},
      {"id": "sizer", "type": "position_sizer", "config": {"method": "volatility"}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "src", "target": "climate"},
      {"source": "src", "target": "cond"},
      {"source": "climate", "target": "gate"},
      {"source": "cond", "target": "gate"},
      {"source": "gate", "target": "var"},
      {"source": "var", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ]
  }
}
```

### 4. Cross-Market Arbitrage

Exploit price differences between two exchanges for the same asset.

```json
{
  "name": "Cross-Market Arbitrage",
  "tags": ["arbitrage", "cross-exchange"],
  "config": {
    "nodes": [
      {"id": "pm", "type": "polymarket_source", "config": {}},
      {"id": "kl", "type": "kalshi_source", "config": {}},
      {"id": "diff", "type": "threshold_condition",
       "config": {"field": "price_differential", "operator": "gt", "threshold": 0.02}},
      {"id": "sizer", "type": "position_sizer", "config": {"method": "fixed", "fixed_fraction": 0.1}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "pm", "target": "diff"},
      {"source": "kl", "target": "diff"},
      {"source": "diff", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ]
  }
}
```

### 5. News Sentiment

Trade based on news sentiment analysis with AI signal validation.

```json
{
  "name": "News Sentiment",
  "tags": ["sentiment", "news", "ai"],
  "config": {
    "nodes": [
      {"id": "news", "type": "news_source", "config": {}},
      {"id": "sentiment", "type": "sentiment_filter", "config": {"threshold": 0.5}},
      {"id": "tabpfn", "type": "tabpfn_signal", "config": {}},
      {"id": "gate", "type": "and_or_gate", "config": {"gate_type": "and"}},
      {"id": "drawdown", "type": "drawdown_monitor", "config": {}},
      {"id": "sizer", "type": "position_sizer", "config": {"method": "kelly", "kelly_fraction": 0.15}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "news", "target": "sentiment"},
      {"source": "news", "target": "tabpfn"},
      {"source": "sentiment", "target": "gate"},
      {"source": "tabpfn", "target": "gate"},
      {"source": "gate", "target": "drawdown"},
      {"source": "drawdown", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ]
  }
}
```

### 6. Hedging Strategy

Protect existing positions with correlated hedges.

```json
{
  "name": "Portfolio Hedge",
  "tags": ["hedging", "risk-management"],
  "config": {
    "nodes": [
      {"id": "corr", "type": "correlation_check", "config": {"max_correlation": 0.7}},
      {"id": "conc", "type": "concentration_check", "config": {"max_concentration": 0.3}},
      {"id": "gate", "type": "and_or_gate", "config": {"gate_type": "or"}},
      {"id": "hedge", "type": "hedge_action", "config": {}},
      {"id": "alert", "type": "alert_action",
       "config": {"message": "Portfolio risk limits exceeded", "severity": "warning"}}
    ],
    "edges": [
      {"source": "corr", "target": "gate"},
      {"source": "conc", "target": "gate"},
      {"source": "gate", "target": "hedge"},
      {"source": "hedge", "target": "alert"}
    ]
  }
}
```

### 7. Bayesian Multi-Signal

Combines multiple signals using Bayesian inference.

```json
{
  "name": "Bayesian Multi-Signal",
  "tags": ["bayesian", "multi-signal", "advanced"],
  "config": {
    "nodes": [
      {"id": "src", "type": "polymarket_source", "config": {}},
      {"id": "news", "type": "news_source", "config": {}},
      {"id": "sentiment", "type": "sentiment_filter", "config": {"threshold": 0.4}},
      {"id": "tabpfn", "type": "tabpfn_signal", "config": {}},
      {"id": "bayes", "type": "bayesian_inference",
       "config": {"prior": 0.5, "likelihood_true": 0.7, "likelihood_false": 0.3}},
      {"id": "cond", "type": "threshold_condition",
       "config": {"field": "posterior", "operator": "gt", "threshold": 0.6}},
      {"id": "sizer", "type": "position_sizer", "config": {"method": "kelly"}},
      {"id": "action", "type": "place_bet", "config": {"side": "buy"}}
    ],
    "edges": [
      {"source": "src", "target": "news"},
      {"source": "news", "target": "sentiment"},
      {"source": "sentiment", "target": "bayes"},
      {"source": "tabpfn", "target": "bayes"},
      {"source": "bayes", "target": "cond"},
      {"source": "cond", "target": "sizer"},
      {"source": "sizer", "target": "action"}
    ]
  }
}
```

---

## Node Graph JSON Format

```json
{
  "nodes": [
    {"id": "unique_id", "type": "node_type", "config": {"key": "value"}}
  ],
  "edges": [
    {"source": "source_node_id", "target": "target_node_id"}
  ]
}
```

### Edge Rules

- Graph must be a DAG (no cycles)
- Each node receives outputs from all upstream connected nodes as `node_inputs`
- If multiple upstream nodes connect to one node, all their outputs are merged
- Execution follows topological order (inputs ready before node runs)
- Cycle detection: if cycle detected, cycle nodes return `{"error": "cycle detected"}`

### Output Propagation

| Scenario | Behavior |
|----------|----------|
| Node has `approved` in output | Becomes final result (action node wins) |
| Node has `action` in output | Becomes final result |
| No action node defined | Last node's output is returned |
| Empty graph | Default: `{"approved": true, "suggested_size": 0.0, "violations": []}` |
