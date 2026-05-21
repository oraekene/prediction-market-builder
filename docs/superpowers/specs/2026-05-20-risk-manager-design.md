# Risk Manager — Full Implementation Design

> **Status:** Approved design spec
> **Date:** 2026-05-20
> **Project:** Prediction Market Strategy Builder

## Overview

Risk management is implemented as a first-class strategy in the central strategy engine — not a separate module with limited functionality. Risk management uses the same node graph system as trading strategies. Users compose risk logic visually by adding risk-specific node types (VaR checks, drawdown monitors, position scalers) to any strategy's node graph. The unified graph executor evaluates all node types identically.

## Architecture

```
Strategy Engine (node graph executor)
  ├── NodeRegistry: maps node_type → handler function
  │     Trading: market_input, threshold_condition, trade_action
  │     Risk:    var_check, drawdown_monitor, correlation_check,
  │              concentration_check, position_sizer, hedge_action,
  │              rebalance_action, alert_action
  │     Logic:   and_gate, or_gate, not_gate
  │
  ├── Handlers call backing services:
  │     risk_calculator.py   — VaR, ES, correlation, drawdown math
  │     portfolio_manager.py — Position tracking, rebalancing, hedging
  │     tabpfn_integration.py — Quantile regression VaR
  │
  ├── Risk API:
  │     GET /api/risk/summary
  │     GET /api/risk/var
  │     GET /api/risk/correlation
  │     GET /api/risk/drawdown
  │     GET /api/risk/portfolio
  │
  └── Frontend (AnalyticsPage):
        RiskMetricsCards, CorrelationMatrix, DrawdownChart
        NodePalette gets risk node types
```

## Components

### 1. Node Graph Executor (`app/services/node_executor.py`)

Replaces the flat `ConditionBuilder` pattern with a proper directed graph executor.

- **`NodeHandler`** protocol: `(node: dict, inputs: dict[str, Any], context: ExecutionContext) -> Any`
- **`NodeRegistry`**: `dict[str, NodeHandler]` — registered at startup
- **`ExecutionContext`**: carries `market`, `signal`, `portfolio`, `risk_calculator`, `portfolio_manager`, `tabpfn`
- **`GraphExecutor.execute(nodes, edges, context)`**: topologically sorts nodes, evaluates in order, passes outputs as inputs to downstream nodes, returns final action output

Execution flow:
1. Build adjacency list from edges
2. Topological sort (Kahn's algorithm)
3. For each node in order: collect inputs from upstream outputs, call handler, store output
4. Return the output of the last node (or the first action-type node)

### 2. Node Type Definitions

**Trading nodes** (existing, kept as-is):
- `market_input`: exposes market data fields
- `threshold_condition`: lt/gt/between/outside checks on a field
- `trade_action`: produces buy/sell/hold recommendation

**Risk condition nodes** (new):
- `var_check`: computes VaR and ES for portfolio at given confidence; triggers if VaR > limit
- `drawdown_monitor`: checks if current drawdown exceeds max_drawdown threshold
- `correlation_check`: checks if a market's correlation to portfolio exceeds max_correlation
- `concentration_check`: checks if any single position exceeds max_concentration of portfolio

**Risk action nodes** (new):
- `position_sizer`: computes position size via Kelly, volatility-based, or fixed method
- `hedge_action`: suggests a hedge trade for a correlated position
- `rebalance_action`: suggests portfolio rebalancing trades to meet target allocations
- `alert_action`: emits a notification when triggered

**Logic nodes** (new):
- `and_gate`: boolean AND of all inputs
- `or_gate`: boolean OR of all inputs
- `not_gate`: boolean NOT of single input

### 3. Risk Calculator (`app/services/risk_calculator.py`)

Pure calculation service — no state, no DB.

| Method | Description |
|--------|-------------|
| `historical_var(returns, confidence)` | Sorts returns, takes quantile at (1-confidence) |
| `parametric_var(returns, confidence)` | Assumes normal, uses mean - z * std |
| `expected_shortfall(returns, confidence)` | Mean of returns below VaR threshold |
| `correlation_matrix(portfolio_returns)` | Pearson correlations between all position pairs |
| `max_drawdown(capital_series)` | Largest peak-to-trough decline |
| `current_drawdown(peak, current)` | Simple percentage from peak |
| `concentration(positions)` | Herfindahl-Hirschman Index of position sizes |
| `portfolio_volatility(returns)` | Annualized volatility from daily returns |
| `value_at_risk(positions, returns, confidence)` | Position-level VaR breakdown |

### 4. Portfolio Manager (`app/services/portfolio_manager.py`)

Stateful service that tracks portfolio state across evaluations.

| Method | Description |
|--------|-------------|
| `__init__(initial_capital)` | Sets up tracker with initial capital |
| `update(portfolio_state)` | Updates current capital, positions, peak |
| `dynamic_position_size(portfolio, signal, volatility, method)` | Sizing via Kelly, volatility-scaled, or fixed fraction |
| `suggest_rebalance(positions, target_allocations, threshold)` | Returns list of suggested trades to rebalance |
| `suggest_hedge(positions, returns_matrix)` | Identifies positions needing hedges, suggests offset |
| `volatility_regime(returns)` | Classifies as "low", "normal", or "high" volatility |
| `track_drawdown(current_capital)` | Updates peak, returns drawdown metrics |

### 5. TabPFN Quantile Integration (`app/services/tabpfn_integration.py`)

Extends `TabPFNService` with quantile regression for VaR.

- `predict_returns_distribution(features, historical_returns)` — uses TabPFNRegressor to predict return distribution given market features
- `tabpfn_var(features, historical_returns, confidence)` — extracts VaR from predicted distribution
- Falls back to `historical_var()` if TabPFN package is not installed or if regression is unavailable

TabPFNService already exists at `app/ai/tabpfn_service.py` with `predict_probability`, `validate_signal`, and `get_feature_importance`. We add regression capability for returns prediction.

### 6. Risk API (`app/routers/risk.py`)

| Endpoint | Method | Returns |
|----------|--------|---------|
| `GET /api/risk/summary` | JSON | `{var_95, es_95, max_drawdown, current_drawdown, concentration, portfolio_volatility}` |
| `GET /api/risk/var` | JSON | `{historical: float, parametric: float, tabpfn: float \| null, confidence: float}` |
| `GET /api/risk/correlation` | JSON | `{pairs: [{asset_a, asset_b, correlation}]}` |
| `GET /api/risk/drawdown` | JSON | `{current_drawdown, peak_capital, current_capital, max_drawdown}` |
| `GET /api/risk/portfolio` | JSON | `{positions: [{market_id, size, var_contribution, concentration_pct}]}` |

Data sources: portfolio state from PortfolioManager, trade data from Trade model, return series computed from executed trades.

### 7. Frontend

**New files:**
- `src/types/risk.ts` — `RiskSummary`, `VaRBreakdown`, `CorrelationPair`, `DrawdownMetrics`, `PositionRisk`
- `src/hooks/useRisk.ts` — `useRiskSummary()`, `useVaR()`, `useCorrelation()`, `useDrawdown()`, `usePortfolioRisk()`
- `src/components/analytics/RiskDashboard.tsx` — main dashboard compositing the cards below
- `src/components/analytics/RiskMetricsCards.tsx` — 4 metric cards (VaR 95%, Drawdown, Concentration, Volatility)
- `src/components/analytics/CorrelationMatrix.tsx` — table of position correlations
- `src/components/analytics/DrawdownChart.tsx` — simple SVG sparkline of drawdown history

**Modified files:**
- `src/lib/api.ts` — add `fetchRiskSummary`, `fetchVaR`, `fetchCorrelation`, `fetchDrawdown`, `fetchPortfolioRisk`
- `src/pages/AnalyticsPage.tsx` — integrate RiskDashboard below existing analytics content
- Strategy node type lists in frontend to include risk node types

### 8. Test Plan

| Test File | Tests |
|-----------|-------|
| `tests/test_node_executor.py` | Topo sort, handler dispatch, error propagation, empty graph |
| `tests/test_risk_calculator.py` | Historical VaR, parametric VaR, ES, correlation, concentration, edge cases |
| `tests/test_portfolio_manager.py` | Position sizing (3 methods), rebalance suggestions, drawdown tracking, volatility regime |
| `tests/test_risk_api.py` | All 5 endpoints via test client |
| `tests/test_risk_node_handlers.py` | Each risk node type handler produces correct output given mock context |
| `tests/test_risk_manager.py` (update) | Ensure existing tests still pass with refactored code |

### 9. File Manifest

```
CREATE:
  backend/app/services/node_executor.py
  backend/app/services/risk_calculator.py
  backend/app/services/portfolio_manager.py
  backend/app/services/tabpfn_integration.py
  backend/app/services/risk_node_handlers.py
  backend/app/routers/risk.py
  backend/tests/test_node_executor.py
  backend/tests/test_risk_calculator.py
  backend/tests/test_portfolio_manager.py
  backend/tests/test_risk_api.py
  backend/tests/test_risk_node_handlers.py
  frontend/src/types/risk.ts
  frontend/src/hooks/useRisk.ts
  frontend/src/components/analytics/RiskDashboard.tsx
  frontend/src/components/analytics/RiskMetricsCards.tsx
  frontend/src/components/analytics/CorrelationMatrix.tsx
  frontend/src/components/analytics/DrawdownChart.tsx

MODIFY:
  backend/app/services/strategy_engine.py — use GraphExecutor instead of ConditionBuilder
  backend/app/services/risk_manager.py — refactor to use node_executor + risk_node_handlers
  backend/app/main.py — register risk router
  backend/tests/test_risk_manager.py — ensure backward compat
  frontend/src/lib/api.ts — add risk endpoints
  frontend/src/pages/AnalyticsPage.tsx — integrate RiskDashboard
  frontend/src/components/strategies/NodePalette.tsx — add risk node types
```
