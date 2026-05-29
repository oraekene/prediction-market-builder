# PM Strategy Builder — Manual Test Guide Vol. 3: Auto-Profit Protection & Risk Management System

> **Purpose:** 150+ test cases covering every new feature from the auto-profit protection system — advanced risk nodes, action nodes, position monitoring, withdrawal strategies, safe wallets, and the full frontend integration.
> **Prerequisites:** Backend running (`uvicorn app.main:app --reload --port 8000`), Frontend running (`npm run dev`), SQLite DB initialized with migration 003 applied (`alembic upgrade head`).
> **Disjoint from:** Vol. 1 (TEST_GUIDE.md) and Vol. 2 (TEST_GUIDE_2.md).

---

## SECTION 1: STRATEGY CANVAS SAVE/LOAD (TC-201 — TC-210)

### TC-201: Create new strategy from blank canvas
1. Login → navigate to `/strategies`
2. Click "Create Strategy"
3. **Verify:** Canvas opens with 3 default nodes (Polymarket Data → Odds < 45% → Place Bet)
4. Drag a "Trailing Stop" node from the Risk palette onto the canvas
5. **Verify:** Node appears with red border, "RISK" badge, label "Trailing Stop"
6. Click "Save Strategy"
7. **Verify:** Strategy saved (no error toast)
8. Click "← Back"
9. **Verify:** Strategy appears in the strategy list grid

### TC-202: Load existing strategy into canvas
1. Navigate to `/strategies`
2. Click on an existing strategy card
3. **Verify:** Canvas opens with that strategy's nodes and edges loaded
4. **Verify:** Strategy name shown in the header bar
5. **Verify:** Status badge shown (draft/active/paused)

### TC-203: Edit strategy and save changes
1. Open an existing strategy in the canvas
2. Drag a new node onto the canvas
3. Connect it to an existing node via edge
4. Click "Save Strategy"
5. Click "← Back"
6. Click the same strategy card again
7. **Verify:** The new node and edge are still there (persisted)

### TC-204: Node property panel write-back
1. Open a strategy in the canvas
2. Click on a Performance node (e.g., "Sharpe")
3. **Verify:** Right panel shows "Configure: Sharpe" header
4. Change the "Window" input from 50 to 100
5. **Verify:** Input value updates (controlled input)
6. Click on a non-performance node
7. **Verify:** Right panel shows "Label", "Parameter", "Description" fields
8. Change the label text
9. **Verify:** Node label on canvas updates in real-time

### TC-205: Node palette shows all 70+ node types
1. Open the strategy canvas
2. **Verify:** Left palette shows categories: Sources, Filters, Conditions, Actions, Risk - Position Exits, Risk - Portfolio Limits, Risk - Diversification, Risk - Greeks, Risk - Execution, Risk - Regime, Risk - Portfolio Construction, Auto-Withdrawal, Analysis, Performance
3. Count items in "Risk - Position Exits" — **Verify:** 10 items (Stop-Loss, Take Profit, Trailing Stop, Tightening Trailing Stop, ATR Stop, Volatility Stop, Break-Even Stop, Time Exit, Scaling Exit, Moving Average Exit)
4. Count items in "Risk - Portfolio Limits" — **Verify:** 17 items
5. Count items in "Risk - Greeks" — **Verify:** 6 items
6. Count items in "Auto-Withdrawal" — **Verify:** 2 items (Withdraw to Safe Wallet, Withdrawal Strategy)

### TC-206: Drag-and-drop maps to correct backend handler type
1. Open the canvas
2. Drag "Trailing Stop" from palette → **Verify:** Node shows red border (risk type)
3. Drag "Polymarket" from palette → **Verify:** Node shows green border (source type)
4. Drag "Threshold" from palette → **Verify:** Node shows yellow border (condition type)
5. Drag "Place Bet" from palette → **Verify:** Node shows orange border (action type)
6. Drag "Sharpe" from palette → **Verify:** Node shows blue border (performance type)

### TC-207: Delete strategy
1. Navigate to `/strategies`
2. Open a strategy in the canvas
3. Note the strategy name
4. Click "← Back"
5. **Verify:** Strategy still in list (not deleted by navigating away)

### TC-208: Strategy node count display
1. Open a strategy with 5 nodes and 4 edges
2. **Verify:** Header shows "5 nodes · 4 connections"

### TC-209: Empty canvas edge creation
1. Open a blank strategy
2. Drag 2 nodes onto the canvas
3. Drag from node 1's right handle to node 2's left handle
4. **Verify:** Edge line appears connecting the two nodes
5. **Verify:** Edge count in header updates

### TC-210: Strategy list shows correct metadata
1. Navigate to `/strategies`
2. **Verify:** Each strategy card shows: name, status badge (color-coded), description (clamped to 2 lines), mode, creation timestamp
3. **Verify:** Active strategies show green badge, paused show yellow, draft show gray

---

## SECTION 2: ADVANCED RISK NODES — POSITION EXITS (TC-211 — TC-230)

### TC-211: Trailing Stop node configuration
1. Open a strategy, drag "Trailing Stop" onto canvas
2. Click the node → **Verify:** Right panel shows backend type "trailing_stop"
3. **Verify:** Default config: trail_pct = 0.05 (5%)

### TC-212: Trailing Stop triggers correctly
1. Create a strategy with: Polymarket Source → Threshold (odds > 0.60) → Trailing Stop (trail_pct: 0.05) → Close Position
2. Deploy strategy
3. Simulate a position that rises from 0.50 to 0.55 (10% gain)
4. Simulate price dropping to 0.52 (5.5% drop from peak)
5. **Verify:** Trailing stop triggers (drop > 5% from HWM)
6. **Verify:** Close Position action fires

### TC-213: Tightening Trailing Stop
1. Drag "Tightening Trailing Stop" onto canvas
2. **Verify:** Default thresholds: [[0.05, 0.03], [0.10, 0.02], [0.20, 0.01]]
3. This means: at +5% profit, trail 3%; at +10%, trail 2%; at +20%, trail 1%

### TC-214: ATR Stop node
1. Drag "ATR Stop" onto canvas
2. **Verify:** Default config: atr_multiplier = 2.0, atr_period = 14
3. **Verify:** Stop distance = 2x current ATR

### TC-215: Volatility Stop
1. Drag "Volatility Stop" onto canvas
2. **Verify:** Default: vol_threshold = 0.03
3. **Verify:** Triggers when portfolio volatility exceeds 3%

### TC-216: Break-Even Stop
1. Drag "Break-Even Stop" onto canvas
2. **Verify:** Default: trigger_pct = 0.02, buffer_pct = 0.005
3. **Verify:** Triggers when price is profitable but has dropped to within 0.5% of entry

### TC-217: Time Exit
1. Drag "Time Exit" onto canvas
2. **Verify:** Default: max_hold_days = 30
3. **Verify:** Triggers when position held longer than 30 days

### TC-218: Scaling Exit
1. Drag "Scaling Exit" onto canvas
2. **Verify:** Default tiers: [{profit_pct: 10%, exit_pct: 33}, {profit_pct: 25%, exit_pct: 50}]
3. **Verify:** At +10% profit, exit 33% of position; at +25%, exit 50%

### TC-219: Moving Average Exit
1. Drag "Moving Average Exit" onto canvas
2. **Verify:** Default: period = 20, ma_type = "sma"
3. **Verify:** Triggers on bearish crossover (price crosses below MA)

### TC-220: Stop-Loss and Take Profit (existing, now exposed)
1. Drag "Stop-Loss" from palette
2. **Verify:** Node appears with red border, "RISK" badge
3. **Verify:** Backend type is "stop_loss"
4. Drag "Take Profit" from palette
5. **Verify:** Backend type is "take_profit"

---

## SECTION 3: ADVANCED RISK NODES — PORTFOLIO LIMITS (TC-231 — TC-255)

### TC-231: Drawdown Monitor
1. Drag "Drawdown" onto canvas
2. **Verify:** Default: max_drawdown = 0.15 (15%)
3. **Verify:** Backend type: "drawdown_monitor"

### TC-232: VaR Check
1. Drag "VaR Check" onto canvas
2. **Verify:** Default: confidence = 0.95, limit = 0.05

### TC-233: Expected Shortfall
1. Drag "Expected Shortfall" onto canvas
2. **Verify:** Default: confidence = 0.95, limit = 0.08

### TC-234: Daily Loss Limit
1. Drag "Daily Loss Limit" onto canvas
2. **Verify:** Default: max_daily_loss = 0.03 (3%)
3. **Verify:** Backend type: "daily_loss_limit"

### TC-235: Weekly Loss Limit
1. Drag "Weekly Loss Limit" onto canvas
2. **Verify:** Default: max_weekly_loss = 0.05 (5%)

### TC-236: Monthly Loss Limit
1. Drag "Monthly Loss Limit" onto canvas
2. **Verify:** Default: max_monthly_loss = 0.10 (10%)

### TC-237: Max Position Count
1. Drag "Max Position Count" onto canvas
2. **Verify:** Default: max_count = 10

### TC-238: Max Gross Exposure
1. Drag "Max Gross Exposure" onto canvas
2. **Verify:** Default: max_exposure = 1.0 (100%)

### TC-239: Max Net Exposure
1. Drag "Max Net Exposure" onto canvas
2. **Verify:** Default: max_net_exposure = 0.5 (50%)

### TC-240: Leverage Limit
1. Drag "Leverage Limit" onto canvas
2. **Verify:** Default: max_leverage = 2.0

### TC-241: Sector Exposure Limit
1. Drag "Sector Exposure Limit" onto canvas
2. **Verify:** Default: sector_limits = {} (empty)

### TC-242: Beta Exposure Limit
1. Drag "Beta Exposure Limit" onto canvas
2. **Verify:** Default: max_beta = 1.0

### TC-243: Volatility Targeting
1. Drag "Volatility Targeting" onto canvas
2. **Verify:** Default: target_vol = 0.10 (10%)
3. **Verify:** Returns scaling_factor to adjust position sizes

### TC-244: Stress Test
1. Drag "Stress Test" onto canvas
2. **Verify:** Default: scenarios = [] (empty)
3. **Verify:** User must configure scenarios with shocks per market

### TC-245: Monte Carlo Risk
1. Drag "Monte Carlo Risk" onto canvas
2. **Verify:** Default: num_simulations = 1000, confidence = 0.95

### TC-246: Tail Risk Check
1. Drag "Tail Risk Check" onto canvas
2. **Verify:** Default: max_kurtosis = 5.0, max_skewness = -0.5

### TC-247: Liquidity Risk
1. Drag "Liquidity Risk" onto canvas
2. **Verify:** Default: min_liquidity = 10000, max_spread_pct = 0.05

---

## SECTION 4: ADVANCED RISK NODES — DIVERSIFICATION (TC-256 — TC-265)

### TC-256: Correlation Check
1. Drag "Correlation Check" onto canvas
2. **Verify:** Default: max_correlation = 0.7

### TC-257: Concentration Check
1. Drag "Concentration Check" onto canvas
2. **Verify:** Default: max_concentration = 0.3

### TC-258: Factor Exposure
1. Drag "Factor Exposure" onto canvas
2. **Verify:** Default: max_factor_exposures = {}

### TC-259: MCR Check
1. Drag "MCR Check" onto canvas
2. **Verify:** Default: max_mcr = 0.1

### TC-260: Worst Case Portfolio
1. Drag "Worst Case Portfolio" onto canvas
2. **Verify:** Default: max_worst_case_loss = 0.20

---

## SECTION 5: ADVANCED RISK NODES — GREEKS (TC-266 — TC-277)

### TC-266: Delta Exposure
1. Drag "Delta Exposure" onto canvas
2. **Verify:** Default: max_delta = 1.0

### TC-267: Gamma Exposure
1. Drag "Gamma Exposure" onto canvas
2. **Verify:** Default: max_gamma = 0.5

### TC-268: Vega Exposure
1. Drag "Vega Exposure" onto canvas
2. **Verify:** Default: max_vega = 0.5

### TC-269: Theta Decay
1. Drag "Theta Decay" onto canvas
2. **Verify:** Default: max_theta_loss = 100

### TC-270: Vanna Exposure
1. Drag "Vanna Exposure" onto canvas
2. **Verify:** Default: max_vanna = 0.3

### TC-271: Volga Exposure
1. Drag "Volga Exposure" onto canvas
2. **Verify:** Default: max_volga = 0.3

---

## SECTION 6: ADVANCED RISK NODES — EXECUTION (TC-278 — TC-290)

### TC-278: Circuit Breaker
1. Drag "Circuit Breaker" onto canvas
2. **Verify:** Default: max_daily_loss = 0.05, max_consecutive_losses = 5, cooldown_seconds = 300

### TC-279: Slippage Guard
1. Drag "Slippage Guard" onto canvas
2. **Verify:** Default: max_slippage_pct = 0.02

### TC-280: Max Consecutive Losses
1. Drag "Max Consecutive Losses" onto canvas
2. **Verify:** Default: max_streak = 5

### TC-281: Cooldown Period
1. Drag "Cooldown Period" onto canvas
2. **Verify:** Default: cooldown_trades = 3

### TC-282: Position Timeout
1. Drag "Position Timeout" onto canvas
2. **Verify:** Default: max_hold_seconds = 86400 (1 day)

---

## SECTION 7: ADVANCED RISK NODES — REGIME (TC-291 — TC-300)

### TC-291: Volatility Regime
1. Drag "Volatility Regime" onto canvas
2. **Verify:** Default: target_regime = "normal"

### TC-292: Correlation Regime Shift
1. Drag "Correlation Regime Shift" onto canvas
2. **Verify:** Default: correlation_spike_threshold = 0.3

### TC-293: Toxicity Detection
1. Drag "Toxicity Detection" onto canvas
2. **Verify:** Default: vpin_threshold = 0.7

### TC-294: Order Flow Imbalance
1. Drag "Order Flow Imbalance" onto canvas
2. **Verify:** Default: imbalance_threshold = 0.3

---

## SECTION 8: ADVANCED RISK NODES — PORTFOLIO CONSTRUCTION (TC-301 — TC-310)

### TC-301: Kelly Criterion
1. Drag "Kelly Criterion" onto canvas
2. **Verify:** Default: method = "kelly"

### TC-302: Risk Parity
1. Drag "Risk Parity" onto canvas
2. **Verify:** Backend type: "risk_parity_allocation"
3. **Verify:** Returns suggested_weights dict

### TC-303: Mean-Variance Optimization
1. Drag "Mean-Variance Optimization" onto canvas
2. **Verify:** Default: risk_aversion = 1.0

### TC-304: Black-Litterman
1. Drag "Black-Litterman" onto canvas
2. **Verify:** Default: views = {}, tau = 0.05

### TC-305: Hierarchical Risk Parity
1. Drag "Hierarchical Risk Parity" onto canvas
2. **Verify:** Backend type: "hierarchical_risk_parity"

---

## SECTION 9: ACTION NODES (TC-311 — TC-325)

### TC-311: Close Position node
1. Drag "Close Position" from Actions palette
2. **Verify:** Node appears with orange border, "ACTION" badge
3. **Verify:** Backend type: "close_position"
4. **Verify:** Default: close_pct = 100

### TC-312: Close Position with partial percentage
1. Configure Close Position node with close_pct = 50
2. Connect upstream trigger (e.g., Take Profit) to Close Position
3. When triggered, **Verify:** Only 50% of position is closed

### TC-313: Convert to Stablecoin node
1. Drag "Convert to Stablecoin" from Actions palette
2. **Verify:** Backend type: "convert_to_stablecoin"
3. **Verify:** Default: target_stablecoin = "USDC", convert_pct = 100

### TC-314: Withdraw to Safe Wallet node
1. Drag "Withdraw to Safe Wallet" from Auto-Withdrawal palette
2. **Verify:** Backend type: "withdraw_to_safe_wallet"
3. **Verify:** Default: withdraw_pct = 50, source = "profits", target_currency = "USDC"

### TC-315: Withdrawal Strategy node
1. Drag "Withdrawal Strategy" from Auto-Withdrawal palette
2. **Verify:** Backend type: "withdrawal_strategy"
3. **Verify:** Default: steps = [] (empty, user configures via WithdrawalPage)

### TC-316: Auto-execute on take profit
1. Create chain: Take Profit → Close Position (auto_execute: true)
2. When take profit triggers, **Verify:** Close Position auto-executes without manual intervention

### TC-317: Auto-execute disabled
1. Create chain: Take Profit → Close Position (auto_execute: false)
2. When take profit triggers, **Verify:** Alert fires but no auto-close

---

## SECTION 10: POSITION MONITOR (TC-326 — TC-340)

### TC-328: Position monitor starts on app launch
1. Start the backend server
2. **Verify:** Log shows "Position monitor started" or similar
3. **Verify:** No errors in startup logs related to position_monitor

### TC-329: Register position for monitoring
1. Place a paper trade with risk_profile containing auto_monitor: true
2. **Verify:** Position appears in monitored_positions
3. **Verify:** Position status is "active"

### TC-330: Position monitor evaluates risk nodes
1. Register a position with a Trailing Stop node (trail_pct: 0.05)
2. Wait for monitor tick (every 5 seconds)
3. Simulate price drop > 5% from HWM
4. **Verify:** Monitor detects trigger
5. **Verify:** Close order is placed (or alert fired)

### TC-331: Position monitor updates trail states
1. Register a position
2. Simulate price rising to new HWM
3. **Verify:** trail_states[position_id]["high_water_mark"] updated

### TC-332: Position monitor stops cleanly
1. Stop the backend server
2. **Verify:** No errors in shutdown logs
3. **Verify:** Monitor loop exits gracefully

### TC-333: Unregister position
1. Register a position
2. Unregister it
3. **Verify:** Position no longer in monitored_positions
4. **Verify:** No further evaluations for that position

---

## SECTION 11: WITHDRAWAL STRATEGY BUILDER (TC-341 — TC-370)

### TC-341: Navigate to Withdrawal page
1. Login → click "Withdrawal" in header nav
2. **Verify:** WithdrawalPage loads with "Withdrawal Strategy Builder" title
3. **Verify:** Left sidebar shows strategy list (initially empty)

### TC-342: Create new withdrawal strategy
1. Click "New Strategy" or "Create" button
2. Enter name: "Profit Locker Tier 1"
3. Enter description: "Withdraw 50% of first $500 profit"
4. **Verify:** Strategy appears in sidebar list

### TC-343: Add a withdrawal step
1. Select a withdrawal strategy
2. Click "+ Add Step"
3. **Verify:** Step editor appears with condition and action dropdowns

### TC-344: Configure profit_threshold condition
1. In step editor, select condition type: "Profit Threshold"
2. Set amount: 500
3. **Verify:** Condition type and amount fields visible

### TC-345: Configure withdraw_pct action
1. Select action type: "Withdraw Percentage"
2. Set percentage: 50
3. Set currency: USDC
4. **Verify:** Action fields update based on type selection

### TC-346: Configure withdraw_fixed action
1. Select action type: "Withdraw Fixed Amount"
2. Set amount: 200
3. Set currency: USDT

### TC-347: Configure convert_to_stablecoin action
1. Select action type: "Convert to Stablecoin"
2. Set stablecoin: USDC
3. Set amount: 100

### TC-348: Set step as one-shot
1. Toggle "Once" on a step
2. **Verify:** Step will only execute once, then skip on future evaluations

### TC-349: Set cooldown on a step
1. Set cooldown_seconds: 3600 (1 hour)
2. **Verify:** Step won't re-trigger within 1 hour of last execution

### TC-350: Set sequential constraint
1. Create 3 steps
2. Toggle "Sequential" on step 2 and step 3
3. **Verify:** Step 2 only evaluates after step 1 executes
4. **Verify:** Step 3 only evaluates after step 2 executes

### TC-351: Multi-step withdrawal ladder
1. Create step 1: profit > $500 → withdraw 50% of profits
2. Create step 2: profit > $1100 → withdraw 20% of profits
3. Create step 3: trailing stop fall 10% → withdraw 20% of profits
4. Create step 4: profit rises 40% → withdraw fixed $12
5. **Verify:** All 4 steps appear in the strategy
6. Click "Save Strategy"
7. **Verify:** Strategy saved with all steps

### TC-352: Edit existing step
1. Select a strategy with existing steps
2. Click "Edit" on step 1
3. Change the condition amount
4. **Verify:** Changes reflected in the step display

### TC-353: Delete a step
1. Select a strategy with steps
2. Click "Delete" on a step
3. **Verify:** Step removed from the list

### TC-354: Reorder steps
1. Create 3 steps
2. Use move up/down buttons
3. **Verify:** Steps reorder correctly

### TC-355: Save withdrawal strategy
1. Create a strategy with 3 steps
2. Click "Save Strategy"
3. **Verify:** Strategy persisted (refresh page, strategy still there)

### TC-356: Delete withdrawal strategy
1. Select a strategy
2. Click "Delete Strategy"
3. **Verify:** Strategy removed from sidebar list

### TC-357: Toggle strategy active/inactive
1. Select a strategy
2. Toggle "Active" switch off
3. **Verify:** Strategy marked as inactive
4. Toggle back on
5. **Verify:** Strategy marked as active

### TC-358: Evaluate withdrawal strategy manually
1. Select a strategy with steps
2. Click "Test Strategy" or "Evaluate"
3. **Verify:** Evaluation results shown (which steps triggered, which actions would fire)

### TC-359: Condition type — profit_pct
1. Create step with condition: profit_pct, pct: 20
2. **Verify:** Triggers when portfolio is up 20% from initial capital

### TC-360: Condition type — trailing_stop_fall
1. Create step with condition: trailing_stop_fall, pct: 10
2. **Verify:** Triggers when portfolio drops 10% from peak

### TC-361: Condition type — drawdown_from_peak
1. Create step with condition: drawdown_from_peak, pct: 15
2. **Verify:** Triggers when drawdown from peak exceeds 15%

### TC-362: Condition type — profit_rise
1. Create step with condition: profit_rise, pct: 40
2. **Verify:** Triggers when portfolio rises 40% since last checkpoint

### TC-363: Condition type — volatility_spike
1. Create step with condition: volatility_spike, threshold: 0.05
2. **Verify:** Triggers when portfolio volatility exceeds 5%

---

## SECTION 12: SAFE WALLETS (TC-371 — TC-390)

### TC-371: Safe wallet dashboard loads
1. Navigate to Withdrawal page
2. **Verify:** Safe wallet section shows wallet cards or "No wallets yet"

### TC-372: Create safe wallet
1. Click "Create Wallet" or "Add Safe Wallet"
2. Enter name: "Main Safe"
3. Select currency: USDC
4. Click "Create"
5. **Verify:** Wallet card appears with name, currency, balance = $0.00

### TC-373: Create multiple safe wallets
1. Create wallet "Profit Locker" with USDC
2. Create wallet "Stable Reserve" with USDT
3. **Verify:** Both wallets appear in the dashboard
4. **Verify:** Total protected capital shows sum of both

### TC-374: Transfer to safe wallet
1. Select a safe wallet
2. Click "Transfer to Safe"
3. Enter amount: 500
4. Select source: "Profits"
5. Click "Transfer"
6. **Verify:** Wallet balance increases by $500
7. **Verify:** Transfer appears in withdrawal history

### TC-375: Transfer from different sources
1. Transfer $200 from "Profits"
2. Transfer $300 from "Capital"
3. **Verify:** Both recorded with correct source labels

### TC-376: Safe wallet balance calculation
1. Create 2 wallets: USDC ($300) and USDT ($200)
2. **Verify:** Total protected capital shows $500
3. **Verify:** Individual balances correct

### TC-377: Withdrawal history
1. Make 3 transfers to safe wallets
2. **Verify:** History table shows all 3 with: date, amount, currency, source, status
3. **Verify:** Most recent transfer at top

### TC-378: Safe wallet is disconnected from strategies
1. Create a safe wallet with $1000
2. Open a strategy in the canvas
3. Check position sizing nodes
4. **Verify:** Safe wallet balance is NOT included in available capital for position sizing

### TC-379: Auto-withdrawal to safe wallet
1. Create a withdrawal strategy with: profit > $500 → withdraw 50% to safe wallet
2. Simulate portfolio reaching $500+ profit
3. **Verify:** Funds automatically transferred to safe wallet
4. **Verify:** Active trading capital reduced accordingly

### TC-380: Safe wallet prevents strategy reuse
1. Transfer $500 to safe wallet
2. Create a new strategy
3. **Verify:** Strategy cannot use the $500 in safe wallet for position sizing
4. **Verify:** Only active trading balance available

---

## SECTION 13: API ENDPOINTS (TC-391 — TC-415)

### TC-391: GET /api/withdrawal/wallets
1. `GET /api/withdrawal/wallets` with valid token
2. **Verify:** Returns 200 with list of safe wallets
3. **Verify:** Each wallet has: id, name, currency, balance, is_disconnected

### TC-392: POST /api/withdrawal/wallets
1. `POST /api/withdrawal/wallets` with `{"name": "Test Wallet", "currency": "USDC"}`
2. **Verify:** Returns 201 with created wallet
3. **Verify:** Wallet has is_disconnected = true

### TC-393: GET /api/withdrawal/wallets/{id}
1. Create a wallet, note its ID
2. `GET /api/withdrawal/wallets/{id}`
3. **Verify:** Returns 200 with wallet details

### TC-394: GET /api/withdrawal/balance
1. Create 2 wallets with balances
2. `GET /api/withdrawal/balance`
3. **Verify:** Returns total_usd_equivalent, balances_by_currency, wallet count

### TC-395: POST /api/withdrawal/transfer
1. `POST /api/withdrawal/transfer` with `{"amount": 100, "currency": "USDC", "source": "profits"}`
2. **Verify:** Returns 200 with transfer confirmation
3. **Verify:** Wallet balance increased
4. **Verify:** WithdrawalRecord created

### TC-396: GET /api/withdrawal/history
1. Make 3 transfers
2. `GET /api/withdrawal/history`
3. **Verify:** Returns all 3 records with correct fields

### TC-397: POST /api/withdrawal/strategies
1. `POST /api/withdrawal/strategies` with `{"name": "Test Strategy", "steps": [...]}`
2. **Verify:** Returns 201 with created strategy

### TC-398: GET /api/withdrawal/strategies
1. Create 2 strategies
2. `GET /api/withdrawal/strategies`
3. **Verify:** Returns both strategies

### TC-399: PUT /api/withdrawal/strategies/{id}
1. Create a strategy
2. `PUT /api/withdrawal/strategies/{id}` with `{"name": "Updated Name"}`
3. **Verify:** Returns 200 with updated strategy
4. **Verify:** Name changed

### TC-400: DELETE /api/withdrawal/strategies/{id}
1. Create a strategy
2. `DELETE /api/withdrawal/strategies/{id}`
3. **Verify:** Returns 200
4. **Verify:** Strategy no longer in list

### TC-401: POST /api/withdrawal/strategies/{id}/evaluate
1. Create a strategy with profit_threshold step
2. `POST /api/withdrawal/strategies/{id}/evaluate`
3. **Verify:** Returns evaluation result (triggered/not triggered, actions)

### TC-402: POST /api/withdrawal/strategies/{id}/toggle
1. Create an active strategy
2. `POST /api/withdrawal/strategies/{id}/toggle`
3. **Verify:** Strategy toggled to inactive
4. Toggle again
5. **Verify:** Strategy toggled back to active

### TC-403: Unauthorized access to withdrawal endpoints
1. Call any `/api/withdrawal/*` endpoint without Authorization header
2. **Verify:** Returns 401

### TC-404: Cross-user wallet access
1. Create wallet as User A
2. `GET /api/withdrawal/wallets` as User B
3. **Verify:** User B cannot see User A's wallets

---

## SECTION 14: STRATEGY ENGINE INTEGRATION (TC-416 — TC-430)

### TC-416: Strategy engine evaluates trailing_stop node
1. `POST /api/strategies/evaluate` with nodes containing trailing_stop
2. **Verify:** Returns triggered/not_triggered based on market data

### TC-417: Strategy engine evaluates circuit_breaker node
1. Build strategy graph with circuit_breaker node
2. Feed portfolio with daily_pnl exceeding limit
3. **Verify:** Circuit breaker triggers

### TC-418: Strategy engine evaluates risk_parity_allocation
1. Build strategy with risk_parity_allocation node
2. Feed portfolio with multiple positions
3. **Verify:** Returns suggested_weights dict

### TC-419: Strategy engine evaluates mean_variance_optimization
1. Build strategy with mean_variance_optimization node
2. Feed portfolio with position_returns
3. **Verify:** Returns suggested_weights

### TC-420: Strategy engine evaluates close_position action
1. Build strategy: threshold → close_position
2. When threshold triggers
3. **Verify:** close_position action returns orders_placed

### TC-421: Strategy engine evaluates withdraw_to_safe_wallet
1. Build strategy: profit_threshold → withdraw_to_safe_wallet
2. When profit exceeds threshold
3. **Verify:** Returns withdraw action with amount

### TC-422: Strategy engine DAG execution order
1. Build strategy: A → B → C (linear chain)
2. Evaluate
3. **Verify:** Nodes execute in order A, B, C

### TC-423: Strategy engine parallel branches
1. Build strategy: A → B, A → C (fork)
2. Evaluate
3. **Verify:** Both B and C receive A's output

### TC-424: Strategy engine cycle detection
1. Build strategy with cycle: A → B → A
2. Evaluate
3. **Verify:** Returns error for cyclic node

### TC-425: Strategy engine unknown node type
1. Build strategy with node type "nonexistent_handler"
2. Evaluate
3. **Verify:** Returns empty dict (graceful degradation)

### TC-426: Strategy engine with new ExecutionContext fields
1. Evaluate strategy with trail_states, circuit_breaker_state, greeks, vpin, ofi
2. **Verify:** All fields accessible in handlers

---

## SECTION 15: DATABASE MIGRATION (TC-431 — TC-440)

### TC-431: Migration 003 applies cleanly
1. Run `alembic upgrade head`
2. **Verify:** No errors
3. **Verify:** Tables created: monitored_positions, safe_wallets, withdrawal_strategies, withdrawal_records

### TC-432: Monitored positions table structure
1. Query `PRAGMA table_info(monitored_positions)`
2. **Verify:** Columns: id, user_id, strategy_id, platform, market_id, side, entry_price, size, high_water_mark, entry_time, status, risk_config, trail_states, exit_price, exit_time, pnl, withdrawal_strategy_id, created_at, updated_at

### TC-433: Safe wallets table structure
1. Query `PRAGMA table_info(safe_wallets)`
2. **Verify:** Columns: id, user_id, name, currency, balance, address, is_disconnected, created_at, updated_at

### TC-434: Withdrawal strategies table structure
1. Query `PRAGMA table_info(withdrawal_strategies)`
2. **Verify:** Columns: id, user_id, name, description, is_active, steps, current_step_index, step_states, safe_wallet_id, created_at, updated_at

### TC-435: Withdrawal records table structure
1. Query `PRAGMA table_info(withdrawal_records)`
2. **Verify:** Columns: id, user_id, safe_wallet_id, strategy_id, amount, currency, source, trigger_type, trigger_step_id, status, created_at

### TC-436: Migration is idempotent
1. Run `alembic upgrade head` twice
2. **Verify:** Second run is a no-op (no errors)

### TC-437: Migration downgrade works
1. Run `alembic downgrade -1`
2. **Verify:** Tables dropped
3. Run `alembic upgrade head`
4. **Verify:** Tables recreated

---

## SECTION 16: ERROR HANDLING & EDGE CASES (TC-441 — TC-460)

### TC-441: Withdraw with zero amount
1. `POST /api/withdrawal/transfer` with `{"amount": 0, "currency": "USDC"}`
2. **Verify:** Returns error "Amount must be positive"

### TC-442: Withdraw negative amount
1. `POST /api/withdrawal/transfer` with `{"amount": -100, "currency": "USDC"}`
2. **Verify:** Returns error

### TC-443: Create wallet with empty name
1. `POST /api/withdrawal/wallets` with `{"name": "", "currency": "USDC"}`
2. **Verify:** Either accepted (no validation) or returns 422

### TC-444: Withdrawal strategy with 0 steps
1. Create strategy with steps: []
2. Evaluate
3. **Verify:** Returns empty actions list

### TC-445: Withdrawal strategy with 60 steps
1. Create strategy with 60 steps
2. **Verify:** All steps saved and loaded correctly
3. Evaluate
4. **Verify:** All 60 steps evaluated

### TC-446: Position monitor with no positions
1. Start monitor with no registered positions
2. **Verify:** Monitor runs without errors

### TC-447: Circuit breaker cooldown
1. Trigger circuit breaker (daily loss exceeded)
2. Wait for cooldown period
3. **Verify:** After cooldown, circuit breaker resets to "closed"

### TC-448: Trailing stop with no positions
1. Evaluate trailing_stop node with empty positions list
2. **Verify:** Returns triggered: false

### TC-449: Monte Carlo with insufficient data
1. Evaluate monte_carlo_risk with < 2 returns
2. **Verify:** Returns zeros (var_mc: 0, worst_case: 0)

### TC-450: Strategy engine with empty graph
1. Evaluate strategy with nodes: [], edges: []
2. **Verify:** Returns default {approved: true, suggested_size: 0.0}

---

## SECTION 17: PERFORMANCE & STRESS (TC-461 — TC-470)

### TC-461: Strategy evaluation latency
1. Build strategy with 20 nodes
2. Evaluate 100 times
3. **Verify:** Average latency < 100ms

### TC-462: Position monitor under load
1. Register 50 positions simultaneously
2. **Verify:** Monitor processes all within one tick cycle (5s)
3. **Verify:** No memory leaks (check process memory)

### TC-463: Withdrawal strategy with 60 steps evaluation
1. Create 60-step withdrawal strategy
2. Evaluate
3. **Verify:** Completes within 1 second

### TC-464: Concurrent API requests
1. Send 10 simultaneous withdrawal API calls
2. **Verify:** No race conditions or deadlocks
3. **Verify:** All return correct responses

### TC-455: Large portfolio stress test
1. Create portfolio with 100 positions
2. Evaluate risk nodes
3. **Verify:** All handlers complete without timeout

---

## SECTION 18: FRONTEND INTEGRATION (TC-471 — TC-500)

### TC-471: Withdrawal page navigation
1. Login → click "Withdrawal" in header
2. **Verify:** Page loads, URL is /withdrawal

### TC-472: Safe wallet creation flow
1. Navigate to /withdrawal
2. Click "Create Wallet"
3. Fill name, currency
4. Click save
5. **Verify:** Wallet appears in dashboard
6. **Verify:** Balance shows $0.00

### TC-473: Transfer flow
1. Select a wallet
2. Click "Transfer"
3. Enter amount, select source
4. Submit
5. **Verify:** Balance updates
6. **Verify:** History entry created

### TC-474: Withdrawal strategy creation flow
1. Navigate to /withdrawal
2. Create new strategy
3. Add step 1 with condition + action
4. Add step 2 with condition + action
5. Save
6. **Verify:** Strategy appears in sidebar
7. Reload page
8. **Verify:** Strategy persists with both steps

### TC-475: Strategy list shows strategies
1. Create 3 withdrawal strategies
2. **Verify:** All 3 appear in sidebar list

### TC-476: Edit strategy steps
1. Select strategy with steps
2. Edit step 1 condition
3. Save
4. **Verify:** Changes persisted

### TC-477: Delete strategy
1. Select strategy
2. Click delete
3. **Verify:** Strategy removed from list

### TC-478: Risk node visual differentiation
1. Open strategy canvas
2. Drag Risk nodes → **Verify:** Red border
3. Drag Action nodes → **Verify:** Orange border
4. Drag Source nodes → **Verify:** Green border
5. Drag Condition nodes → **Verify:** Yellow border
6. Drag Performance nodes → **Verify:** Blue border

### TC-479: Node handles connectivity
1. Drag 2 risk nodes onto canvas
2. Drag from right handle of node 1 to left handle of node 2
3. **Verify:** Edge created
4. Drag from node 2's right handle to empty space
5. **Verify:** No edge created (no target)

### TC-480: Node selection highlights
1. Click on a node
2. **Verify:** Node gets selection border
3. **Verify:** Right panel shows node configuration
4. Click on empty canvas
5. **Verify:** Selection cleared, right panel shows "Select a node to configure"

---

## SECTION 19: END-TO-END WORKFLOWS (TC-501 — TC-520)

### TC-501: Full auto-profit protection workflow
1. Create strategy: Polymarket Source → TabPFN Signal → Threshold (probability > 0.7) → Place Bet
2. Add risk chain: Trailing Stop (5%) → Close Position
3. Deploy strategy
4. Place paper trade through the strategy
5. Simulate price rising then falling > 5% from peak
6. **Verify:** Trailing stop triggers
7. **Verify:** Close position fires
8. **Verify:** Trade appears in history with PnL

### TC-502: Full withdrawal workflow
1. Create safe wallet "Profit Locker" (USDC)
2. Create withdrawal strategy: profit > $500 → withdraw 50% to Profit Locker
3. Place profitable trades until profit > $500
4. **Verify:** Auto-withdrawal triggers
5. **Verify:** Profit Locker balance increased
6. **Verify:** Active trading capital decreased

### TC-503: Multi-step withdrawal ladder
1. Create 5-step withdrawal strategy with increasing thresholds
2. Simulate portfolio growing through each threshold
3. **Verify:** Each step fires at the correct threshold
4. **Verify:** Cumulative withdrawals match expected amounts

### TC-504: Circuit breaker → recovery workflow
1. Create strategy with circuit breaker (max_daily_loss: 3%)
2. Simulate daily loss exceeding 3%
3. **Verify:** Circuit breaker opens, new trades blocked
4. Wait for cooldown period
5. **Verify:** Circuit breaker resets
6. **Verify:** New trades can be placed

### TC-505: Risk parity allocation workflow
1. Create strategy with Risk Parity node
2. Feed portfolio with 3 positions of different volatilities
3. **Verify:** Suggested weights are inversely proportional to volatility
4. Apply weights
5. **Verify:** Portfolio risk is balanced across positions

---

## APPENDIX A: NODE TYPE REFERENCE

| Category | Node Name | Backend Type | Default Config |
|----------|-----------|-------------|----------------|
| Sources | Polymarket | polymarket_source | {} |
| Sources | Kalshi | kalshi_source | {} |
| Sources | Drift | drift_source | {} |
| Sources | Web Search | web_search | {} |
| Sources | News | news_source | {} |
| Filters | TabPFN Signal | tabpfn_signal | {} |
| Filters | Toto-2 Climate | toto2_climate | {} |
| Filters | Sentiment | sentiment_filter | {} |
| Filters | SHAP Feature Importance | shap_feature_importance | {min_importance: 0, top_k: 5} |
| Conditions | Threshold | threshold_condition | {field: "current_odds", operator: "lt", threshold: 0.5} |
| Conditions | Time-Based | time_condition | {operator: "after"} |
| Conditions | AND/OR | and_or_gate | {gate_type: "and"} |
| Conditions | Branch | branch | {branch_if: true} |
| Actions | Place Bet | place_bet | {} |
| Actions | Send Alert | alert_action | {message: "...", severity: "warning"} |
| Actions | Forward | forward | {} |
| Actions | Webhook | webhook | {} |
| Actions | Close Position | close_position | {close_pct: 100} |
| Actions | Convert to Stablecoin | convert_to_stablecoin | {target_stablecoin: "USDC", convert_pct: 100} |
| Risk-Exits | Stop-Loss | stop_loss | {stop_loss: 0.1} |
| Risk-Exits | Take Profit | take_profit | {take_profit: 0.2} |
| Risk-Exits | Trailing Stop | trailing_stop | {trail_pct: 0.05} |
| Risk-Exits | Tightening Trailing Stop | tightening_trailing_stop | {thresholds: [[0.05, 0.03], [0.10, 0.02], [0.20, 0.01]]} |
| Risk-Exits | ATR Stop | atr_stop | {atr_multiplier: 2.0, atr_period: 14} |
| Risk-Exits | Volatility Stop | volatility_stop | {vol_threshold: 0.03} |
| Risk-Exits | Break-Even Stop | break_even_stop | {trigger_pct: 0.02, buffer_pct: 0.005} |
| Risk-Exits | Time Exit | time_exit | {max_hold_days: 30} |
| Risk-Exits | Scaling Exit | scaling_exit | {tiers: [{profit_pct: 0.10, exit_pct: 33}, {profit_pct: 0.25, exit_pct: 50}]} |
| Risk-Exits | Moving Average Exit | moving_average_exit | {period: 20, ma_type: "sma"} |
| Risk-Limits | Drawdown | drawdown_monitor | {max_drawdown: 0.15} |
| Risk-Limits | VaR Check | var_check | {confidence: 0.95, limit: 0.05} |
| Risk-Limits | Expected Shortfall | expected_shortfall_check | {confidence: 0.95, limit: 0.08} |
| Risk-Limits | Daily Loss Limit | daily_loss_limit | {max_daily_loss: 0.03} |
| Risk-Limits | Weekly Loss Limit | weekly_loss_limit | {max_weekly_loss: 0.05} |
| Risk-Limits | Monthly Loss Limit | monthly_loss_limit | {max_monthly_loss: 0.10} |
| Risk-Limits | Max Position Count | max_position_count | {max_count: 10} |
| Risk-Limits | Max Gross Exposure | max_gross_exposure | {max_exposure: 1.0} |
| Risk-Limits | Max Net Exposure | max_net_exposure | {max_net_exposure: 0.5} |
| Risk-Limits | Leverage Limit | leverage_limit | {max_leverage: 2.0} |
| Risk-Limits | Sector Exposure Limit | sector_exposure_limit | {sector_limits: {}} |
| Risk-Limits | Beta Exposure Limit | beta_exposure_limit | {max_beta: 1.0} |
| Risk-Limits | Volatility Targeting | volatility_targeting | {target_vol: 0.10} |
| Risk-Limits | Stress Test | stress_test | {scenarios: []} |
| Risk-Limits | Monte Carlo Risk | monte_carlo_risk | {num_simulations: 1000, confidence: 0.95} |
| Risk-Limits | Tail Risk Check | tail_risk_check | {max_kurtosis: 5.0, max_skewness: -0.5} |
| Risk-Limits | Liquidity Risk | liquidity_risk_check | {min_liquidity: 10000, max_spread_pct: 0.05} |
| Risk-Div | Correlation Check | correlation_check | {max_correlation: 0.7} |
| Risk-Div | Concentration Check | concentration_check | {max_concentration: 0.3} |
| Risk-Div | Factor Exposure | factor_exposure_check | {max_factor_exposures: {}} |
| Risk-Div | MCR Check | mcr_check | {max_mcr: 0.1} |
| Risk-Div | Worst Case Portfolio | worst_case_portfolio | {max_worst_case_loss: 0.20} |
| Risk-Greeks | Delta Exposure | delta_exposure | {max_delta: 1.0} |
| Risk-Greeks | Gamma Exposure | gamma_exposure | {max_gamma: 0.5} |
| Risk-Greeks | Vega Exposure | vega_exposure | {max_vega: 0.5} |
| Risk-Greeks | Theta Decay | theta_decay | {max_theta_loss: 100} |
| Risk-Greeks | Vanna Exposure | vanna_exposure | {max_vanna: 0.3} |
| Risk-Greeks | Volga Exposure | volga_exposure | {max_volga: 0.3} |
| Risk-Exec | Circuit Breaker | circuit_breaker | {max_daily_loss: 0.05, max_consecutive_losses: 5, cooldown_seconds: 300} |
| Risk-Exec | Slippage Guard | slippage_guard | {max_slippage_pct: 0.02} |
| Risk-Exec | Max Consecutive Losses | max_consecutive_losses | {max_streak: 5} |
| Risk-Exec | Cooldown Period | cooldown_period | {cooldown_trades: 3} |
| Risk-Exec | Position Timeout | position_timeout | {max_hold_seconds: 86400} |
| Risk-Regime | Volatility Regime | volatility_regime_check | {target_regime: "normal"} |
| Risk-Regime | Correlation Regime Shift | correlation_regime_shift | {correlation_spike_threshold: 0.3} |
| Risk-Regime | Toxicity Detection | toxicity_detection | {vpin_threshold: 0.7} |
| Risk-Regime | Order Flow Imbalance | order_flow_imbalance | {imbalance_threshold: 0.3} |
| Risk-Construct | Kelly Criterion | position_sizer | {method: "kelly"} |
| Risk-Construct | Risk Parity | risk_parity_allocation | {} |
| Risk-Construct | Mean-Variance Optimization | mean_variance_optimization | {risk_aversion: 1.0} |
| Risk-Construct | Black-Litterman | black_litterman | {views: {}, tau: 0.05} |
| Risk-Construct | Hierarchical Risk Parity | hierarchical_risk_parity | {} |
| Auto-Withdrawal | Withdraw to Safe Wallet | withdraw_to_safe_wallet | {withdraw_pct: 50, source: "profits", target_currency: "USDC"} |
| Auto-Withdrawal | Withdrawal Strategy | withdrawal_strategy | {steps: []} |
| Analysis | Bayesian Inference | bayesian_inference | {prior: 0.5} |
| Analysis | Monte Carlo | monte_carlo | {simulations: 1000, days: 30} |
| Analysis | Backtest | backtest | {} |
| Analysis | SHAP Explainability | shap_explainability | {} |
| Performance | Current Balance | performance | {metric: "current-balance", window: 50} |
| Performance | Total P&L | performance | {metric: "total-pnl", window: 50} |
| Performance | Win Rate | performance | {metric: "win-rate", window: 50} |
| Performance | Avg R:R | performance | {metric: "avg-rr", window: 50} |
| Performance | Sharpe | performance | {metric: "sharpe", window: 50} |
| Performance | Sortino | performance | {metric: "sortino", window: 50} |
| Performance | Calmar | performance | {metric: "calmar", window: 50} |
| Performance | Max Drawdown | performance | {metric: "max-drawdown", window: 50} |
| Performance | Profit Factor | performance | {metric: "profit-factor", window: 50} |
| Performance | Kelly % | performance | {metric: "kelly-optimal", window: 50} |
| Performance | Edge | performance | {metric: "edge", window: 50} |
| Performance | Brier Score | performance | {metric: "brier-score", window: 50} |
| Performance | Trade Count | performance | {metric: "trade-count", window: 50} |
| Performance | SQN | performance | {metric: "sqn", window: 50} |
| Performance | Recovery Factor | performance | {metric: "recovery-factor", window: 50} |
| Performance | Largest Win | performance | {metric: "largest-win", window: 50} |
| Performance | Largest Loss | performance | {metric: "largest-loss", window: 50} |
| Performance | Consecutive Streak | performance | {metric: "consecutive-streak", window: 50} |

---

## APPENDIX B: API ENDPOINT REFERENCE

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/withdrawal/wallets | Create safe wallet |
| GET | /api/withdrawal/wallets | List safe wallets |
| GET | /api/withdrawal/wallets/{id} | Get safe wallet |
| GET | /api/withdrawal/balance | Total safe balance |
| POST | /api/withdrawal/transfer | Transfer to safe wallet |
| GET | /api/withdrawal/history | Withdrawal history |
| POST | /api/withdrawal/strategies | Create withdrawal strategy |
| GET | /api/withdrawal/strategies | List strategies |
| GET | /api/withdrawal/strategies/{id} | Get strategy |
| PUT | /api/withdrawal/strategies/{id} | Update strategy |
| DELETE | /api/withdrawal/strategies/{id} | Delete strategy |
| POST | /api/withdrawal/strategies/{id}/evaluate | Evaluate strategy |
| POST | /api/withdrawal/strategies/{id}/toggle | Toggle active/inactive |
