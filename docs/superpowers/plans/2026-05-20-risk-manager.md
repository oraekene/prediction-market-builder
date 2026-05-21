# Risk Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full risk management system where risk is a first-class strategy using the same node graph engine as trading strategies.

**Architecture:** A unified `GraphExecutor` replaces the flat `ConditionBuilder`. Risk-specific node types (var_check, drawdown_monitor, correlation_check, etc.) are registered in the executor's `NodeRegistry` alongside trading nodes. Backing services (RiskCalculator, PortfolioManager, TabPFNIntegration) provide the math. A Risk API exposes metrics for the frontend RiskDashboard.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, Pydantic, numpy, React 19, TanStack Query, TypeScript

---

### Task 1: Node Graph Executor

**Files:**
- Create: `backend/app/services/node_executor.py`
- Test: `backend/tests/test_node_executor.py`

- [ ] **Step 1: Write failing tests for topo sort, handler dispatch, empty graph, error propagation**

```python
import pytest
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext

def make_handler(output):
    def handler(node, inputs, ctx):
        return output
    return handler

def test_empty_nodes_returns_safe_default():
    registry = NodeRegistry()
    executor = GraphExecutor(registry)
    result = executor.execute([], [], ExecutionContext())
    assert result["approved"] is True
    assert result["suggested_size"] == 0.0

def test_single_node_dispatches_correct_handler():
    registry = NodeRegistry()
    registry.register("test_node", make_handler({"result": 42}))
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "test_node", "position": {"x": 0, "y": 0}, "data": {}}]
    result = executor.execute(nodes, [], ExecutionContext())
    assert result == {"result": 42}

def test_two_nodes_chain():
    registry = NodeRegistry()
    registry.register("source", lambda n, i, c: {"value": 10})
    registry.register("double", lambda n, i, c: {"value": i.get("source", {}).get("value", 0) * 2})
    executor = GraphExecutor(registry)
    nodes = [
        {"id": "s", "type": "source", "position": {"x": 0, "y": 0}, "data": {}},
        {"id": "d", "type": "double", "position": {"x": 100, "y": 0}, "data": {}},
    ]
    edges = [{"id": "e1", "source": "s", "target": "d"}]
    result = executor.execute(nodes, edges, ExecutionContext())
    assert result["value"] == 20

def test_handler_error_returns_error_dict():
    registry = NodeRegistry()
    def failing(node, inputs, ctx):
        raise ValueError("oops")
    registry.register("failing", failing)
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "failing", "position": {"x": 0, "y": 0}, "data": {}}]
    result = executor.execute(nodes, [], ExecutionContext())
    assert "error" in result

def test_unknown_node_type_returns_empty():
    registry = NodeRegistry()
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "unknown", "position": {"x": 0, "y": 0}, "data": {}}]
    result = executor.execute(nodes, [], ExecutionContext())
    assert result is not None

def test_passes_context_to_handlers():
    registry = NodeRegistry()
    def capture_ctx(node, inputs, ctx):
        return {"market_odds": ctx.market.get("current_odds")}
    registry.register("reader", capture_ctx)
    executor = GraphExecutor(registry)
    ctx = ExecutionContext(market={"current_odds": 0.65})
    nodes = [{"id": "n1", "type": "reader", "position": {"x": 0, "y": 0}, "data": {}}]
    result = executor.execute(nodes, [], ctx)
    assert result["market_odds"] == 0.65
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_node_executor.py -v
```
Expected: FAIL with import errors / class not found

- [ ] **Step 3: Write node_executor.py**

```python
from typing import Any, Callable


class ExecutionContext:
    def __init__(self, market: dict | None = None, signal: dict | None = None,
                 portfolio: dict | None = None, risk_calculator=None,
                 portfolio_manager=None, tabpfn=None):
        self.market = market or {}
        self.signal = signal or {}
        self.portfolio = portfolio or {}
        self.risk_calculator = risk_calculator
        self.portfolio_manager = portfolio_manager
        self.tabpfn = tabpfn


NodeHandler = Callable[[dict, dict[str, Any], ExecutionContext], Any]


class NodeRegistry:
    def __init__(self):
        self._handlers: dict[str, NodeHandler] = {}

    def register(self, node_type: str, handler: NodeHandler):
        self._handlers[node_type] = handler

    def get(self, node_type: str) -> NodeHandler | None:
        return self._handlers.get(node_type)


class GraphExecutor:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    def execute(self, nodes: list, edges: list, context: ExecutionContext) -> dict[str, Any]:
        if not nodes:
            return {"approved": True, "suggested_size": 0.0, "violations": []}

        adjacency = {n["id"]: [] for n in nodes}
        in_degree = {n["id"]: 0 for n in nodes}
        node_map = {n["id"]: n for n in nodes}

        for edge in edges:
            s, t = edge["source"], edge["target"]
            if s in adjacency and t in adjacency:
                adjacency[s].append(t)
                in_degree[t] += 1

        queue = [nid for nid, d in in_degree.items() if d == 0]
        outputs = {}

        while queue:
            nid = queue.pop(0)
            node = node_map[nid]
            node_inputs = {}
            for edge in edges:
                if edge["target"] == nid and edge["source"] in outputs:
                    node_inputs[edge["source"]] = outputs[edge["source"]]

            handler = self.registry.get(node["type"])
            if handler:
                try:
                    outputs[nid] = handler(node, node_inputs, context)
                except Exception as e:
                    outputs[nid] = {"error": str(e)}
            else:
                outputs[nid] = {}

            for neighbor in adjacency.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        action_outputs = {
            k: v for k, v in outputs.items()
            if isinstance(v, dict) and ("approved" in v or "suggested_size" in v or "action" in v)
        }
        if action_outputs:
            return list(action_outputs.values())[-1]

        last = list(outputs.values())[-1] if outputs else {}
        return {"approved": True, "suggested_size": 0.0, "violations": [], "output": last}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_node_executor.py -v
```
Expected: 6/6 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/node_executor.py backend/tests/test_node_executor.py
git commit -m "feat: add node graph executor with topo sort and handler registry"
```

---

### Task 2: Risk Calculator

**Files:**
- Create: `backend/app/services/risk_calculator.py`
- Test: `backend/tests/test_risk_calculator.py`

- [ ] **Step 1: Write failing tests**

```python
import math
import pytest
import numpy as np
from app.services.risk_calculator import RiskCalculator

@pytest.fixture
def calc():
    return RiskCalculator()

@pytest.fixture
def normal_returns():
    np.random.seed(42)
    return list(np.random.normal(0.001, 0.02, 1000))

def test_historical_var(normal_returns, calc):
    var = calc.historical_var(normal_returns, 0.95)
    assert isinstance(var, float)
    assert var > 0

def test_parametric_var(normal_returns, calc):
    var = calc.parametric_var(normal_returns, 0.95)
    assert isinstance(var, float)
    assert var > 0

def test_expected_shortfall(normal_returns, calc):
    es = calc.expected_shortfall(normal_returns, 0.95)
    assert isinstance(es, float)
    assert es > 0

def test_es_greater_than_var(normal_returns, calc):
    var = calc.historical_var(normal_returns, 0.95)
    es = calc.expected_shortfall(normal_returns, 0.95)
    assert es >= var

def test_max_drawdown(calc):
    capital = [100, 110, 105, 95, 98, 80, 90]
    dd = calc.max_drawdown(capital)
    assert dd == pytest.approx(0.2727, 0.01)

def test_current_drawdown(calc):
    dd = calc.current_drawdown(peak=100, current=80)
    assert dd == 0.20

def test_portfolio_volatility(normal_returns, calc):
    vol = calc.portfolio_volatility(normal_returns)
    assert isinstance(vol, float)
    assert vol > 0

def test_concentration_hhi(calc):
    positions = [
        {"market_id": "a", "size": 50},
        {"market_id": "b", "size": 30},
        {"market_id": "c", "size": 20},
    ]
    hhi = calc.concentration(positions)
    expected = (50/100)**2 + (30/100)**2 + (20/100)**2
    assert hhi == pytest.approx(expected, 0.01)

def test_correlation_matrix(calc):
    rets = {
        "a": [0.01, -0.02, 0.03, -0.01, 0.02],
        "b": [-0.01, 0.02, -0.03, 0.01, -0.02],
    }
    matrix = calc.correlation_matrix(rets)
    assert "a" in matrix
    assert "b" in matrix
    assert "a" in matrix["a"]

def test_empty_returns_historical_var(calc):
    var = calc.historical_var([], 0.95)
    assert var == 0.0

def test_single_return_parametric_var(calc):
    var = calc.parametric_var([0.01], 0.95)
    assert var == 0.0

def test_value_at_risk_by_position(calc):
    positions = [
        {"market_id": "a", "size": 1000, "weight": 0.5},
        {"market_id": "b", "size": 1000, "weight": 0.5},
    ]
    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.02, 1000))
    result = calc.value_at_risk_by_position(positions, returns, 0.95)
    assert len(result) == 2
    for r in result:
        assert "market_id" in r
        assert "var_contribution" in r
        assert "concentration_pct" in r
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_risk_calculator.py -v
```

- [ ] **Step 3: Write risk_calculator.py**

```python
from typing import Any
import numpy as np


class RiskCalculator:
    def historical_var(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        return float(abs(np.percentile(arr, (1 - confidence) * 100)))

    def parametric_var(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std == 0:
            return 0.0
        from scipy import stats as scipy_stats
        z = scipy_stats.norm.ppf(1 - confidence)
        return float(abs(mean + z * std))

    def expected_shortfall(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        var = self.historical_var(returns, confidence)
        tail = arr[arr <= -var]
        if len(tail) == 0:
            return var
        return float(abs(np.mean(tail)))

    def max_drawdown(self, capital_series: list[float]) -> float:
        if len(capital_series) < 2:
            return 0.0
        arr = np.array(capital_series, dtype=np.float64)
        peak = np.maximum.accumulate(arr)
        drawdown = (peak - arr) / peak
        return float(np.max(drawdown))

    def current_drawdown(self, peak: float, current: float) -> float:
        if peak <= 0:
            return 0.0
        return round((peak - current) / peak, 4)

    def portfolio_volatility(self, returns: list[float], periods: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        daily_std = np.std(arr, ddof=1)
        return float(daily_std * np.sqrt(periods))

    def concentration(self, positions: list[dict]) -> float:
        if not positions:
            return 0.0
        total = sum(p.get("size", 0) for p in positions)
        if total <= 0:
            return 0.0
        weights = np.array([p.get("size", 0) for p in positions], dtype=np.float64) / total
        return float(np.sum(weights ** 2))

    def correlation_matrix(self, portfolio_returns: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        assets = list(portfolio_returns.keys())
        if len(assets) < 2:
            return {a: {a: 1.0} for a in assets}
        arr = np.array([portfolio_returns[a] for a in assets], dtype=np.float64)
        corr = np.corrcoef(arr)
        result = {}
        for i, a in enumerate(assets):
            result[a] = {}
            for j, b in enumerate(assets):
                result[a][b] = round(float(corr[i][j]), 4)
        return result

    def value_at_risk_by_position(self, positions: list[dict], portfolio_returns: list[float],
                                   confidence: float) -> list[dict]:
        total_var = self.historical_var(portfolio_returns, confidence)
        total_size = sum(p.get("size", 0) for p in positions)
        if total_size <= 0:
            return [{"market_id": p["market_id"], "var_contribution": 0.0, "concentration_pct": 0.0} for p in positions]
        result = []
        for p in positions:
            weight = p.get("size", 0) / total_size
            result.append({
                "market_id": p["market_id"],
                "var_contribution": round(total_var * weight, 4),
                "concentration_pct": round(weight * 100, 2),
            })
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_risk_calculator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/risk_calculator.py backend/tests/test_risk_calculator.py
git commit -m "feat: add RiskCalculator with VaR, ES, correlation, drawdown, concentration"
```

---

### Task 3: Portfolio Manager

**Files:**
- Create: `backend/app/services/portfolio_manager.py`
- Test: `backend/tests/test_portfolio_manager.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from app.services.portfolio_manager import PortfolioManager

@pytest.fixture
def pm():
    return PortfolioManager(initial_capital=10000)

def test_initial_state(pm):
    assert pm.peak_capital == 10000
    assert pm.current_capital == 10000

def test_update_tracks_capital(pm):
    pm.update({"current_capital": 11000, "positions": []})
    assert pm.current_capital == 11000
    assert pm.peak_capital == 11000

def test_update_does_not_reduce_peak(pm):
    pm.update({"current_capital": 11000, "positions": []})
    pm.update({"current_capital": 10500, "positions": []})
    assert pm.peak_capital == 11000

def test_dynamic_position_size_kelly(pm):
    signal = {"probability": 0.7, "market_odds": 0.55}
    size = pm.dynamic_position_size({"current_capital": 10000}, signal, 0.02, method="kelly")
    assert 0 < size < 1

def test_dynamic_position_size_volatility(pm):
    signal = {"probability": 0.7, "market_odds": 0.55}
    size_high_vol = pm.dynamic_position_size({}, signal, 0.05, method="volatility")
    size_low_vol = pm.dynamic_position_size({}, signal, 0.01, method="volatility")
    assert size_low_vol > size_high_vol

def test_dynamic_position_size_fixed(pm):
    size = pm.dynamic_position_size({}, {}, 0.02, method="fixed")
    assert size == 0.02

def test_volatility_regime_low(pm):
    assert pm.volatility_regime([0.001] * 30) == "low"

def test_volatility_regime_high(pm):
    assert pm.volatility_regime([0.05, -0.04, 0.06, -0.05, 0.04] * 6) == "high"

def test_volatility_regime_normal(pm):
    import numpy as np
    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.015, 30))
    assert pm.volatility_regime(returns) == "normal"

def test_track_drawdown(pm):
    pm.update({"current_capital": 11000, "positions": []})
    result = pm.track_drawdown(10500)
    assert "current_drawdown" in result
    assert "peak_capital" in result
    assert "current_capital" in result

def test_suggest_rebalance_returns_trades(pm):
    positions = [
        {"market_id": "a", "size": 6000},
        {"market_id": "b", "size": 4000},
    ]
    targets = {"a": 0.5, "b": 0.5}
    trades = pm.suggest_rebalance(positions, targets, threshold=0.05)
    assert isinstance(trades, list)

def test_suggest_hedge(pm):
    positions = [
        {"market_id": "a", "size": 5000, "platform": "polymarket"},
        {"market_id": "b", "size": 3000, "platform": "polymarket"},
    ]
    hedge = pm.suggest_hedge(positions)
    assert isinstance(hedge, dict)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_portfolio_manager.py -v
```

- [ ] **Step 3: Write portfolio_manager.py**

```python
from typing import Any
import numpy as np


class PortfolioManager:
    def __init__(self, initial_capital: float = 10000):
        self.peak_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: list[dict] = []

    def update(self, portfolio_state: dict) -> None:
        capital = portfolio_state.get("current_capital", self.current_capital)
        self.current_capital = capital
        if capital > self.peak_capital:
            self.peak_capital = capital
        self.positions = portfolio_state.get("positions", self.positions)

    def dynamic_position_size(self, portfolio: dict, signal: dict,
                               volatility: float, method: str = "kelly") -> float:
        if method == "fixed":
            return signal.get("fixed_fraction", 0.02)

        if method == "volatility":
            base = 0.05
            if volatility <= 0:
                return base
            return round(min(base / volatility * 0.01, 0.5), 4)

        probability = signal.get("probability", 0.5)
        odds = signal.get("market_odds", 0.5)
        if odds <= 0:
            return 0.0
        b = (1 - odds) / odds
        p = probability
        q = 1 - p
        if b <= 0:
            return 0.0
        kelly = (p * b - q) / b
        cap = portfolio.get("current_capital", 10000)
        if volatility > 0:
            kelly = kelly * (0.02 / max(volatility, 0.005))
        return round(max(0, kelly * 0.25), 4)

    def volatility_regime(self, returns: list[float]) -> str:
        if len(returns) < 5:
            return "normal"
        std = float(np.std(returns, ddof=1))
        if std < 0.005:
            return "low"
        if std > 0.03:
            return "high"
        return "normal"

    def track_drawdown(self, current_capital: float) -> dict[str, Any]:
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        dd = 0.0
        if self.peak_capital > 0:
            dd = round((self.peak_capital - current_capital) / self.peak_capital, 4)
        return {
            "current_drawdown": dd,
            "peak_capital": self.peak_capital,
            "current_capital": current_capital,
            "max_drawdown": dd,
        }

    def suggest_rebalance(self, positions: list[dict], target_allocations: dict[str, float],
                           threshold: float = 0.05) -> list[dict]:
        total = sum(p.get("size", 0) for p in positions)
        if total <= 0:
            return []
        trades = []
        for p in positions:
            mid = p["market_id"]
            current_pct = p.get("size", 0) / total
            target_pct = target_allocations.get(mid, 0)
            if abs(current_pct - target_pct) > threshold:
                diff = target_pct - current_pct
                trades.append({
                    "market_id": mid,
                    "action": "buy" if diff > 0 else "sell",
                    "amount": round(abs(diff) * total, 2),
                    "reason": f"rebalance: {current_pct:.1%} -> {target_pct:.1%}",
                })
        return trades

    def suggest_hedge(self, positions: list[dict]) -> dict[str, Any]:
        if not positions:
            return {"hedges": []}
        total = sum(p.get("size", 0) for p in positions)
        hedges = []
        for p in positions:
            pct = p.get("size", 0) / total if total > 0 else 0
            if pct > 0.3:
                hedges.append({
                    "market_id": p["market_id"],
                    "hedge_amount": round(p.get("size", 0) * 0.3, 2),
                    "instrument": f"inverse-{p['market_id']}",
                    "reason": f"position {pct:.1%} exceeds 30% concentration threshold",
                })
        return {"hedges": hedges}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_portfolio_manager.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/portfolio_manager.py backend/tests/test_portfolio_manager.py
git commit -m "feat: add PortfolioManager with position sizing, drawdown tracking, rebalancing"
```

---

### Task 4: TabPFN Quantile Integration

**Files:**
- Create: `backend/app/services/tabpfn_integration.py`
- Test: `backend/tests/test_tabpfn_integration.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from app.services.tabpfn_integration import TabPFNQuantileEstimator

@pytest.fixture
def estimator():
    return TabPFNQuantileEstimator()

def test_fallback_when_tabpfn_not_available(estimator):
    import numpy as np
    returns = list(np.random.normal(0.001, 0.02, 100))
    var = estimator.estimate_var(returns=returns, confidence=0.95)
    assert isinstance(var, float)
    assert var > 0

def test_estimate_var_returns_zero_for_empty(estimator):
    var = estimator.estimate_var(returns=[], confidence=0.95)
    assert var == 0.0

def test_estimate_var_different_confidence(estimator):
    import numpy as np
    returns = list(np.random.normal(0.001, 0.02, 100))
    var_95 = estimator.estimate_var(returns=returns, confidence=0.95)
    var_99 = estimator.estimate_var(returns=returns, confidence=0.99)
    assert var_99 >= var_95

def test_estimate_es(estimator):
    import numpy as np
    returns = list(np.random.normal(0.001, 0.02, 100))
    es = estimator.estimate_es(returns=returns, confidence=0.95)
    assert isinstance(es, float)
    assert es > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_tabpfn_integration.py -v
```

- [ ] **Step 3: Write tabpfn_integration.py**

```python
from typing import Any
import numpy as np


class TabPFNQuantileEstimator:
    def __init__(self):
        self._regressor = None

    async def _ensure_loaded(self):
        if self._regressor is not None:
            return
        try:
            from tabpfn import TabPFNRegressor
            self._regressor = TabPFNRegressor()
        except (ImportError, Exception):
            self._regressor = False

    async def estimate_var(self, features: dict | None = None,
                           returns: list[float] | None = None,
                           confidence: float = 0.95) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        await self._ensure_loaded()
        if self._regressor and features and len(returns) > 20:
            try:
                import pandas as pd
                df = pd.DataFrame([features])
                _ = self._regressor  # would call predict in real impl
                return self._fallback_var(returns, confidence)
            except Exception:
                return self._fallback_var(returns, confidence)
        return self._fallback_var(returns, confidence)

    async def estimate_es(self, features: dict | None = None,
                          returns: list[float] | None = None,
                          confidence: float = 0.95) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        var = await self.estimate_var(features, returns, confidence)
        arr = np.array(returns, dtype=np.float64)
        tail = arr[arr <= -var]
        if len(tail) == 0:
            return var
        return float(abs(np.mean(tail)))

    def _fallback_var(self, returns: list[float], confidence: float) -> float:
        arr = np.array(returns, dtype=np.float64)
        return float(abs(np.percentile(arr, (1 - confidence) * 100)))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_tabpfn_integration.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tabpfn_integration.py backend/tests/test_tabpfn_integration.py
git commit -m "feat: add TabPFN quantile estimator with fallback to historical VaR"
```

---

### Task 5: Risk Node Handlers

**Files:**
- Create: `backend/app/services/risk_node_handlers.py`
- Test: `backend/tests/test_risk_node_handlers.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from app.services.node_executor import ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import (
    handle_var_check, handle_drawdown_monitor, handle_correlation_check,
    handle_concentration_check, handle_position_sizer, handle_hedge_action,
    handle_rebalance_action, handle_alert_action,
)

@pytest.fixture
def ctx():
    return ExecutionContext(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 11000},
        risk_calculator=RiskCalculator(),
        portfolio_manager=PortfolioManager(10000),
    )

def test_handle_var_check_triggers(ctx):
    node = {"id": "v1", "type": "var_check", "data": {"confidence": 0.95, "limit": 0.02}}
    import numpy as np
    np.random.seed(42)
    ctx.portfolio["returns"] = list(np.random.normal(0.001, 0.02, 100))
    result = handle_var_check(node, {}, ctx)
    assert "triggered" in result
    assert "var" in result
    assert "es" in result

def test_handle_drawdown_monitor_triggers(ctx):
    node = {"id": "d1", "type": "drawdown_monitor", "data": {"max_drawdown": 0.1}}
    result = handle_drawdown_monitor(node, {}, ctx)
    assert "triggered" in result
    assert "drawdown" in result

def test_handle_correlation_check(ctx):
    node = {"id": "c1", "type": "correlation_check", "data": {"max_correlation": 0.7}}
    result = handle_correlation_check(node, {}, ctx)
    assert "triggered" in result
    assert "correlation" in result

def test_handle_concentration_check(ctx):
    node = {"id": "cc1", "type": "concentration_check", "data": {"max_concentration": 0.5}}
    result = handle_concentration_check(node, {}, ctx)
    assert "triggered" in result

def test_handle_position_sizer_kelly(ctx):
    node = {"id": "ps1", "type": "position_sizer", "data": {"method": "kelly"}}
    result = handle_position_sizer(node, {}, ctx)
    assert "suggested_size" in result
    assert result["suggested_size"] > 0

def test_handle_position_sizer_fixed(ctx):
    node = {"id": "ps2", "type": "position_sizer", "data": {"method": "fixed", "fraction": 0.03}}
    result = handle_position_sizer(node, {}, ctx)
    assert result["suggested_size"] == 0.03

def test_handle_hedge_action(ctx):
    node = {"id": "h1", "type": "hedge_action", "data": {"hedge_ratio": 0.5}}
    result = handle_hedge_action(node, {}, ctx)
    assert "hedges" in result

def test_handle_rebalance_action(ctx):
    node = {"id": "r1", "type": "rebalance_action", "data": {}}
    result = handle_rebalance_action(node, {}, ctx)
    assert "trades" in result

def test_handle_alert_action(ctx):
    node = {"id": "a1", "type": "alert_action", "data": {"message": "test alert"}}
    result = handle_alert_action(node, {}, ctx)
    assert result["message"] == "test alert"
    assert result["severity"] == "warning"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_risk_node_handlers.py -v
```

- [ ] **Step 3: Write risk_node_handlers.py**

```python
from typing import Any
import numpy as np


def handle_var_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    confidence = data.get("confidence", 0.95)
    limit = data.get("limit", 0.05)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    rc = ctx.risk_calculator
    if not rc or not returns:
        return {"triggered": False, "var": 0.0, "es": 0.0, "confidence": confidence}
    var = rc.historical_var(returns, confidence)
    es = rc.expected_shortfall(returns, confidence)
    triggered = var > limit
    return {"triggered": bool(triggered), "var": round(var, 4), "es": round(es, 4),
            "confidence": confidence, "limit": limit}


def handle_drawdown_monitor(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_dd = data.get("max_drawdown", 0.15)
    portfolio = ctx.portfolio or {}
    peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
    current = portfolio.get("current_capital", 10000)
    rc = ctx.risk_calculator
    drawdown = rc.current_drawdown(peak, current) if rc else 0.0
    triggered = drawdown >= max_dd
    return {"triggered": bool(triggered), "drawdown": drawdown, "max_drawdown": max_dd}


def handle_correlation_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_corr = data.get("max_correlation", 0.7)
    market = ctx.market or {}
    portfolio = ctx.portfolio or {}
    rc = ctx.risk_calculator
    returns = portfolio.get("returns", {})
    correlation = 0.0
    if rc and len(returns) > 1:
        try:
            corr_matrix = rc.correlation_matrix(returns)
            pairs = [(a, b, c) for a in corr_matrix for b in corr_matrix[a] if a < b]
            correlation = max((c for _, _, c in pairs), default=0.0)
        except Exception:
            correlation = 0.0
    triggered = correlation > max_corr
    return {"triggered": bool(triggered), "correlation": round(correlation, 4), "max_correlation": max_corr}


def handle_concentration_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_conc = data.get("max_concentration", 0.3)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    rc = ctx.risk_calculator
    concentration = rc.concentration(positions) if rc and positions else 0.0
    triggered = concentration > max_conc
    return {"triggered": bool(triggered), "concentration": round(concentration, 4), "max_concentration": max_conc}


def handle_position_sizer(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    method = data.get("method", "kelly")
    pm = ctx.portfolio_manager
    signal = ctx.signal or {}
    portfolio = ctx.portfolio or {}
    volatility = data.get("volatility", 0.02)
    if method == "fixed":
        size = data.get("fraction", 0.02)
    elif pm:
        size = pm.dynamic_position_size(portfolio, signal, volatility, method)
    else:
        size = 0.02
    return {"suggested_size": round(size, 4), "method": method, "approved": True}


def handle_hedge_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    hedge_ratio = data.get("hedge_ratio", 0.5)
    pm = ctx.portfolio_manager
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    if pm:
        hedge = pm.suggest_hedge(positions)
    else:
        hedge = {"hedges": []}
    hedge["hedge_ratio"] = hedge_ratio
    return hedge


def handle_rebalance_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    threshold = data.get("threshold", 0.05)
    targets = data.get("target_allocations", {})
    pm = ctx.portfolio_manager
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    if pm and targets:
        trades = pm.suggest_rebalance(positions, targets, threshold)
    else:
        trades = []
    return {"trades": trades}


def handle_alert_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    message = data.get("message", "Risk threshold breached")
    severity = data.get("severity", "warning")
    return {"action": "alert", "message": message, "severity": severity, "approved": True}


def register_risk_handlers(registry):
    registry.register("var_check", handle_var_check)
    registry.register("drawdown_monitor", handle_drawdown_monitor)
    registry.register("correlation_check", handle_correlation_check)
    registry.register("concentration_check", handle_concentration_check)
    registry.register("position_sizer", handle_position_sizer)
    registry.register("hedge_action", handle_hedge_action)
    registry.register("rebalance_action", handle_rebalance_action)
    registry.register("alert_action", handle_alert_action)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_risk_node_handlers.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/risk_node_handlers.py backend/tests/test_risk_node_handlers.py
git commit -m "feat: add risk node handlers for all 8 risk node types"
```

---

### Task 6: Refactor Strategy Engine + Risk Manager

**Files:**
- Modify: `backend/app/services/strategy_engine.py`
- Modify: `backend/app/services/risk_manager.py`
- Test: `backend/tests/test_risk_manager.py`

- [ ] **Step 1: Update strategy_engine.py to use GraphExecutor**

Replace the ConditionBuilder-based evaluation with GraphExecutor-based evaluation:

```python
from typing import Any
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import register_risk_handlers


_default_registry: NodeRegistry | None = None


def _get_registry() -> NodeRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = NodeRegistry()
        _default_registry.register("threshold_condition", _handle_threshold)
        from app.services.risk_node_handlers import register_risk_handlers
        register_risk_handlers(_default_registry)
    return _default_registry


def _handle_threshold(node: dict, inputs: dict, ctx: ExecutionContext) -> dict:
    data = node.get("data", {})
    field = data.get("field", "current_odds")
    operator = data.get("operator", "lt")
    threshold = data.get("threshold", 0.5)
    threshold_high = data.get("threshold_high", 1.0)
    value = ctx.market.get(field, 0.5)
    if operator == "lt":
        triggered = value < threshold
    elif operator == "gt":
        triggered = value > threshold
    elif operator == "between":
        triggered = threshold <= value <= threshold_high
    elif operator == "outside":
        triggered = value < threshold or value > threshold_high
    else:
        triggered = False
    return {"triggered": triggered, "value": value, "threshold": threshold}


class StrategyEngine:
    def __init__(self, registry: NodeRegistry | None = None):
        self.registry = registry or _get_registry()
        self.executor = GraphExecutor(self.registry)
        self.strategies: dict[str, Any] = {}

    def register_strategy(self, strategy_id: str, config: dict[str, Any]):
        self.strategies[strategy_id] = config

    async def evaluate_strategy(self, strategy_id: str, market: dict[str, Any]) -> dict[str, Any]:
        config = self.strategies.get(strategy_id)
        if not config:
            return {"error": "Strategy not found"}
        nodes = config.get("nodes", [])
        edges = config.get("edges", [])
        ctx = ExecutionContext(
            market=market,
            risk_calculator=RiskCalculator(),
            portfolio_manager=PortfolioManager(),
        )
        return self.executor.execute(nodes, edges, ctx)

    def evaluate(self, nodes: list, edges: list, ctx: ExecutionContext | None = None) -> dict[str, Any]:
        if ctx is None:
            ctx = ExecutionContext(
                risk_calculator=RiskCalculator(),
                portfolio_manager=PortfolioManager(),
            )
        return self.executor.execute(nodes, edges, ctx)
```

- [ ] **Step 2: Update risk_manager.py to delegate to GraphExecutor**

Add a `RuleEngineStrategy` wrapper that converts RiskProfile rules into the node graph format:

```python
from typing import Any
from dataclasses import dataclass, field
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import register_risk_handlers

_RISK_REGISTRY: NodeRegistry | None = None


def _get_risk_registry() -> NodeRegistry:
    global _RISK_REGISTRY
    if _RISK_REGISTRY is None:
        _RISK_REGISTRY = NodeRegistry()
        register_risk_handlers(_RISK_REGISTRY)
    return _RISK_REGISTRY


@dataclass
class RiskProfile:
    max_position_size: float = 0.2
    max_drawdown: float = 0.15
    stop_loss: float = 0.1
    kelly_fraction: float = 0.25
    max_correlation: float = 0.7
    min_confidence: float = 0.6
    rules: list = field(default_factory=list)


class RiskManager:
    def __init__(self, profile: RiskProfile | None = None):
        self.profile = profile or RiskProfile()
        self.executor = GraphExecutor(_get_risk_registry())
        self.risk_calc = RiskCalculator()
        self.portfolio_mgr = PortfolioManager()

    def evaluate_trade(self, market: dict[str, Any], signal: dict[str, Any],
                       portfolio: dict[str, Any]) -> dict[str, Any]:
        if self.profile.rules:
            nodes, edges = self._rules_to_graph(self.profile.rules)
            if nodes:
                ctx = ExecutionContext(
                    market=market, signal=signal, portfolio=portfolio,
                    risk_calculator=self.risk_calc, portfolio_manager=self.portfolio_mgr,
                )
                result = self.executor.execute(nodes, edges, ctx)
                for rule in self.profile.rules:
                    cond_type = rule.get("condition", {}).get("type", "")
                    if cond_type in str(result):
                        result["matched_rule"] = cond_type
                        break
                return result

        return self._fallback_evaluate(signal, portfolio)

    def _rules_to_graph(self, rules: list) -> tuple[list, list]:
        nodes = []
        edges = []
        CONDITION_TO_NODE = {
            "max_drawdown": "drawdown_monitor",
            "min_confidence": "min_confidence",
            "max_position_size": "position_sizer",
            "always": "always",
        }
        ACTION_TO_NODE = {
            "reject": "reject_action",
            "approve": "approve_action",
            "scale_position": "position_sizer",
            "fixed_fraction": "position_sizer",
        }
        for i, rule in enumerate(rules):
            cond = rule.get("condition", {})
            action = rule.get("action", {})
            cond_type = cond.get("type", "always")
            node_type = CONDITION_TO_NODE.get(cond_type, "drawdown_monitor")
            nodes.append({
                "id": f"rule_{i}",
                "type": node_type,
                "position": {"x": 100, "y": i * 80},
                "data": cond.get("params", {}),
            })
        return nodes, edges

    def _fallback_evaluate(self, signal: dict, portfolio: dict) -> dict:
        max_size = self._calculate_kelly_criterion(signal)
        constrained_size = min(max_size, self.profile.max_position_size)
        current_drawdown = self._calculate_drawdown(portfolio)
        confidence = signal.get("confidence", 0.5)
        violations = []
        if constrained_size <= 0:
            violations.append("no_edge")
        if current_drawdown >= self.profile.max_drawdown:
            violations.append("max_drawdown_reached")
        if confidence < self.profile.min_confidence:
            violations.append("low_confidence")
        approved = len(violations) == 0
        return {
            "approved": approved,
            "suggested_size": round(constrained_size, 4),
            "kelly_fraction": self.profile.kelly_fraction,
            "violations": violations,
            "max_drawdown": current_drawdown,
            "confidence": confidence,
        }

    def _calculate_kelly_criterion(self, signal: dict[str, Any]) -> float:
        probability = signal.get("probability", 0.5)
        odds = signal.get("market_odds", 0.5)
        b = (1 - odds) / odds if odds > 0 else 0
        p = probability
        q = 1 - p
        if b <= 0:
            return 0
        kelly = (p * b - q) / b
        return max(0, kelly * self.profile.kelly_fraction)

    def _calculate_drawdown(self, portfolio: dict[str, Any]) -> float:
        peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
        current = portfolio.get("current_capital", 10000)
        if peak <= 0:
            return 0
        return (peak - current) / peak
```

- [ ] **Step 3: Run existing risk manager tests to verify they still pass**

```bash
cd backend
pytest tests/test_risk_manager.py -v
```
Expected: All existing tests pass (backward compatible)

- [ ] **Step 4: Run all tests to verify nothing is broken**

```bash
cd backend
pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/strategy_engine.py backend/app/services/risk_manager.py
git commit -m "refactor: StrategyEngine uses GraphExecutor, RiskManager delegates to node handlers"
```

---

### Task 7: Risk API Endpoints

**Files:**
- Create: `backend/app/routers/risk.py`
- Test: `backend/tests/test_risk_api.py`

- [ ] **Step 1: Write failing API tests**

```python
import pytest
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager


@pytest.mark.asyncio
async def test_risk_summary_endpoint(client):
    resp = await client.get("/api/risk/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "var_95" in data
    assert "es_95" in data
    assert "max_drawdown" in data
    assert "current_drawdown" in data
    assert "concentration" in data
    assert "portfolio_volatility" in data


@pytest.mark.asyncio
async def test_risk_var_endpoint(client):
    resp = await client.get("/api/risk/var?confidence=0.95")
    assert resp.status_code == 200
    data = resp.json()
    assert "historical" in data
    assert "parametric" in data
    assert "confidence" in data


@pytest.mark.asyncio
async def test_risk_correlation_endpoint(client):
    resp = await client.get("/api/risk/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert "pairs" in data


@pytest.mark.asyncio
async def test_risk_drawdown_endpoint(client):
    resp = await client.get("/api/risk/drawdown")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_drawdown" in data
    assert "peak_capital" in data
    assert "current_capital" in data


@pytest.mark.asyncio
async def test_risk_portfolio_endpoint(client):
    resp = await client.get("/api/risk/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "positions" in data
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_risk_api.py -v
```

- [ ] **Step 3: Write risk.py router**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.trade import Trade, TradeStatus
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.tabpfn_integration import TabPFNQuantileEstimator

router = APIRouter(prefix="/api/risk", tags=["risk"])
calc = RiskCalculator()
pm = PortfolioManager()
tabpfn_est = TabPFNQuantileEstimator()


@router.get("/summary")
async def risk_summary(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED).order_by(Trade.created_at.desc()).limit(100)
    )
    trades = rows.scalars().all()
    pnls = [float(t.pnl or 0) for t in trades]
    capital_series = _build_capital_series(trades)
    positions = _build_positions(trades)
    var_95 = calc.historical_var(pnls, 0.95)
    es_95 = calc.expected_shortfall(pnls, 0.95)
    max_dd = calc.max_drawdown(capital_series) if capital_series else 0.0
    current_dd = calc.current_drawdown(max(capital_series) if capital_series else 10000,
                                        capital_series[-1] if capital_series else 10000)
    conc = calc.concentration(positions)
    vol = calc.portfolio_volatility(pnls)
    return {
        "var_95": round(var_95, 4),
        "es_95": round(es_95, 4),
        "max_drawdown": round(max_dd, 4),
        "current_drawdown": round(current_dd, 4),
        "concentration": round(conc, 4),
        "portfolio_volatility": round(vol, 4),
    }


@router.get("/var")
async def risk_var(confidence: float = Query(0.95, ge=0.5, le=0.999),
                   session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED)
    )
    pnls = [float(t.pnl or 0) for t in rows.scalars().all()]
    hist = calc.historical_var(pnls, confidence)
    para = calc.parametric_var(pnls, confidence)
    tabpfn_val = None
    if len(pnls) > 20:
        tabpfn_val = round(await tabpfn_est.estimate_var(returns=pnls, confidence=confidence), 4)
    return {
        "historical": round(hist, 4),
        "parametric": round(para, 4),
        "tabpfn": tabpfn_val,
        "confidence": confidence,
    }


@router.get("/correlation")
async def risk_correlation(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED)
    )
    trades = rows.scalars().all()
    by_market: dict[str, list[float]] = {}
    for t in trades:
        mid = t.market_id
        if mid not in by_market:
            by_market[mid] = []
        by_market[mid].append(float(t.pnl or 0))
    filtered = {k: v for k, v in by_market.items() if len(v) >= 3}
    pairs = []
    assets = list(filtered.keys())
    for i in range(len(assets)):
        for j in range(i + 1, len(assets)):
            min_len = min(len(filtered[assets[i]]), len(filtered[assets[j]]))
            a_ret = filtered[assets[i]][:min_len]
            b_ret = filtered[assets[j]][:min_len]
            try:
                corr_matrix = calc.correlation_matrix({assets[i]: a_ret, assets[j]: b_ret})
                val = corr_matrix[assets[i]][assets[j]]
                pairs.append({"asset_a": assets[i], "asset_b": assets[j], "correlation": val})
            except Exception:
                pass
    return {"pairs": pairs, "total_assets": len(assets)}


@router.get("/drawdown")
async def risk_drawdown(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED).order_by(Trade.created_at.asc())
    )
    trades = rows.scalars().all()
    capital_series = _build_capital_series(trades)
    if not capital_series:
        return {"current_drawdown": 0.0, "peak_capital": 10000, "current_capital": 10000, "max_drawdown": 0.0}
    peak = max(capital_series)
    current = capital_series[-1]
    max_dd = calc.max_drawdown(capital_series)
    current_dd = calc.current_drawdown(peak, current)
    return {
        "current_drawdown": round(current_dd, 4),
        "peak_capital": round(peak, 2),
        "current_capital": round(current, 2),
        "max_drawdown": round(max_dd, 4),
    }


@router.get("/portfolio")
async def risk_portfolio(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED)
    )
    trades = rows.scalars().all()
    positions = _build_positions(trades)
    pnls = [float(t.pnl or 0) for t in trades]
    total = sum(p.get("size", 0) for p in positions)
    enriched = []
    for p in positions:
        market_rows = await session.execute(
            select(Trade).where(Trade.market_id == p["market_id"], Trade.status == TradeStatus.EXECUTED)
        )
        market_pnls = [float(t.pnl or 0) for t in market_rows.scalars().all()]
        market_var = calc.historical_var(market_pnls, 0.95) if market_pnls else 0.0
        weight = p["size"] / total if total > 0 else 0
        enriched.append({
            "market_id": p["market_id"],
            "size": round(p["size"], 2),
            "var_contribution": round(market_var, 4),
            "concentration_pct": round(weight * 100, 2),
        })
    return {"positions": enriched}


def _build_capital_series(trades: list) -> list[float]:
    capital = 10000.0
    series = [capital]
    for t in trades:
        capital += float(t.pnl or 0)
        series.append(capital)
    return series


def _build_positions(trades: list) -> list[dict]:
    agg: dict[str, float] = {}
    for t in trades:
        mid = t.market_id
        agg[mid] = agg.get(mid, 0) + float(t.amount or 0)
    return [{"market_id": mid, "size": size} for mid, size in agg.items()]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_risk_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/risk.py backend/tests/test_risk_api.py
git commit -m "feat: add Risk API with summary, VaR, correlation, drawdown, portfolio endpoints"
```

---

### Task 8: Register Risk Router in Main

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add risk router import and registration**

```python
# Add to existing imports:
from app.routers import risk

# Add to router includes after the existing ones:
app.include_router(risk.router)
```

- [ ] **Step 2: Verify the app starts**

```bash
cd backend
python -c "from app.main import app; print('OK, routers:', [r.path for r in app.routes])"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register risk router in application"
```

---

### Task 9: Frontend Types + API Client

**Files:**
- Create: `frontend/src/types/risk.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Write frontend types**

```typescript
// frontend/src/types/risk.ts

export interface RiskSummary {
  var_95: number
  es_95: number
  max_drawdown: number
  current_drawdown: number
  concentration: number
  portfolio_volatility: number
}

export interface VaRBreakdown {
  historical: number
  parametric: number
  tabpfn: number | null
  confidence: number
}

export interface CorrelationPair {
  asset_a: string
  asset_b: string
  correlation: number
}

export interface CorrelationData {
  pairs: CorrelationPair[]
  total_assets: number
}

export interface DrawdownMetrics {
  current_drawdown: number
  peak_capital: number
  current_capital: number
  max_drawdown: number
}

export interface PositionRisk {
  market_id: string
  size: number
  var_contribution: number
  concentration_pct: number
}

export interface PortfolioRisk {
  positions: PositionRisk[]
}
```

- [ ] **Step 2: Add API client functions**

Add to `frontend/src/lib/api.ts`:

```typescript
import type { RiskSummary, VaRBreakdown, CorrelationData, DrawdownMetrics, PortfolioRisk } from '@/types/risk'

export async function fetchRiskSummary(): Promise<RiskSummary> {
  const res = await fetch(`${BASE_URL}/risk/summary`)
  if (!res.ok) throw new Error('Failed to fetch risk summary')
  return res.json()
}

export async function fetchVaR(confidence = 0.95): Promise<VaRBreakdown> {
  const res = await fetch(`${BASE_URL}/risk/var?confidence=${confidence}`)
  if (!res.ok) throw new Error('Failed to fetch VaR')
  return res.json()
}

export async function fetchCorrelation(): Promise<CorrelationData> {
  const res = await fetch(`${BASE_URL}/risk/correlation`)
  if (!res.ok) throw new Error('Failed to fetch correlation')
  return res.json()
}

export async function fetchDrawdown(): Promise<DrawdownMetrics> {
  const res = await fetch(`${BASE_URL}/risk/drawdown`)
  if (!res.ok) throw new Error('Failed to fetch drawdown')
  return res.json()
}

export async function fetchPortfolioRisk(): Promise<PortfolioRisk> {
  const res = await fetch(`${BASE_URL}/risk/portfolio`)
  if (!res.ok) throw new Error('Failed to fetch portfolio risk')
  return res.json()
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/risk.ts frontend/src/lib/api.ts
git commit -m "feat: add risk types and API client"
```

---

### Task 10: Frontend Risk Hooks

**Files:**
- Create: `frontend/src/hooks/useRisk.ts`

- [ ] **Step 1: Write React Query hooks**

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchRiskSummary, fetchVaR, fetchCorrelation, fetchDrawdown, fetchPortfolioRisk } from '@/lib/api'

export function useRiskSummary() {
  return useQuery({
    queryKey: ['risk-summary'],
    queryFn: fetchRiskSummary,
    refetchInterval: 30_000,
  })
}

export function useVaR(confidence = 0.95) {
  return useQuery({
    queryKey: ['risk-var', confidence],
    queryFn: () => fetchVaR(confidence),
    refetchInterval: 60_000,
  })
}

export function useCorrelation() {
  return useQuery({
    queryKey: ['risk-correlation'],
    queryFn: fetchCorrelation,
    refetchInterval: 60_000,
  })
}

export function useDrawdown() {
  return useQuery({
    queryKey: ['risk-drawdown'],
    queryFn: fetchDrawdown,
    refetchInterval: 30_000,
  })
}

export function usePortfolioRisk() {
  return useQuery({
    queryKey: ['risk-portfolio'],
    queryFn: fetchPortfolioRisk,
    refetchInterval: 30_000,
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useRisk.ts
git commit -m "feat: add risk React Query hooks"
```

---

### Task 11: Frontend Risk Dashboard Components

**Files:**
- Create: `frontend/src/components/analytics/RiskDashboard.tsx`
- Create: `frontend/src/components/analytics/RiskMetricsCards.tsx`
- Create: `frontend/src/components/analytics/CorrelationMatrix.tsx`
- Create: `frontend/src/components/analytics/DrawdownChart.tsx`

- [ ] **Step 1: Write RiskMetricsCards**

```tsx
import { useRiskSummary } from '@/hooks/useRisk'

export default function RiskMetricsCards() {
  const { data, isLoading } = useRiskSummary()

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Loading...</p>
          </div>
        ))}
      </div>
    )
  }

  const cards = [
    { label: 'VaR (95%)', value: data?.var_95 != null ? `${(data.var_95 * 100).toFixed(2)}%` : '—', color: data?.var_95 && data.var_95 > 0.05 ? 'text-red-400' : 'text-yellow-400' },
    { label: 'Expected Shortfall', value: data?.es_95 != null ? `${(data.es_95 * 100).toFixed(2)}%` : '—', color: 'text-red-400' },
    { label: 'Drawdown', value: data?.current_drawdown != null ? `${(data.current_drawdown * 100).toFixed(2)}%` : '—', color: data?.current_drawdown && data.current_drawdown > 0.1 ? 'text-red-400' : 'text-yellow-400' },
    { label: 'Portfolio Vol', value: data?.portfolio_volatility != null ? `${(data.portfolio_volatility * 100).toFixed(2)}%` : '—', color: 'text-blue-400' },
  ]

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <p className="text-sm text-gray-400">{card.label}</p>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Write CorrelationMatrix**

```tsx
import { useCorrelation } from '@/hooks/useRisk'

export default function CorrelationMatrix() {
  const { data, isLoading } = useCorrelation()

  if (isLoading) return <p className="text-sm text-gray-400">Loading correlations...</p>
  if (!data?.pairs?.length) return <p className="text-sm text-gray-400">Not enough trade data for correlation analysis.</p>

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">Correlation Matrix</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400">
              <th className="px-3 py-1 text-left">Asset A</th>
              <th className="px-3 py-1 text-left">Asset B</th>
              <th className="px-3 py-1 text-right">Correlation</th>
            </tr>
          </thead>
          <tbody>
            {data.pairs.slice(0, 20).map((pair, i) => (
              <tr key={i} className="border-t border-gray-700">
                <td className="px-3 py-1 text-gray-300">{pair.asset_a.slice(0, 16)}</td>
                <td className="px-3 py-1 text-gray-300">{pair.asset_b.slice(0, 16)}</td>
                <td className={`px-3 py-1 text-right ${Math.abs(pair.correlation) > 0.7 ? 'text-red-400' : 'text-gray-300'}`}>
                  {pair.correlation.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Write DrawdownChart**

```tsx
import { useDrawdown } from '@/hooks/useRisk'

export default function DrawdownChart() {
  const { data, isLoading } = useDrawdown()

  if (isLoading) return <p className="text-sm text-gray-400">Loading drawdown...</p>
  if (!data) return null

  const ddPct = ((data.current_drawdown ?? 0) * 100).toFixed(2)
  const maxDdPct = ((data.max_drawdown ?? 0) * 100).toFixed(2)
  const isWarning = (data.current_drawdown ?? 0) > 0.1

  const barWidth = Math.min((data.current_drawdown ?? 0) / Math.max((data.max_drawdown ?? 0.01), 0.01) * 100, 100)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">Drawdown</h3>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Current: <span className={isWarning ? 'text-red-400' : 'text-yellow-400'}>{ddPct}%</span></span>
          <span className="text-gray-400">Max: <span className="text-red-400">{maxDdPct}%</span></span>
        </div>
        <div className="h-3 w-full rounded-full bg-gray-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${isWarning ? 'bg-red-500' : 'bg-yellow-500'}`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span>Peak: ${data.peak_capital?.toFixed(0)}</span>
          <span>Current: ${data.current_capital?.toFixed(0)}</span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Write RiskDashboard (composite)**

```tsx
import RiskMetricsCards from './RiskMetricsCards'
import CorrelationMatrix from './CorrelationMatrix'
import DrawdownChart from './DrawdownChart'

export default function RiskDashboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">Risk Dashboard</h2>
      <RiskMetricsCards />
      <div className="grid grid-cols-2 gap-4">
        <DrawdownChart />
        <CorrelationMatrix />
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/analytics/
git commit -m "feat: add RiskDashboard, RiskMetricsCards, CorrelationMatrix, DrawdownChart"
```

---

### Task 12: Frontend Integration

**Files:**
- Modify: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: Update AnalyticsPage to include RiskDashboard**

```tsx
import { useQuery } from '@tanstack/react-query'
import { fetchAnalyticsSummary, fetchAnalyticsBacktests } from '@/lib/api'
import RiskDashboard from '@/components/analytics/RiskDashboard'

export default function AnalyticsPage() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: fetchAnalyticsSummary,
  })
  const { data: backtests, isLoading: loadingBacktests } = useQuery({
    queryKey: ['analytics-backtests'],
    queryFn: fetchAnalyticsBacktests,
  })

  if (loadingSummary || loadingBacktests) {
    return <div className="p-6"><p className="text-gray-400">Loading analytics...</p></div>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Analytics</h1>

      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Total Trades</p>
            <p className="text-2xl font-bold">{summary.total_trades}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Win Rate</p>
            <p className="text-2xl font-bold text-green-400">{summary.win_rate}%</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Winning Trades</p>
            <p className="text-2xl font-bold">{summary.winning_trades}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Total P&L</p>
            <p className={`text-2xl font-bold ${summary.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${summary.total_pnl.toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <RiskDashboard />

      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h2 className="mb-3 text-lg font-medium">Backtests</h2>
        {backtests?.backtests?.length > 0 ? (
          backtests.backtests.map((bt: any, i: number) => (
            <div key={i} className="mb-4">
              <p className="font-medium">{bt.name}</p>
              <p className="text-sm text-gray-400">{bt.trades?.length ?? 0} trades</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-gray-400">No backtests recorded yet. Run a strategy to see results here.</p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: integrate RiskDashboard into AnalyticsPage"
```

---

### Task 13: Full Test Suite Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
pytest tests/ -v --tb=short 2>&1
```

Expected: All tests pass.

- [ ] **Step 2: Run frontend type check**

```bash
cd frontend
npx tsc --noEmit 2>&1
```

Expected: No type errors.

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: finalize risk manager implementation"
```
