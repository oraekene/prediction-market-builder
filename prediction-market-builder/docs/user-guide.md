# Prediction Market Strategy Builder — User Guide

## Architecture Overview

The system is built on 5 layers:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Svelte 5 + Tailwind | Visual strategy builder and dashboard |
| **API** | FastAPI (Python) | REST + WebSocket endpoints |
| **Strategy Engine** | Graph-based node executor | DAG of conditions, signals, risk checks, actions |
| **Execution** | Connector pattern | Polymarket CLOB v4, Kalshi REST v2, Drift API |
| **Data** | SQLite/Postgres + ChromaDB + DuckDB | Relational, vector memory, time-series analytics |

## Quick Start

### 1. Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Response contains access_token and refresh_token
# Use Bearer token in subsequent requests:
# Authorization: Bearer <access_token>
```

### 2. Browse Markets

```bash
# List all open markets
curl http://localhost:8000/api/markets \
  -H "Authorization: Bearer <token>"

# Filter by platform
curl "http://localhost:8000/api/markets?platform=polymarket&limit=10"

# Search
curl "http://localhost:8000/api/markets?search=bitcoin"
```

### 3. Create Your First Strategy

Use **Chat Mode** for natural language or **Node Mode** for visual graph building.

#### Chat Mode

```
POST /api/chat/message
{"message": "Create a strategy that buys when Bitcoin price crosses above $50k with 70% confidence"}

POST /api/strategies
{
  "name": "BTC Momentum",
  "mode": "chat"
}
```

#### Node Mode

```json
POST /api/strategies
{
  "name": "Simple Threshold",
  "mode": "node",
  "nodes": [
    {"id": "n1", "type": "polymarket_source", "config": {"market_id": "btc-123"}},
    {"id": "n2", "type": "threshold_condition", "config": {"field": "current_odds", "operator": "gt", "threshold": 0.6}},
    {"id": "n3", "type": "position_sizer", "config": {"method": "kelly", "kelly_fraction": 0.25}},
    {"id": "n4", "type": "place_bet", "config": {"side": "buy"}}
  ],
  "edges": [
    {"source": "n1", "target": "n2"},
    {"source": "n2", "target": "n3"},
    {"source": "n3", "target": "n4"}
  ],
  "risk_profile": {
    "max_position_size": 0.2,
    "max_drawdown": 0.15,
    "stop_loss": 0.1,
    "kelly_fraction": 0.25,
    "min_confidence": 0.6
  }
}
```

### 4. Deploy and Paper Trade

```bash
# Deploy strategy
POST /api/strategies/{id}/deploy

# Get paper wallet
GET /api/paper/wallet

# Place paper trade
POST /api/paper/orders
{
  "wallet_id": "<wallet_id>",
  "platform": "polymarket",
  "market_id": "btc-123",
  "side": "buy",
  "amount": 100,
  "price": 0.55,
  "mode": "paper"
}
```

## Chat Mode (Natural Language)

The Hermes AI assistant understands natural language strategy creation:

- "Create a momentum strategy for tech markets"
- "Add a stop-loss at 10% drawdown"
- "What's my current Sharpe ratio?"
- "Backtest this strategy on the last 30 days"
- "Explain why my last trade lost money"

WebSocket endpoint: `ws://localhost:8000/ws/chat`

## Node Mode (Visual Strategy Builder)

### Node Types

| Category | Nodes | Description |
|----------|-------|-------------|
| **Data Sources** | `polymarket_source`, `kalshi_source`, `drift_source`, `web_search`, `news_source` | Fetch market data or external information |
| **Conditions** | `threshold_condition`, `time_condition`, `and_or_gate`, `branch`, `sentiment_filter` | Decision logic |
| **AI Signals** | `tabpfn_signal`, `toto2_climate`, `shap_explainability`, `shap_feature_importance`, `bayesian_inference`, `monte_carlo` | ML-powered analysis |
| **Risk** | `var_check`, `drawdown_monitor`, `correlation_check`, `concentration_check`, `position_sizer`, `stop_loss`, `take_profit`, `min_confidence` | Risk management |
| **Actions** | `place_bet`, `alert_action`, `webhook`, `hedge_action`, `rebalance_action`, `reject_action`, `approve_action` | Execution |
| **Utility** | `forward`, `performance`, `backtest` | Data flow and analysis |

### Example Strategy Graphs

**Momentum Following:**
```
Market Source → Threshold (price > MA) → Position Sizer → Place Bet
```

**Mean Reversion:**
```
Market Source → Toto2 Climate → Threshold (oversold) → Position Sizer → Place Bet
```

**Cross-Market Arbitrage:**
```
Polymarket Source → Differential Calc → Threshold (>2% gap) → Position Sizer → Place Bet
Kalshi Source _____↑
```

**News Sentiment:**
```
News Source → Sentiment Filter → TabPFN Signal → Risk Check → Place Bet
```

## Risk Management

### Risk Profile Configuration

```json
{
  "max_position_size": 0.2,
  "max_drawdown": 0.15,
  "stop_loss": 0.1,
  "kelly_fraction": 0.25,
  "max_correlation": 0.7,
  "min_confidence": 0.6
}
```

### Risk Metrics

| API | Description |
|-----|-------------|
| `GET /api/risk/summary` | Aggregate VaR, ES, drawdown, concentration, volatility |
| `GET /api/risk/var?confidence=0.95` | Value-at-Risk (historical, parametric, TabPFN) |
| `GET /api/risk/correlation` | Pairwise correlation matrix |
| `GET /api/risk/drawdown` | Current and maximum drawdown |
| `GET /api/risk/portfolio` | Position-level VaR contribution |

### Rule-Based Risk Templates

```bash
# Create a risk template
POST /api/risk-templates
{
  "name": "Conservative",
  "rules": [
    {"condition": {"type": "max_drawdown", "threshold": 0.1}, "action": {"type": "reject"}},
    {"condition": {"type": "min_confidence", "threshold": 0.7}, "action": {"type": "reject"}}
  ]
}

# Evaluate a trade against a template
POST /api/risk-templates/{id}/evaluate
{
  "signal": {"probability": 0.65, "confidence": 0.8},
  "portfolio": {"current_capital": 10000}
}
```

## Paper Trading

### Virtual Wallet

- Default initial balance: $10,000
- Supports paper and live trading modes
- Tracks PnL, win rate, Sharpe ratio, max drawdown

### Performance Metrics

| Metric | Description |
|--------|-------------|
| `total_pnl` | Net profit/loss |
| `win_rate` | Fraction of winning trades |
| `sharpe` | Risk-adjusted return (annualized) |
| `sortino` | Downside deviation-adjusted return |
| `calmar` | Return / max drawdown |
| `max_drawdown` | Peak-to-trough decline |
| `profit_factor` | Gross gain / gross loss |
| `kelly_optimal` | Optimal position size fraction |
| `brier_score` | Probability calibration error |
| `sqn` | System Quality Number |

```bash
GET /api/paper/performance?user_id=default
GET /api/paper/metrics/sharpe?window=50
GET /api/paper/compare?strategy_ids=strat1,strat2
```

## Real Trading

### Setup Exchange API Keys

Store encrypted keys via the user profile. Supported exchanges:

| Exchange | Auth Method | Endpoint |
|----------|------------|----------|
| Polymarket | HMAC-SHA256 | `clob.polymarket.com` |
| Kalshi | RSA-SHA256 | `trading-api.kalshi.com` |
| Drift | Bearer Token | `api.drift.trade` |

### Safety Features

1. **Confirmation Required**: First live trade requires explicit confirmation via `POST /api/paper/confirm-live`
2. **Session Loss Limit**: Default $100 max loss per session
3. **Connection Test**: Verify exchange connectivity before trading via `GET /api/paper/connection-test?platform=polymarket`
4. **Kill Switch**: Emergency stop via `POST /api/paper/kill-switch`
5. **Mode Toggle**: Switch between paper/live via `POST /api/paper/trading-mode`

### Live Trading Flow

```bash
# 1. Confirm live trading
POST /api/paper/confirm-live

# 2. Set trading mode
POST /api/paper/trading-mode {"mode": "live"}

# 3. Place live order
POST /api/paper/orders {"wallet_id": "...", "mode": "live", ...}

# 4. Kill switch if needed
POST /api/paper/kill-switch
```

## Analytics Dashboard

```bash
# Portfolio overview
GET /api/portfolio

# Trade analytics
GET /api/analytics/summary

# Backtest data
GET /api/analytics/backtests
```

## Strategy Templates

### Pre-built Templates

| Template | Description |
|----------|-------------|
| Momentum Following | Buy when price trends above moving average |
| Mean Reversion | Buy oversold markets, sell overbought |
| Volatility Breakout | Trade when volatility exceeds threshold |
| Cross-Market Arbitrage | Exploit price differences across exchanges |
| News Sentiment | Trade based on news sentiment analysis |
| Hedging | Protect positions with correlated hedges |

### Template API

```bash
# List templates
GET /api/strategies/templates

# Create template
POST /api/strategies/templates
{
  "name": "My Template",
  "description": "Custom momentum strategy",
  "config": {"nodes": [...], "edges": [...], "risk_profile": {...}},
  "tags": ["momentum", "conservative"]
}

# Apply template to create strategy
POST /api/strategies/templates/{id}/apply
```

## AI Research Pipeline

### Automated Hypothesis Generation

The system continuously generates, tests, and promotes trading hypotheses:

1. **Alpha Vector Discovery**: RLM scans forums and research for alpha signals
2. **Hypothesis Generation**: NLP creates trading hypotheses from alpha vectors
3. **Backtesting**: Monte Carlo simulation validates hypotheses
4. **Genetic Optimization**: NSGA-II evolves hypothesis population
5. **Promotion**: Top hypotheses are promoted to live strategies

### Research API

```bash
# Trigger research run
POST /api/research/run

# View results
GET /api/research/sessions/{session_id}/results

# Configure research
PUT /api/research/config?preset=sharpe_max&max_concurrent=3
```

## WebSocket Protocol

### Chat WebSocket

```
ws://localhost:8000/ws/chat
```

**Send:**
```json
{"payload": {"content": "Analyze BTC markets", "user_id": "default"}}
```

**Receive:**
```json
{"type": "chat_response", "content": "Analysis results..."}
```

### Research WebSocket

```
ws://localhost:8000/api/research/ws/research/{session_id}
```

**Send:**
```json
{"type": "pause"}
{"type": "resume"}
{"type": "stop"}
```

## SHAP Explainability

Understand why the AI made a trade recommendation:

```bash
GET /api/explainability/{result_id}
GET /api/explainability/session/{session_id}/aggregate
POST /api/explainability/explain {"features": {...}, "regime_vector": {...}}
```

## Meta-Strategies

Combine multiple strategies into a meta-strategy:

| Mode | Description |
|------|-------------|
| `standard` | Single strategy execution |
| `competition` | Multiple strategies compete; best performer promoted |
| `confluence` | Multiple strategies must agree to trade |
| `both` | Competition + Confluence combined |

```bash
# Create meta-strategy
POST /api/meta-strategies
{
  "name": "Multi-Strategy Suite",
  "mode": "competition",
  "strategy_ids": ["strat1", "strat2", "strat3"],
  "scoring_config": {"sharpe": 0.3, "win_rate": 0.2, "profit_factor": 0.2, "max_drawdown": 0.15, "confidence": 0.15}
}

# Get rankings
GET /api/meta-strategies/{id}/rankings
```

## REPL Environment

Execute Python code in a sandboxed environment for custom analysis:

```bash
POST /ai/repl/create
POST /ai/repl/{session_id}/execute {"code": "import statistics; statistics.mean([0.55, 0.62, 0.58])"}
```
