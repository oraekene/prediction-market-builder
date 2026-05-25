# PM Strategy Builder — Comprehensive Manual Test Guide

> **Purpose:** Step-by-step test cases covering every user-facing feature and workflow.
> **Prerequisites:** Backend running (`uvicorn app.main:app --reload --port 8000`), Frontend running (`npm run dev`), SQLite DB initialized.

---

## SECTION 1: AUTHENTICATION & ACCOUNT

### TC-01: Register a new account
1. Navigate to `http://localhost:5173/login`
2. Click "Register" toggle
3. Enter email: `testuser@example.com`
4. Enter password: `TestPass123` (min 8 chars)
5. Enter display name: `Test User`
6. Click "Register"
7. **Verify:** Redirected to `/markets`; logged in as Test User
8. **Verify:** JWT token stored in localStorage key `pm_builder_token`

### TC-02: Duplicate registration rejected
1. Logout, navigate to `/login`
2. Click "Register" toggle
3. Enter same email: `testuser@example.com`
4. Enter password: `TestPass123`
5. Click "Register"
6. **Verify:** Red error message: "Email already registered"
7. **Verify:** Not redirected

### TC-03: Password too short rejected
1. Click "Register" toggle
2. Enter email: `short@example.com`
3. Enter password: `Ab1` (3 chars)
4. Click "Register"
5. **Verify:** Browser validation rejects (minLength=6 attribute on form)
6. **Verify:** Try programmatic: POST `/api/auth/register` with `{"email":"short2@example.com","password":"Ab1"}` -> 400 "Password must be at least 8 characters"

### TC-04: Login with valid credentials
1. Navigate to `/login`
2. Enter email: `testuser@example.com`
3. Enter password: `TestPass123`
4. Click "Sign In"
5. **Verify:** Redirected to `/markets`
6. **Verify:** `GET /api/auth/me` returns `{email: "testuser@example.com", display_name: "Test User"}`

### TC-05: Login with wrong password
1. Navigate to `/login`
2. Enter email: `testuser@example.com`
3. Enter password: `WrongPassword999`
4. Click "Sign In"
5. **Verify:** Red error message: "Invalid credentials"
6. **Verify:** URL stays at `/login`

### TC-06: Token refresh mechanism
1. Login and get both access_token + refresh_token from localStorage
2. Call `POST /api/auth/refresh` with `{"refresh_token": "<refresh_token>"}`
3. **Verify:** Returns new `access_token` and new `refresh_token`
4. **Verify:** Old access_token still works during its expiry window

### TC-07: Token expiry handling
1. Login, wait 61 minutes (or manipulate system clock)
2. Navigate to `/markets`
3. **Verify:** Redirected to `/login`
4. **Verify:** `apiFetch` 401 handler cleared localStorage tokens

### TC-08: Protected routes redirect to login
1. Clear localStorage (`localStorage.clear()`)
2. Navigate to `http://localhost:5173/markets`
3. **Verify:** Redirected to `/login`
4. Test also: `/strategies`, `/analytics`, `/research`, `/paper-trading`, `/meta-strategies`, `/settings`

### TC-09: Logout clears session
1. Login
2. Open browser DevTools -> Application -> Local Storage
3. Note `pm_builder_token` and `pm_builder_user` present
4. Click "Logout" (via sidebar or header)
5. **Verify:** Redirected to `/login`
6. **Verify:** localStorage cleared of both keys

---

## SECTION 2: MARKETS BROWSING

### TC-10: Market list loads successfully
1. Login -> navigate to `/markets`
2. **Verify:** "Loading markets..." appears briefly
3. **Verify:** Market table renders with columns: Market, Platform, Odds, Volume, Close
4. **Verify:** Total Markets stat card shows count > 0
5. **Verify:** Avg Odds shows decimal value (e.g., 0.5000)
6. **Verify:** Total Volume stat card shows value

### TC-11: Market search by keyword
1. Navigate to `/markets`
2. Type "election" in the search input
3. **Verify:** Table filters to show only markets with "election" (case-insensitive) in title
4. **Verify:** "No markets found" appears if no matches
5. **Verify:** Stat cards update to reflect filtered data

### TC-12: Market filtering by category
1. Navigate to `/markets`
2. Click "Politics" category button
3. **Verify:** Only markets with category "Politics" shown
4. Click "Crypto"
5. **Verify:** Only crypto-categorized markets shown
6. Click "All"
7. **Verify:** All markets shown again

### TC-13: Market detail via API
1. Call `GET /api/markets/{id}` where id is a known market ID
2. **Verify:** Returns market data: platform_market_id, title, current_odds, volume, close_time
3. For unknown ID: returns `{"error": "Market not found"}`

### TC-14: Empty search state
1. Navigate to `/markets`
2. Search for `zzzzzxyznonexistent`
3. **Verify:** "No markets found" message displayed
4. **Verify:** "Try a different search or category" sub-message shown

### TC-15: Odds color coding
1. Navigate to `/markets`
2. **Verify:** Markets with odds >= 0.5 show green text
3. **Verify:** Markets with odds < 0.5 show red text

---

## SECTION 3: STRATEGY BUILDER

### TC-16: Strategy list page loads
1. Navigate to `/strategies`
2. **Verify:** "Strategies" heading shown
3. **Verify:** "Create Strategy" button visible
4. **Verify:** StrategyList component renders (may be empty)

### TC-17: Create strategy via API
1. `POST /api/strategies` with body:
```json
{"name": "Test Strategy", "nodes": [{"id": "n1", "type": "market_data"}], "edges": []}
```
2. **Verify:** Returns strategy object with id, status "draft", version 1

### TC-18: Strategy CRUD - List
1. `GET /api/strategies?user_id=default`
2. **Verify:** Returns array of strategies for the user

### TC-19: Strategy CRUD - Get by ID
1. Use ID from TC-17
2. `GET /api/strategies/{id}`
3. **Verify:** Returns full strategy with nodes, edges, risk_profile, status, version

### TC-20: Strategy CRUD - Update
1. `PUT /api/strategies/{id}` with body:
```json
{"name": "Updated Strategy", "risk_profile": {"max_drawdown": 0.1}}
```
2. **Verify:** Returns updated strategy

### TC-21: Strategy CRUD - Delete
1. `DELETE /api/strategies/{id}`
2. **Verify:** Returns `{"status": "deleted"}`
3. `GET /api/strategies/{id}` -> 404

### TC-22: Strategy lifecycle - Deploy
1. Create a draft strategy (status = "draft")
2. `POST /api/strategies/{id}/deploy`
3. **Verify:** Status changes to "active"
4. **Verify:** version_history now has 1 snapshot entry

### TC-23: Strategy lifecycle - Pause
1. `POST /api/strategies/{id}/pause`
2. **Verify:** Status changes to "paused"
3. **Verify:** Error 400 if strategy is not currently "active"

### TC-24: Strategy lifecycle - Resume
1. `POST /api/strategies/{id}/resume`
2. **Verify:** Status changes to "active"
3. **Verify:** Error 400 if strategy is not currently "paused"

### TC-25: Strategy lifecycle - Archive
1. `POST /api/strategies/{id}/archive`
2. **Verify:** Status changes to "archived"
3. **Verify:** version_history snapshot saved

### TC-26: Strategy rollback
1. Deploy strategy -> update it (creates version 2)
2. `POST /api/strategies/{id}/rollback`
3. **Verify:** nodes/edges/risk_profile restored to version 1
4. **Verify:** version decremented, version_history shrunk
5. Error 400 if no history to rollback to

### TC-27: Strategy history
1. Deploy and update strategy several times
2. `GET /api/strategies/{id}/history`
3. **Verify:** Returns `current_version` and `history` array

### TC-28: Strategy templates - CRUD
1. `POST /api/strategies/templates` with `{"name": "Mean Reversion", "config": {"mode": "auto"}}`
2. `GET /api/strategies/templates` -> list all templates
3. `GET /api/strategies/templates/{id}` -> get single template
4. `PUT /api/strategies/templates/{id}` -> update template fields
5. `DELETE /api/strategies/templates/{id}` -> delete template

### TC-29: Apply template to create strategy
1. Create template with full config
2. `POST /api/strategies/templates/{id}/apply`
3. **Verify:** New strategy created from template config
4. **Verify:** Template's `usage_count` incremented

### TC-30: Strategy evaluate endpoint
1. `POST /api/strategies/evaluate` with nodes + edges + market context
2. **Verify:** Returns evaluation result from StrategyEngine
3. **Verify:** 503 if engine not initialized

### TC-31: Visual node canvas
1. Navigate to `/strategies`, click "Create Strategy"
2. **Verify:** NodeCanvas, NodePalette, NodePropertyPanel all render
3. Drag nodes from palette onto canvas
4. **Verify:** Nodes render at dropped positions
5. Connect nodes via port dragging
6. **Verify:** Edge lines appear between connections

---

## SECTION 4: AUTORESEARCH

### TC-32: Research page loads with stats
1. Navigate to `/research`
2. **Verify:** "pi-autoresearch" heading visible
3. **Verify:** Five stat cards: Total Sessions, Kept, Avg Sharpe, Keep Rate, Best Sharpe

### TC-33: Run single research session
1. Navigate to `/research`
2. Click "Run Now"
3. **Verify:** Button shows "Running..." and disables
4. **Verify:** Active Session panel shows hypothesis, backtest progress, TabPFN results
5. **Verify:** On completion, iteration appears in Iteration History table

### TC-34: Run continuous research
1. Click "Continuous"
2. **Verify:** Multiple iterations produced automatically
3. Click "Stop"
4. **Verify:** Research stops; "Stop" button disabled

### TC-35: Session detail and results
1. Click a session in Sessions sidebar
2. **Verify:** Iteration History shows results for that session
3. **Verify:** Columns: #, Hypothesis, Regime, Score, Sharpe, Win Rate, TabPFN, Verdict

### TC-36: SHAP explanation expand/collapse
1. Click a result row in Iteration History
2. **Verify:** SHAP explanation panel expands
3. Click again
4. **Verify:** Panel collapses

### TC-37: Research API - Sessions
1. `GET /api/research/sessions` -> sessions array with status, mode, avg_sharpe
2. `GET /api/research/sessions/{id}` -> full session detail
3. `GET /api/research/sessions/{id}/results?limit=50` -> iteration results

### TC-38: Research API - Stats & Config
1. `GET /api/research/stats` -> aggregate stats
2. `GET /api/research/config` -> current config
3. `PUT /api/research/config?max_concurrent=3&cron_enabled=true` -> update config

### TC-39: Climate & Features
1. `GET /api/research/climate` -> regime + volatility
2. `GET /api/research/features` -> feature importance
3. **Verify:** UI shows Climate & Features panel

### TC-40: RLM Alpha Vector scan
1. Click "Scan" in RLM Alpha Vectors panel
2. **Verify:** POST `/api/research/rlm-scan` called
3. **Verify:** New vector appears in panel
4. `POST /api/research/rlm-scan?source_type=forum&keywords=trump,election` -> returns alpha_vector_id

### TC-41: RLM drift + pipeline
1. `POST /api/research/rlm-drift` -> detects linguistic drift
2. `POST /api/research/rlm-pipeline` -> combined scan + drift
3. `POST /api/research/rlm-text-batch?texts=["a","b"]&query=analyze` -> text analysis

### TC-42: RLM trajectory and state
1. `GET /api/research/rlm-trajectory` -> dspy trajectory
2. `GET /api/research/rlm-state` -> accumulated state
3. `GET /api/research/rlm/trace/{vector_id}` -> full vector trace

### TC-43: Research WebSocket
1. Connect WS to `ws://localhost:8000/api/research/ws/{session_id}`
2. **Verify:** Receives `hypothesis`, `tabpfn_result`, `backtest_progress`, `iteration_complete` events
3. Send `{"type": "pause"}` -> receive `{"type": "paused"}`
4. Send `{"type": "stop"}` -> receive `{"type": "stopped"}`

---

## SECTION 5: PAPER TRADING

### TC-44: Paper trading dashboard
1. Navigate to `/paper-trading`
2. **Verify:** Wallet card: initial ($10,000), current balance, P&L, P&L%
3. **Verify:** Empty state for orders if none exist

### TC-45: Place paper order
1. Place order via API: `POST /api/paper/orders`
2. **Verify:** Order appears with status PENDING
3. **Verify:** Wallet balance adjusts

### TC-46: Cancel paper order
1. `DELETE /api/paper/orders/{order_id}`
2. **Verify:** Status changes to cancelled
3. **Verify:** Wallet balance restored

### TC-47: Wallet reset
1. `POST /api/paper/wallet/reset`
2. **Verify:** Balance returns to $10,000

### TC-48: Trading mode switch
1. `POST /api/paper/trading-mode {"mode": "paper"}`
2. `POST /api/paper/trading-mode {"mode": "live"}`
3. **Verify:** Warning if no API keys configured
4. `POST /api/paper/trading-mode {"mode": "invalid"}` -> 400

### TC-49: Kill switch
1. `POST /api/paper/kill-switch`
2. **Verify:** All positions closed, all orders cancelled

### TC-50: Strategy comparison
1. `GET /api/paper/compare?strategy_ids=a,b`
2. **Verify:** Returns comparison metrics

### TC-51: Connection test
1. `GET /api/paper/connection-test?platform=polymarket`
2. **Verify:** Returns platform + available boolean

---

## SECTION 6: ANALYTICS & RISK

### TC-52: Analytics summary
1. Navigate to `/analytics`
2. **Verify:** Four stat cards: Total Trades, Win Rate, Winning Trades, P&L

### TC-53: Risk dashboard
1. Navigate to `/analytics`
2. **Verify:** RiskDashboard: VaR, ES, Max DD, Current DD, Concentration, Volatility

### TC-54: Risk API endpoints
1. `GET /api/risk/summary` -> all risk metrics
2. `GET /api/risk/var?confidence=0.95` -> VaR breakdown
3. `GET /api/risk/correlation` -> pairwise correlations
4. `GET /api/risk/drawdown` -> drawdown analysis
5. `GET /api/risk/portfolio` -> position-level risk

### TC-55: Backtests section
1. Navigate to `/analytics`
2. **Verify:** "Backtests" section with trade history
3. Empty state: "No backtests recorded yet"

### TC-56: Risk template CRUD + evaluate
1. `POST /api/risk-templates` with name and rules
2. `GET /api/risk-templates` -> list
3. `PUT /api/risk-templates/{id}` -> update
4. `DELETE /api/risk-templates/{id}` -> delete
5. `POST /api/risk-templates/{id}/evaluate` -> test trade against template

---

## SECTION 7: META-STRATEGIES

### TC-57: Meta-strategies list
1. Navigate to `/meta-strategies`
2. **Verify:** List or empty state
3. `GET /api/meta-strategies` -> returns array

### TC-58: Create meta-strategy
1. `POST /api/meta-strategies {"name": "Tournament", "mode": "competition"}`
2. **Verify:** Returns meta-strategy with id

### TC-59: Add/remove strategies
1. `POST /api/meta-strategies/{id}/strategies?strategy_id={sid}` -> adds to pool
2. `DELETE /api/meta-strategies/{id}/strategies/{sid}` -> removes from pool

### TC-60: Rankings
1. `GET /api/meta-strategies/{id}/rankings`
2. **Verify:** Sorted rankings with scores and winner indicator

### TC-61: Evaluate promotion
1. `POST /api/meta-strategies/{id}/evaluate`
2. **Verify:** Promoted true/false with reason

### TC-62: Force promote
1. `POST /api/meta-strategies/{id}/force-promote?strategy_id={sid}`
2. **Verify:** current_winner_id updated

### TC-63: Performance
1. `GET /api/meta-strategies/{id}/performance`
2. **Verify:** Total P&L, trades, win rate, per-strategy breakdown

### TC-64: Update and delete
1. `PUT /api/meta-strategies/{id}` -> update fields
2. `DELETE /api/meta-strategies/{id}` -> delete

---

## SECTION 8: CHAT & ORCHESTRATOR

### TC-65: Chat toggle
1. Click floating "Chat" button
2. **Verify:** Chat panel opens (400x500px)
3. **Verify:** Welcome message displayed
4. Click "X"
5. **Verify:** Panel closes

### TC-66: Send chat message
1. Open chat, type message, press Enter
2. **Verify:** User message appears
3. **Verify:** Assistant responds via WebSocket

### TC-67: Chat REST + history
1. `POST /api/chat/message {"message": "Hello"}`
2. `GET /api/chat/history` -> returns conversation
3. `DELETE /api/chat/history` -> clears

### TC-68: Orchestrator message
1. `POST /api/orchestrator/message {"message": "Analyze markets"}`
2. **Verify:** Returns orchestrated response

### TC-69: Orchestrator sessions and health
1. `GET /api/orchestrator/session/{id}` -> state
2. `DELETE /api/orchestrator/session/{id}` -> clear
3. `GET /api/orchestrator/sessions` -> active sessions
4. `GET /api/orchestrator/health` -> component health

### TC-70: Skill creation
1. `POST /api/orchestrator/skill/create {"description": "Analyze election markets"}`
2. **Verify:** Skill created (10+ char description required)
3. `GET /api/orchestrator/skills` -> list skills

### TC-71: Agent spawning
1. `POST /api/orchestrator/spawn {"goal": "Research crypto markets"}`
2. `GET /api/orchestrator/agents` -> list spawned agents
3. `GET /api/orchestrator/traces/{id}` -> agent execution traces

### TC-72: Pipeline and goals
1. `POST /api/orchestrator/pipeline {"message": "Full analysis"}`
2. `GET /api/orchestrator/goals` -> cognitive goals

---

## SECTION 9: PORTFOLIO, TRADES

### TC-73: Portfolio summary
1. `GET /api/portfolio`
2. **Verify:** total_value, total_pnl, active_strategies, total_trades, positions

### TC-74: Trade evaluation
1. `POST /api/trades/evaluate` with risk_profile, market, signal
2. **Verify:** Returns approved + suggested_size or violations

### TC-75: Create trade
1. `POST /api/trades` with full data
2. **Verify:** If risk approved -> trade created (PENDING)
3. **Verify:** If risk rejected -> violations list

### TC-76: List trades
1. `GET /api/trades` -> all trades
2. `GET /api/trades?status=executed` -> filtered

---

## SECTION 10: AI & SEARCH

### TC-77: Agentic search
1. `POST /api/v1/search {"query": "Bitcoin price", "depth": "standard"}`
2. **Verify:** Results with title, url, snippet, content

### TC-78: Search status
1. `GET /api/v1/search/status`
2. **Verify:** Returns status + component checks

### TC-79: Alchemy analysis
1. `POST /ai/alchemy/analyze {"query": "ETH > $5K?"}`
2. **Verify:** Returns cross-domain analysis report
3. `GET /ai/alchemy/history` -> past reports
4. `GET /ai/alchemy/history/{id}` -> single report

### TC-80: REPL sandbox
1. `POST /ai/repl/create` -> session_id
2. `POST /ai/repl/{id}/execute {"code": "2+2"}` -> result
3. `GET /ai/repl/{id}/state` -> session state
4. `DELETE /ai/repl/{id}` -> destroy

### TC-81: Explainability
1. `POST /api/explainability/explain {"features": {"vol": 0.5}}` -> SHAP explanation
2. `GET /api/explainability/{result_id}` -> specific result
3. `GET /api/explainability/session/{id}/aggregate` -> session aggregate

---

## SECTION 11: SYSTEM

### TC-82: Health and metrics
1. `GET /health` -> `{"status": "ok"}`
2. `GET /metrics` -> Prometheus text format

### TC-83: Rate limiting
1. Send 61+ requests within 1 minute
2. **Verify:** 61st request -> 429 Too Many Requests

### TC-84: Security headers
1. Check response headers:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security
   - Referrer-Policy: strict-origin-when-cross-origin
   - X-Request-ID present

### TC-85: Settings page
1. Navigate to `/settings`
2. **Verify:** Profile, API Keys, Trading Mode, Safety Limits, Connection sections

### TC-86: CORS validation
1. From `http://localhost:3000`, call `GET /api/markets`
2. **Verify:** CORS error
3. From `http://localhost:5173`, same call succeeds

---

## SECTION 12: ERROR EDGE CASES

### TC-87: Backend unreachable
1. Stop backend
2. Refresh frontend
3. **Verify:** Error states shown on pages
4. Restart backend
5. **Verify:** Operation resumes

### TC-88: Invalid token
1. Set localStorage `pm_builder_token` = "invalid"
2. Refresh
3. **Verify:** Redirected to login

### TC-89: Empty database states
1. Fresh DB: all pages show appropriate empty states

### TC-90: 503 for uninitialized services
1. Access research endpoints before scheduler init -> 503

### TC-91: Concurrency limit
1. Start max research sessions (default 2)
2. Attempt another -> 429

### TC-92: Confluence threshold
1. Meta-strategy with CONFLUENCE mode, threshold=3
2. Evaluate with < 3 agreeing strategies
3. **Verify:** Not promoted, reason "Confluence not met"

### TC-93: Probation period
1. Set probation_hours > 0 in promotion_config
2. Force promote, then immediately try to auto-promote a different strategy
3. **Verify:** Probation blocks the promotion

---

## TC COMPLETION TRACKER

| Section | Count | Done |
|---------|-------|------|
| 1 - Auth | 9 | |
| 2 - Markets | 6 | |
| 3 - Strategies | 16 | |
| 4 - Research | 12 | |
| 5 - Paper Trading | 8 | |
| 6 - Analytics & Risk | 5 | |
| 7 - Meta-Strategies | 8 | |
| 8 - Chat & Orchestrator | 8 | |
| 9 - Portfolio & Trades | 4 | |
| 10 - AI & Search | 5 | |
| 11 - System | 5 | |
| 12 - Error Edge Cases | 7 | |
| **TOTAL** | **93** | |

---

Instructions: Check each TC box as you complete the test. Note failures separately. Use browser console, curl, Postman, or any HTTP client for API-only tests.
