# PM Strategy Builder — Manual Test Guide Vol. 2: Edges, Security & Integration

> **Purpose:** 93 additional test cases covering attack surfaces, input boundaries, state machines, concurrency, stress, integration flows, and degradation modes. Completely disjoint from Vol. 1 (TEST_GUIDE.md).

---

## SECTION A: SECURITY & ABUSE (TC-94 — TC-103)

### TC-94: SQL injection in market search
1. Navigate to `/markets`
2. Search for `' OR 1=1 --`
3. **Verify:** No error, just returns matching results (or empty if no match)
4. Search for `'; DROP TABLE users; --`
5. **Verify:** No database corruption, system still functional
6. **Verify:** Login still works after injection attempt

### TC-95: XSS in strategy name
1. `POST /api/strategies` with `name: "<script>alert('XSS')</script>"`
2. Navigate to `/strategies`
3. **Verify:** Name displayed as escaped text, no script execution
4. **Verify:** Check DOM — `<script>` tag is not injected, shown as `&lt;script&gt;`

### TC-96: XSS in chat messages
1. Open chat panel
2. Send message: `<img src=x onerror=alert(1)>`
3. **Verify:** No alert executed
4. Send message: `<b>bold text</b>`
5. **Verify:** If HTML is rendered, only safe tags; if plaintext, shown as-is

### TC-97: IDOR — Access another user's strategy
1. Register User A, create strategy, note its ID
2. Register User B (different account)
3. `GET /api/strategies/{UserA_strategy_id}` with User B's token
4. **Verify:** Either 404 not found (proper isolation) or strategy returned but strategy.user_id shows User A
5. **Verify:** Cannot modify or delete User A's strategy as User B

### TC-98: IDOR — Access another user's trades
1. Create trade as User A
2. `GET /api/trades` as User B
3. **Verify:** User B cannot see User A's trades

### TC-99: JWT none-algorithm attack
1. Encode a JWT manually: header=`{"alg":"none"}`, payload=`{"sub":"some-id","type":"access"}`, signature=empty
2. Send `Authorization: Bearer <crafted_token>` to any protected endpoint
3. **Verify:** Returns 401, not 200
4. **Verify:** Server logs show attempted signature bypass

### TC-100: Mass assignment protection
1. `POST /api/strategies` with extra fields: `is_admin=true, role="superuser"`
2. `GET /api/strategies/{id}`
3. **Verify:** Extra fields are NOT persisted to the model
4. Repeat for `POST /api/trades`, `POST /api/meta-strategies`

### TC-101: Directory traversal in RLM scan path
1. `POST /api/research/rlm-scan?source_path=../../etc/passwd`
2. **Verify:** Returns error or sanitized path, not contents of `/etc/passwd`
3. Try: `source_path=..\\..\\..\\Windows\\System32\\config`
4. **Verify:** Path traversal prevented

### TC-102: Rate limit on auth endpoints
1. Rapidly call `POST /api/auth/login` with wrong password 20+ times in 10 seconds
2. **Verify:** 429 Too Many Requests after exceeding rate limit
3. **Verify:** Correct login still works after rate limit resets (no permanent lockout)

### TC-103: Valid email validation
1. `POST /api/auth/register` with `email: "not-an-email"`
2. **Verify:** 422 Validation error (EmailStr validation)
3. Try: `email: "test@localhost"`, `email: ""`, `email: "a@b.c"`
4. **Verify:** Only valid email formats accepted

---

## SECTION B: INPUT BOUNDARY & VALIDATION (TC-104 — TC-116)

### TC-104: Strategy name boundary — 1 char
1. `POST /api/strategies` with `name: "A"`
2. **Verify:** Created successfully (no minimum length enforced)
3. `GET /api/strategies/{id}` — name is "A"

### TC-105: Strategy name boundary — 1000 chars
1. `POST /api/strategies` with `name: "A" * 1000`
2. **Verify:** Created successfully
3. `GET /api/strategies/{id}` — name is full 1000 chars

### TC-106: Strategy description — null vs empty vs very long
1. `POST /api/strategies` with `description: null`
2. `POST /api/strategies` with `description: ""`
3. `POST /api/strategies` with `description: "X" * 5000`
4. **Verify:** All created without error; null stored as null

### TC-107: Nodes/edges boundary — empty arrays
1. `POST /api/strategies` with `nodes: [], edges: [], risk_profile: {}`
2. **Verify:** Created as empty strategy

### TC-108: Nodes/edges — 200 nodes, 500 edges
1. Build large JSON with 200 nodes and 500 edges
2. `POST /api/strategies` with this payload
3. **Verify:** Created successfully (check request body size limit isn't hit)
4. `GET /api/strategies/{id}` — nodes/edges returned correctly

### TC-109: Risk profile — extreme values
1. `PUT /api/strategies/{id}` with `risk_profile: {"max_drawdown": 999, "stop_loss": -999, "kelly_fraction": 5000}`
2. **Verify:** Accepted (no server-side validation)
3. **Verify:** Evaluate endpoint handles extreme values without crashing

### TC-110: Trade amount — zero and negative
1. `POST /api/trades` with `amount: 0`
2. **Verify:** Trade created (amount=0) or rejected
3. `POST /api/trades` with `amount: -100`
4. **Verify:** Rejected or handled gracefully

### TC-111: Trade price — boundary (0 and 1.0)
1. `POST /api/paper/orders` with `price: 0`
2. **Verify:** Order created at price 0 (edge case)
3. `POST /api/paper/orders` with `price: 1.0`
4. **Verify:** Order created at price 1.0

### TC-112: Market list — limit boundary
1. `GET /api/markets?limit=0`
2. **Verify:** Returns 0 markets (or clamped to minimum)
3. `GET /api/markets?limit=500`
4. **Verify:** Returns up to 500 markets
5. `GET /api/markets?limit=501`
6. **Verify:** Returns max 500 (le=500 constraint), or error

### TC-113: Market list — offset boundary
1. `GET /api/markets?offset=0` — returns from start
2. `GET /api/markets?offset=999999` — returns empty array, total is still accurate
3. **Verify:** No crash or error

### TC-114: Research config — extreme values
1. `PUT /api/research/config?max_concurrent=0`
2. **Verify:** Clamped to 1
3. `PUT /api/research/config?max_concurrent=10`
4. **Verify:** Clamped to 5
5. `PUT /api/research/config?max_hypotheses=4`
6. **Verify:** Clamped to 5
7. `PUT /api/research/config?max_hypotheses=300`
8. **Verify:** Clamped to 200

### TC-115: RLM scan — empty directory
1. Create an empty directory `./data/archives_empty`
2. `POST /api/research/rlm-scan?source_path=./data/archives_empty`
3. **Verify:** Returns successful scan with 0 tokens
4. **Verify:** Alpha vector created

### TC-116: RLM scan — non-existent path
1. `POST /api/research/rlm-scan?source_path=./data/nonexistent`
2. **Verify:** Returns error or handled gracefully (no 500 crash)

---

## SECTION C: STATE MACHINE & TRANSITIONS (TC-117 — TC-124)

### TC-117: Strategy — deploy on already-active strategy
1. Deploy strategy (status=active)
2. `POST /api/strategies/{id}/deploy` again
3. **Verify:** Returns strategy as-is, no error, no duplicate version snapshot

### TC-118: Strategy — pause on draft strategy
1. Create draft strategy
2. `POST /api/strategies/{id}/pause`
3. **Verify:** Error 400 "Only active strategies can be paused"

### TC-119: Strategy — archive on paused strategy
1. Deploy → pause → archive
2. **Verify:** Full lifecycle completes without errors
3. **Verify:** Cannot resume after archive (or verify archival is terminal)

### TC-120: Strategy — rollback with no history
1. Create fresh strategy (never deployed)
2. `POST /api/strategies/{id}/rollback`
3. **Verify:** Error 400 "No previous version to rollback to"

### TC-121: Research session — stop already stopped session
1. Run research → stop → status=completed
2. `POST /api/research/stop?session_id={id}`
3. **Verify:** 404 or graceful — already stopped

### TC-122: Research session — resume completed session
1. Run research → session completes naturally
2. Via WS: send `{"type": "resume"}` for the completed session
3. **Verify:** Check behavior — does it create a new iteration or reject?

### TC-123: Paper order — cancel already filled order
1. Place order → it gets filled (status=FILLED)
2. `DELETE /api/paper/orders/{id}`
3. **Verify:** Error 400 "Order cannot be cancelled or not found"

### TC-124: Paper order — cancel already cancelled order
1. Cancel order → status=CANCELLED
2. Cancel again
3. **Verify:** Error 400

---

## SECTION D: CONCURRENCY & RACE CONDITIONS (TC-125 — TC-131)

### TC-125: Rapid concurrent strategy updates
1. Create one strategy
2. Fire 10 simultaneous `PUT /api/strategies/{id}` requests with different names
3. **Verify:** All succeed (eventual consistency)
4. **Verify:** Final name is one of the 10, no data corruption

### TC-126: Wallet race — place orders exceeding balance
1. Note wallet balance = $10,000
2. Fire 5 simultaneous `POST /api/paper/orders` each for $4,000
3. **Verify:** At most 2 orders can be placed (2x4,000=8,000 < 10,000)
4. **Verify:** 3rd order is rejected due to insufficient balance
5. **Verify:** No wallet balance goes negative

### TC-127: Wallet reset while orders pending
1. Place a pending order
2. Simultaneously call `POST /api/paper/wallet/reset`
3. **Verify:** Reset completes
4. **Verify:** The pending order is either cancelled or handled gracefully

### TC-128: Multiple research WebSocket connections — same session
1. Open 3 browser tabs to research page, all connected to same session
2. Trigger research run
3. **Verify:** All 3 WS connections receive the same events
4. **Verify:** No duplicate iterations created (broadcast is fan-out, not fan-in)

### TC-129: Rapid create/delete strategy cycle
1. Create strategy → immediately delete → immediately create with same name
2. **Verify:** All operations succeed
3. Repeat 20 times
4. **Verify:** No database constraint violations

### TC-130: Meta-strategy — add and remove strategy simultaneously
1. Fire `POST add` and `DELETE remove` for the same strategy ID at the same time
2. **Verify:** Final state is deterministic (either in pool or not, no corruption)

### TC-131: Concurrent RLM scans
1. Fire 3 simultaneous `POST /api/research/rlm-scan` requests
2. **Verify:** All return successfully
3. **Verify:** 3 unique alpha vectors created

---

## SECTION E: API PARAMETER COMBINATIONS (TC-132 — TC-139)

### TC-132: Markets — all 5 filters combined
1. `GET /api/markets?platform=polymarket&category=crypto&search=bitcoin&min_volume=1000&limit=50&offset=0`
2. **Verify:** All filters applied correctly
3. Change category to "politics" while keeping other params
4. **Verify:** Different result set (intersection of all filters)

### TC-133: Markets — non-existent platform filter
1. `GET /api/markets?platform=nonexistent_platform`
2. **Verify:** Returns empty markets array, total=0

### TC-134: Markets — special characters in search
1. `GET /api/markets?search=100%25+chance`
2. **Verify:** URL-decoded correctly, no error
3. `GET /api/markets?search=🚀+moon`
4. **Verify:** Emoji handled without error

### TC-135: Research — every preset option
1. Try each preset via `POST /api/research/run?preset=sharpe_max`
2. Try: `preset=win_rate`, `preset=sortino`, `preset=calmar`, `preset=profit_factor`
3. **Verify:** Research runs with each preset
4. Try invalid preset: `preset=nonexistent`
5. **Verify:** Falls back to default or returns error

### TC-136: Paper trading — every metric name
1. For each metric: `current_balance`, `total_pnl`, `win_rate`, `avg_rr`, `sharpe`, `sortino`, `calmar`, `max_drawdown`, `profit_factor`, `kelly_optimal`, `edge`, `brier_score`, `trade_count`, `sqn`, `recovery_factor`, `largest_win`, `largest_loss`, `consecutive_wins`, `consecutive_losses`
2. Call `GET /api/paper/metrics/{metric}` for each
3. **Verify:** Each returns appropriate numeric or null value

### TC-137: Paper metrics — window boundary
1. `GET /api/paper/metrics/sharpe?window=0`
2. **Verify:** Returns all-time metric
3. `GET /api/paper/metrics/sharpe?window=5000`
4. **Verify:** Returns metric with window=5000 (or max)
5. `GET /api/paper/metrics/sharpe?window=-1`
6. **Verify:** Handled gracefully (not crashed)

### TC-138: RLM — all source_type options
1. Test each: `source_type=forum`, `source_type=twitter`, `source_type=news`, `source_type=discord`, `source_type=reddit`
2. `POST /api/research/rlm-scan?source_type={type}`
3. **Verify:** Each returns alpha vector with correct source_type

### TC-139: Meta-strategies — all mode values
1. Create meta-strategies with each mode: `competition`, `confluence`, `both`
2. **Verify:** Each created with correct mode
3. Evaluate promotion for each mode
4. **Verify:** Competition mode uses scoring, Confluence mode checks signal agreement, Both mode does both

---

## SECTION F: FRONTEND COMPONENT STATES (TC-140 — TC-150)

### TC-140: MarketTable — loading state
1. Add a deliberate delay (e.g., browser throttle to slow 3G)
2. Navigate to `/markets`
3. **Verify:** "Loading markets..." message displays immediately
4. **Verify:** No partial table rendering during load

### TC-141: MarketTable — error state
1. Stop backend
2. Navigate to `/markets`
3. **Verify:** "Error loading markets" displayed (not infinite spinner, not broken UI)
4. Start backend, refresh
5. **Verify:** Normal data loads

### TC-142: StrategyList — empty state
1. Delete all strategies (or fresh DB)
2. Navigate to `/strategies`
3. **Verify:** Empty state message shown (not blank white area)
4. **Verify:** "Create Strategy" button still visible

### TC-143: ResearchPage — all empty panels
1. Fresh DB, no research run yet
2. Navigate to `/research`
3. **Verify:** "No sessions" in Sessions panel
4. **Verify:** "No active iteration" in Active Session panel
5. **Verify:** "No results yet" in Iteration History
6. **Verify:** "Not available" in Climate panel
7. **Verify:** "No vectors" in RLM Alpha Vectors panel

### TC-144: PaperTrading — empty wallet state
1. Fresh DB
2. Navigate to `/paper-trading`
3. **Verify:** Wallet shows $10,000 initial balance
4. **Verify:** "No orders" or "No recent trades" shown
5. **Verify:** New Order form is functional from this state

### TC-145: Keyboard navigation — Login form
1. Navigate to `/login`
2. Tab through all form fields
3. **Verify:** Focus order: email → password → submit button → toggle link
4. Press Enter on focused Submit
5. **Verify:** Form submits
6. Press Enter on toggle link
7. **Verify:** Switches to Register mode

### TC-146: Keyboard navigation — Strategy canvas
1. Navigate to strategy canvas
2. Tab through: palette items, canvas, property panel
3. **Verify:** All interactive elements reachable via keyboard

### TC-147: Browser back/forward navigation
1. Login → Markets → click Strategy → click Research → click Back (browser)
2. **Verify:** Returns to Strategies
3. Click Forward
4. **Verify:** Returns to Research
5. **Verify:** Each page retains its state (no blank renders)

### TC-148: Deep linking to meta-strategy detail
1. Create meta-strategy, note its ID
2. Navigate directly to `/meta-strategies/{id}`
3. **Verify:** MetaStrategyDetail loads with correct data
4. **Verify:** 404 handled gracefully for non-existent ID

### TC-149: Deep linking to research session
1. Run research, note session ID
2. Navigate directly to route that shows that session's data
3. **Verify:** Session selected and results loaded

### TC-150: Component unmount during async
1. Navigate to `/markets` (triggers fetch)
2. Immediately navigate to `/strategies` before load completes
3. **Verify:** No React errors, no "setState on unmounted component"
4. **Verify:** Strategies page renders correctly

---

## SECTION G: WEBSOCKET DEEP TESTING (TC-151 — TC-157)

### TC-151: WebSocket reconnect — mid-server restart
1. Open chat, send a message, get response
2. Stop backend server
3. **Verify:** ChatWebSocket auto-reconnect timer fires (3-second interval)
4. **Verify:** Console shows reconnect attempts (no crash)
5. Restart backend
6. **Verify:** Connection re-established
7. **Verify:** New messages flow through

### TC-152: WebSocket — large payload
1. Send a chat message with 50,000 characters via `POST /api/chat/message`
2. **Verify:** Message accepted
3. **Verify:** WS delivers the large response back (potentially truncated, but not crashed)

### TC-153: WebSocket — binary frame
1. Send binary data to `ws://localhost:8000/ws/chat`
2. **Verify:** Server doesn't crash (graceful handling of non-JSON)

### TC-154: WebSocket — JSON with circular reference
1. Send `{"type": "chat", "payload": {"self": null}}` but with JSON that has deeply nested structures
2. **Verify:** Server handles without memory overflow

### TC-155: WebSocket — multiple rapid messages
1. Send 50 chat messages in rapid succession (no delay between sends)
2. **Verify:** All messages arrive at server
3. **Verify:** Responses come back for each (may be queued/ordered)

### TC-156: WebSocket — invalid path
1. Connect to `ws://localhost:8000/ws/nonexistent`
2. **Verify:** Connection rejected or 404 (not hanging open)
3. Connect to `ws://localhost:8000/ws/chat/extra/path`
4. **Verify:** Connection rejected

### TC-157: WebSocket — graceful degradation
1. Block WebSocket connections (browser DevTools → Network → WS block)
2. Open chat and send message
3. **Verify:** REST fallback works (if implemented), or message is queued
4. **Verify:** UI doesn't break — shows error/retry state

---

## SECTION H: PERFORMANCE & STRESS (TC-158 — TC-164)

### TC-158: Large market list response
1. Count the number of markets returned by `GET /api/markets?limit=500`
2. **Verify:** Response time < 3 seconds
3. **Verify:** Frontend renders all 500 markets (browser may have perf limits — verify no freeze)

### TC-159: Graph with 100 nodes evaluation
1. Create a strategy with 100 connected nodes
2. `POST /api/strategies/evaluate` with the full graph
3. **Verify:** Evaluation completes within reasonable time (e.g., < 10s)
4. **Verify:** Response is well-structured JSON

### TC-160: Research scheduler stress
1. Fire `POST /api/research/run` 10 times rapidly
2. **Verify:** Only max_concurrent (default 2) start; rest get 429
3. Wait for sessions to complete
4. **Verify:** All eventual runs complete

### TC-161: Database connection pool
1. Fire 50 concurrent API requests to various endpoints
2. **Verify:** All return successfully (no "too many connections" errors)
3. **Verify:** SQLite handles concurrency without `database is locked` errors

### TC-162: Response time baseline
1. Measure response time for each critical endpoint (average of 5 calls):
   - `GET /api/markets` — should be < 5s (external API calls)
   - `GET /api/strategies` — < 500ms
   - `GET /api/research/stats` — < 1s
   - `GET /api/portfolio` — < 500ms
   - `POST /api/strategies/evaluate` — < 3s
2. **Verify:** All within reasonable bounds

### TC-163: Memory leak check — WebSocket
1. Connect to research WS
2. Send 1000 ping messages
3. Monitor browser memory (DevTools → Performance → Memory)
4. **Verify:** No continuous memory growth (stable after initial load)

### TC-164: Memory leak check — chat messages
1. Send 200 chat messages rapidly
2. **Verify:** No memory leak in chat interface

---

## SECTION I: CROSS-FEATURE INTEGRATION FLOWS (TC-165 — TC-174)

### TC-165: Full strategy lifecycle flow
1. Create strategy with Market Data + TabPFN nodes
2. Deploy it (status=active)
3. Go to Research → "Run Now" → research session created
4. Research produces iterations with backtest results
5. Go to Analytics → verify stats reflect research output
6. Go to Paper Trading → place paper order referencing the strategy
7. **Verify:** Every step succeeds, data flows correctly between features

### TC-166: Paper trade → risk calculation → meta-strategy ranking
1. Create 2 strategies
2. Place multiple paper trades for each strategy
3. Create meta-strategy containing both strategies
4. `GET /api/meta-strategies/{id}/rankings`
5. **Verify:** Rankings reflect actual trade performance from paper trades
6. **Verify:** Winning strategy has higher score

### TC-167: RLM scan → alpha vector → research
1. Run RLM scan with keywords related to prediction markets
2. Verify alpha vector created
3. Run research session
4. **Verify:** Research scheduler picks up the alpha vector (check session's `rlm_alpha_vector_id`)

### TC-168: Chat → orchestrator → agent spawn → tool execution
1. Send orchestrator message requesting market analysis
2. **Verify:** Agent spawned (check `/api/orchestrator/agents`)
3. **Verify:** Agent has tools (search, web, etc.)
4. Check traces at `/api/orchestrator/traces/{session_id}`
5. **Verify:** Contains agent execution history

### TC-169: Research → SHAP explainability → analytics
1. Run research to get results with SHAP explanations
2. Click result row to expand SHAP explanation
3. **Verify:** Feature importance chart renders correctly
4. `GET /api/explainability/session/{id}/aggregate`
5. **Verify:** Aggregate explanation matches individual explanations

### TC-170: Strategy template → apply → evaluate
1. Create template with full strategy config
2. Apply template → new strategy created
3. Evaluate the new strategy against a market
4. **Verify:** Template-to-evaluation pipeline works end-to-end

### TC-171: Trading mode switch → connection test → live trade flag
1. Set trading mode to "live"
2. Check connection test
3. Verify confirm-live endpoint behavior
4. Switch back to "paper"
5. **Verify:** Kill switch available for emergency stop

### TC-172: Multi-platform market aggregation
1. `GET /api/markets` — verify markets from Polymarket are returned
2. If Kalshi connector is functional: verify Kalshi markets also appear
3. **Verify:** Markets from different platforms are merged into one list
4. **Verify:** Each market has correct `platform` field

### TC-173: Risk profile → trade evaluation → trade creation
1. Set strict risk profile via template
2. Evaluate trade with different signals (some passing, some failing)
3. Create trade when approved
4. Verify trade rejected when risk violations exist
5. **Verify:** Risk rules actually enforced (not just advisory)

### TC-174: Skill creation → skill listing → agent using skill
1. Create skill via orchestrator
2. Verify skill appears in `/api/orchestrator/skills`
3. Spawn an agent with specific toolset
4. **Verify:** Agent can access the created skill (if skill system integrates with agent tool registry)

---

## SECTION J: OPTIONAL DEPENDENCY DEGRADATION (TC-175 — TC-182)

### TC-175: SHAP unavailable — graceful explainability
1. If SHAP is not installed (verify by checking logs for "shap not installed")
2. `POST /api/explainability/explain`
3. **Verify:** Returns 503 "Explainability service not available"
4. **Verify:** No 500 crash
5. `GET /api/explainability/{result_id}`
6. **Verify:** Returns `{"explanation": null, "message": "No SHAP explanation available"}`

### TC-176: ChromaDB unavailable — strategy evaluation fallback
1. Stop/disable ChromaDB
2. `POST /api/strategies/evaluate`
3. **Verify:** Evaluation works (ChromaDBManager fallback doesn't crash the route)
4. Search for errors in backend logs

### TC-177: TabPFN not available — research continues
1. If TabPFN model not loaded (check logs)
2. `POST /api/research/run`
3. **Verify:** Research session starts and produces iterations
4. **Verify:** TabPFN columns in results show null/0 (not crash)

### TC-178: Camoufox/browser not available — text-only search
1. `POST /api/v1/search` with depth=deep (requires browser for JS pages)
2. **Verify:** Falls back to text-only extraction (no crash)
3. `GET /api/v1/search/status`
4. **Verify:** Shows browser as unavailable

### TC-179: Hermes unavailable — orchestrator graceful degradation
1. Stop/interrupt Hermes service
2. `POST /api/orchestrator/message`
3. **Verify:** Returns error response (not 500 crash)
4. `GET /api/orchestrator/health`
5. **Verify:** Shows Hermes as unhealthy

### TC-180: Encryption key missing — auth still works
1. Remove encryption_key from .env
2. Restart backend
3. **Verify:** Warning logged but server starts
4. **Verify:** Auth endpoints still functional (login, register, token)

### TC-181: DuckDB unavailable — analytics still works
1. If DuckDB not available
2. `GET /api/analytics/summary`
3. **Verify:** Returns data from SQLite (fallback path)

### TC-182: Redis unavailable — rate limiting falls back
1. Stop Redis (if running separately)
2. Send many requests
3. **Verify:** Rate limiting still works (in-memory fallback)
4. **Verify:** No crash due to missing Redis connection

---

## SECTION K: DATABASE & PERSISTENCE (TC-183 — TC-187)

### TC-183: Database migration — alembic
1. Run `alembic upgrade head`
2. **Verify:** All migrations apply without error
3. `alembic current` — shows head revision
4. `alembic downgrade -1` then `alembic upgrade head`
5. **Verify:** Rollback and re-apply works

### TC-184: Unique constraint violations
1. Register same email twice → verify 2nd attempt blocked
2. Create duplicate tokens if unique constraints exist
3. **Verify:** App handles constraint violations gracefully (not raw DB errors exposed to user)

### TC-185: Clean database restart
1. Delete `pmbuilder.db`
2. Restart backend
3. **Verify:** Tables auto-created via `create_tables()` lifespan event
4. **Verify:** App starts without errors
5. Register, create a strategy
6. **Verify:** Full functionality on fresh DB

### TC-186: Data persistence across restarts
1. Create strategy, place trades, run research
2. Restart backend
3. `GET /api/strategies` — strategy persists
4. `GET /api/portfolio` — trades persist
5. `GET /api/research/stats` — research stats persist

### TC-187: Foreign key integrity
1. Create a strategy, note its id
2. Create trades referencing this strategy_id
3. Delete the strategy
4. **Verify:** Trades still exist (or constraint prevents deletion, or cascade deletes trades)
5. **Verify:** No orphaned references pointing to non-existent records

---

## SECTION L: DOCKER & INFRASTRUCTURE (TC-188 — TC-193)

### TC-188: Backend Docker build
1. From `prediction-market-builder/backend/`, run `docker build -t pm-builder-backend .`
2. **Verify:** Build completes without errors
3. **Verify:** Image size is reasonable (check Dockerfile for multi-stage)

### TC-189: Frontend Docker build
1. From `prediction-market-builder/frontend/`, run `docker build -t pm-builder-frontend .`
2. **Verify:** Build completes
3. **Verify:** Nginx/serve stage works

### TC-190: Docker container — backend starts
1. `docker run -p 8000:8000 -v ./pmbuilder.db:/app/pmbuilder.db pm-builder-backend`
2. **Verify:** Server starts, `/health` returns 200
3. Stop container

### TC-191: Docker environment variables
1. Run backend container WITHOUT .env file
2. **Verify:** Server starts with defaults (logs may show warnings for missing SECRET_KEY)
3. Run with `-e SECRET_KEY=test123` override
4. **Verify:** Auth works with the provided key

### TC-192: Docker volume persistence
1. Run container with volume mount for database
2. Register user, create strategy (inside container)
3. Stop container
4. Restart container with same volume
5. **Verify:** User and strategy persist from previous run

### TC-193: Docker compose (if compose file exists)
1. Run `docker-compose up`
2. **Verify:** Backend and frontend both start
3. **Verify:** Frontend can reach backend (api proxy works)
4. `docker-compose down`
5. **Verify:** Clean shutdown

---

## TC COMPLETION TRACKER — VOLUME 2

| Section | Test IDs | Count | Done |
|---------|----------|-------|------|
| A — Security & Abuse | TC-094 — TC-103 | 10 | |
| B — Input Boundary & Validation | TC-104 — TC-116 | 13 | |
| C — State Machine & Transitions | TC-117 — TC-124 | 8 | |
| D — Concurrency & Race Conditions | TC-125 — TC-131 | 7 | |
| E — API Parameter Combinations | TC-132 — TC-139 | 8 | |
| F — Frontend Component States | TC-140 — TC-150 | 11 | |
| G — WebSocket Deep Testing | TC-151 — TC-157 | 7 | |
| H — Performance & Stress | TC-158 — TC-164 | 7 | |
| I — Cross-Feature Integration | TC-165 — TC-174 | 10 | |
| J — Dependency Degradation | TC-175 — TC-182 | 8 | |
| K — Database & Persistence | TC-183 — TC-187 | 5 | |
| L — Docker & Infrastructure | TC-188 — TC-193 | 6 | |
| **TOTAL** | **TC-094 — TC-193** | **100** | |

---

## COMBINED TRACKER — VOLUMES 1 + 2

| Source | Count |
|--------|-------|
| Volume 1 (TEST_GUIDE.md) | 93 |
| Volume 2 (TEST_GUIDE_2.md, this file) | 100 |
| **Grand Total** | **193** |
