# API Reference — Prediction Market Strategy Builder

Base URL: `http://localhost:8000`  
Version: `0.1.0`  
Auth: JWT Bearer tokens (`Authorization: Bearer <token>`)

---

## Authentication

### POST /api/auth/register

Create a new user account.

```json
// Request
{"email": "user@example.com", "password": "securepass123", "display_name": "User"}
// Response 200
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "user_id": "uuid"}
```

### POST /api/auth/login

Authenticate with credentials.

```json
// Request
{"email": "user@example.com", "password": "securepass123"}
// Response 200
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "user_id": "uuid"}
// Response 401
{"detail": "Invalid credentials"}
```

### POST /api/auth/refresh

Exchange a refresh token for new access + refresh tokens.

```json
// Request
{"refresh_token": "eyJ..."}
// Response 200
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "user_id": "uuid"}
```

### GET /api/auth/me

Get current user profile.

```json
// Response 200
{"id": "uuid", "email": "user@example.com", "display_name": "User",
 "has_polymarket_key": false, "has_kalshi_key": false}
```

---

## Markets

### GET /api/markets

List markets across all platforms.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `platform` | str | — | Filter: polymarket, kalshi, drift |
| `category` | str | — | Filter by category |
| `search` | str | — | Full-text search |
| `min_volume` | float | — | Minimum volume filter |
| `limit` | int | 100 | Results per page (max 500) |
| `offset` | int | 0 | Pagination offset |

```json
// Response 200
{"markets": [{"id": "str", "platform": "polymarket", "platform_market_id": "str",
   "title": "Will BTC hit $100k?", "current_odds": 0.65, "volume": 5000000,
   "status": "open", "close_time": "2026-06-01T00:00:00Z"}],
 "total": 42}
```

### GET /api/markets/{market_id}

Get a single market by ID.

```json
// Response 200
{"id": "str", "platform": "polymarket", "title": "Will BTC hit $100k?",
 "current_odds": 0.65, "bid": 0.64, "ask": 0.66, ...}
// Response 404
{"error": "Market not found"}
```

---

## Strategies

### GET /api/strategies

List strategies. Query: `user_id` (default: "default").

### POST /api/strategies

Create a new strategy.

```json
// Request
{"user_id": "default", "name": "BTC Momentum", "description": "...",
 "mode": "node", "nodes": [...], "edges": [...],
 "risk_profile": {"max_position_size": 0.2, "max_drawdown": 0.15, "stop_loss": 0.1,
   "kelly_fraction": 0.25, "max_correlation": 0.7, "min_confidence": 0.6}}
```

### GET /api/strategies/{id}

Get strategy by ID. Returns 404 if not found.

### PUT /api/strategies/{id}

Update strategy fields. Partial update — only send changed fields.

### DELETE /api/strategies/{id}

Delete a strategy. Returns `{"status": "deleted"}`.

### POST /api/strategies/{id}/deploy

Activate a strategy. Creates a version snapshot.

### POST /api/strategies/{id}/pause

Pause an active strategy. Requires status `active`.

### POST /api/strategies/{id}/resume

Resume a paused strategy. Requires status `paused`.

### POST /api/strategies/{id}/archive

Archive a strategy.

### POST /api/strategies/{id}/rollback

Rollback to previous version. Requires non-empty `version_history`.

### GET /api/strategies/{id}/history

Get version history. Returns `{"current_version": int, "history": [...]}`.

### POST /api/strategies/evaluate

Evaluate strategy nodes against market data.

```json
// Request
{"nodes": [...], "edges": [...], "market_id": "str", "market": {...}}
// Response
{"approved": true, "suggested_size": 0.05, "violations": []}
```

### Strategy Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/strategies/templates` | List templates |
| POST | `/api/strategies/templates` | Create template |
| GET | `/api/strategies/templates/{id}` | Get template |
| PUT | `/api/strategies/templates/{id}` | Update template |
| DELETE | `/api/strategies/templates/{id}` | Delete template |
| POST | `/api/strategies/templates/{id}/apply` | Create strategy from template |

---

## Chat

### POST /api/chat/message

Send a message to the AI assistant.

```json
// Request
{"message": "Analyze BTC markets", "user_id": "default"}
// Response
{"response": "Analysis...", "strategy": null}
```

### GET /api/chat/history

Get chat history. Query: `user_id` (default: "default").

### DELETE /api/chat/history

Clear chat history. Query: `user_id` (default: "default").

### WebSocket /ws/chat

```
Connection: ws://host:8000/ws/chat

Send:  {"payload": {"content": "message", "user_id": "default"}}
Recv:  {"type": "chat_response", "content": "response"}
```

---

## Paper Trading

### GET /api/paper/wallet

Get wallet with open positions and recent trades. Query: `user_id` (default: "default").

### POST /api/paper/wallet/reset

Reset wallet balance. Query: `user_id` (default: "default").

### POST /api/paper/orders

Place an order (paper or live mode).

```json
// Request
{"wallet_id": "str", "platform": "polymarket", "market_id": "str",
 "market_title": "str", "side": "buy", "amount": 100, "price": 0.55,
 "strategy_id": "str", "risk_profile": {...}, "mode": "paper"}
// Response (success)
{"success": true, "order": {"id": "str", "platform": "polymarket", ...},
 "wallet_balance": 9900.0, "slippage": 0.001, "mode": "paper"}
// Response (failure — need confirmation)
{"success": false, "error": "Live trading not confirmed", "need_confirmation": true}
// Response (failure — risk)
{"success": false, "error": "Risk check failed", "violations": [...]}
```

### GET /api/paper/orders

List orders. Query: `status`, `wallet_id`, `limit` (default 50, max 200).

### DELETE /api/paper/orders/{order_id}

Cancel an order.

### GET /api/paper/performance

Get performance metrics. Query: `strategy_id`, `user_id`.

### POST /api/paper/sync-resolutions

Sync market resolutions.

```json
// Request
{"resolutions": [{"market_id": "str", "platform": "str", "outcome": "yes"}]}
```

### GET /api/paper/metrics/{metric}

Get a specific metric. Path: metric name. Query: `user_id`, `window` (0-5000).

### GET /api/paper/compare

Compare strategies. Query: `strategy_ids` (comma-separated, required).

### POST /api/paper/confirm-live

Confirm live trading mode. Requires authentication.

### POST /api/paper/kill-switch

Emergency stop — cancel all open orders. Query: `user_id` (default: "default").

### GET /api/paper/connection-test

Test exchange connectivity. Query: `platform` (default: "polymarket").

### POST /api/paper/trading-mode

Set trading mode. Requires authentication.

```json
// Request
{"mode": "live"}
// Response
{"mode": "live"}
// Warning if no keys configured
{"mode": "live", "warning": "No exchange API keys configured. Live trading will fail."}
```

---

## Trades

### POST /api/trades/evaluate

Evaluate a trade against a risk profile without saving.

```json
// Request
{"risk_profile": {...}, "market": {...}, "signal": {...}, "portfolio": {...}}
```

### POST /api/trades

Create a trade after risk evaluation.

### GET /api/trades

List trades. Query: `status`, `limit` (default 50).

---

## Risk

### GET /api/risk/summary

```json
// Response
{"var_95": 150.0, "es_95": 220.0, "max_drawdown": 0.12,
 "current_drawdown": 0.03, "concentration": 0.45, "portfolio_volatility": 0.18}
```

### GET /api/risk/var

Query: `confidence` (0.5–0.999, default 0.95).

```json
// Response
{"historical": 150.0, "parametric": 145.0, "tabpfn": 140.0, "confidence": 0.95}
```

### GET /api/risk/correlation

```json
// Response
{"pairs": [{"asset_a": "BTC", "asset_b": "ETH", "correlation": 0.82}], "total_assets": 5}
```

### GET /api/risk/drawdown

```json
// Response
{"current_drawdown": 0.03, "peak_capital": 10500, "current_capital": 10150, "max_drawdown": 0.12}
```

### GET /api/risk/portfolio

```json
// Response
{"positions": [{"market_id": "str", "size": 500, "var_contribution": 0.3, "concentration_pct": 0.15}]}
```

---

## Risk Templates

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/risk-templates` | Create risk template |
| GET | `/api/risk-templates` | List templates |
| GET | `/api/risk-templates/{id}` | Get template |
| PUT | `/api/risk-templates/{id}` | Update template |
| DELETE | `/api/risk-templates/{id}` | Delete template |
| POST | `/api/risk-templates/{id}/evaluate` | Evaluate trade against template |

---

## Portfolio

### GET /api/portfolio

```json
// Response
{"summary": {"total_value": 10000, "total_pnl": 250, "active_strategies": 3,
  "total_trades": 45, "win_rate": 0.62},
 "positions": [{"market_id": "str", "platform": "polymarket", "side": "buy",
   "amount": 100, "price": 0.55, "pnl": 15.5, "executed_at": "..."}]}
```

---

## Analytics

### GET /api/analytics/summary

```json
// Response
{"total_trades": 45, "winning_trades": 28, "total_pnl": 250.0, "win_rate": 0.622}
```

### GET /api/analytics/backtests

```json
// Response
{"backtests": [{"name": "All Trades", "trades": [...]}]}
```

---

## Research

### POST /api/research/run

Trigger a research run. Query: `strategy_id`, `preset` (default: "sharpe_max").

### POST /api/research/stop

Stop a research session. Query: `session_id` (required).

### POST /api/research/sessions

Create a research session.

```json
// Request
{"strategy_id": "str", "mode": "manual", "preset": "sharpe_max"}
```

### GET /api/research/sessions

List sessions. Query: `limit` (default 20, max 100).

### GET /api/research/sessions/{id}

Get session details.

### GET /api/research/sessions/{id}/results

Get experiment results. Query: `limit` (default 50, max 200).

### GET /api/research/stats

Aggregate research statistics.

### GET /api/research/config

Get research configuration.

### PUT /api/research/config

Update research config via query params: `preset`, `max_concurrent`, `cron_enabled`, `cron_interval`, `continuous_enabled`, `max_hypotheses`, `enable_genetic_optimization`.

### GET /api/research/climate

Market climate assessment.

### GET /api/research/features

TabPFN feature importance.

### GET /api/research/alpha-vectors

List RLM alpha vectors. Query: `limit` (default 10, max 50).

### WebSocket /api/research/ws/research/{session_id}

```
Send: {"type": "pause"} | {"type": "resume"} | {"type": "stop"}
Recv: Real-time research events
```

RLM endpoints: `rlm-scan`, `rlm-drift`, `rlm-text-batch`, `rlm-pipeline`, `rlm-trajectory`, `rlm-state`, `rlm/trace/{vector_id}`.

---

## Meta-Strategies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/meta-strategies` | List meta-strategies |
| POST | `/api/meta-strategies` | Create meta-strategy |
| GET | `/api/meta-strategies/{id}` | Get meta-strategy |
| PUT | `/api/meta-strategies/{id}` | Update |
| DELETE | `/api/meta-strategies/{id}` | Delete |
| POST | `/api/meta-strategies/{id}/strategies` | Add strategy to pool |
| DELETE | `/api/meta-strategies/{id}/strategies/{sid}` | Remove strategy |
| GET | `/api/meta-strategies/{id}/rankings` | Strategy rankings |
| POST | `/api/meta-strategies/{id}/evaluate` | Run promotion evaluation |
| POST | `/api/meta-strategies/{id}/force-promote` | Force promote strategy |
| GET | `/api/meta-strategies/{id}/performance` | Aggregate performance |

---

## Orchestrator

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/orchestrator/message` | Process message through AI orchestrator |
| GET | `/api/orchestrator/session/{id}` | Get session state |
| DELETE | `/api/orchestrator/session/{id}` | Clear session |
| GET | `/api/orchestrator/health` | Watchdog health check |
| GET | `/api/orchestrator/sessions` | List active sessions |
| POST | `/api/orchestrator/skill/create` | Create a new skill |
| GET | `/api/orchestrator/skills` | List skills |
| POST | `/api/orchestrator/spawn` | Spawn a sub-agent |
| GET | `/api/orchestrator/agents` | List active agents |
| GET | `/api/orchestrator/traces/{sid}` | Get traces |
| GET | `/api/orchestrator/goals` | List cognitive goals |
| POST | `/api/orchestrator/pipeline` | Run full pipeline |

---

## Other Services

### Alchemy (Cross-Domain Analysis)

`/ai/alchemy/*` — Cross-domain analysis across markets, news, macros, legal, on-chain, social, and memory.

### Explainability

`/api/explainability/*` — SHAP-based model explanations, feature importance, and aggregate session analysis.

### REPL

`/ai/repl/*` — Sandboxed Python execution environment for custom analysis.

### Agentic Search

`/api/v1/search/*` — Multi-engine web search with configurable depth (quick/standard/deep).

### Health & Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{"status": "ok", "version": "0.1.0"}` |
| GET | `/metrics` | Prometheus metrics (text/plain) |
