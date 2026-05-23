# StrategyEngine Bridge: Unifying pi-autoresearch with the Central Node System

## 1. Motivation

pi-autoresearch and the central StrategyEngine operate as completely independent systems with no integration:

```
pi-autoresearch                          StrategyEngine
─────────────────                        ─────────────────
HYPOTHESIS_TEMPLATES (5 entries)         35+ registered node types
{threshold, operator, side}              {nodes: [...], edges: [...]}
Backtester.run() — standalone            GraphExecutor.execute() — DAG pipeline
No awareness of custom nodes             SkillCreator registers custom nodes

NO BRIDGE EXISTS BETWEEN THESE WORLDS
```

This means:
- A custom `threshold_condition` node with a user-defined feature transform is invisible to pi-autoresearch
- A hypothesis discovered by pi-autoresearch ("momentum breakout at threshold 0.6") cannot be deployed as a real Strategy node graph
- The Monte Carlo backtest uses a simplified threshold model, not the full 35-node-type pipeline
- User-created custom nodes via SkillCreator have zero impact on hypothesis generation

## 2. Architecture: The GraphBuilder Component

The bridge is a single new component — the **GraphBuilder** — that converts any `StrategySpec` (from any hypothesis mode) into a real `{nodes, edges}` graph compatible with `StrategyEngine.evaluate()`.

```
StrategySpec {entry, exit, sizing, risk, source}
       │
       ▼
┌─────────────────────────────────────────────┐
│              GraphBuilder                     │
│                                               │
│  StrategySpec → Node Graph Translation:       │
│                                               │
│  entry.threshold_condition  → threshold node  │
│  exit.take_profit           → take_profit node│
│  sizing.kelly               → position_sizer  │
│  risk.stop_loss             → stop_loss node  │
│                                               │
│  Connects nodes in topological order:         │
│  source → entry → risk → sizing → place_bet  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
{nodes: [...], edges: [...]}
                       │
                       ▼
StrategyEngine.evaluate(nodes, edges, context)
                       │
                       ▼
BacktestResult {trades, pnl, win_rate, sharpe}
```

### 2.1 StrategySpec (Already Designed)

From the main design doc (Section 8.5):

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

The GraphBuilder accepts any `StrategySpec` regardless of source and produces a valid node graph.

### 2.2 Standard Node Graph Topology

Every hypothesis translates to this DAG structure:

```
                    ┌──────────────┐
                    │ market_source │  (always present — provides market data)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  toto2_climate│  (optional — provides regime context)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   regim_gate │  (optional — filters by regime)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌─────▼──────┐ ┌───▼────────┐
     │ entry_node │ │ exit_node  │ │ risk_node  │
     │ (required) │ │ (optional) │ │ (optional) │
     └────────┬───┘ └─────┬──────┘ └───┬────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │ position_sizer│  (optional — sizing logic)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  place_bet   │  (always present — action output)
                    └──────────────┘
```

### 2.3 Template-to-Node Mapping

Every template in the 150+ catalog now includes node mapping metadata:

```python
{
    "id": "momentum_breakout_1",
    "template": "Momentum breakout on {feature}",
    "dimension": "entry",
    "level": "entry",
    "params": {
        "feature": {"primary": "odds_momentum_3h", "alternatives": [...]},
        "operator": "gt",
        "threshold_range": (0.55, 0.75),
    },
    # NEW: Node graph mapping
    "node_graph": {
        "node_type": "threshold_condition",      # Registered StrategyEngine node type
        "node_category": "entry",                # entry | exit | sizing | risk | regime
        "param_mapping": {                        # How template params → node config
            "feature": "params.feature",
            "operator": "params.operator",
            "threshold": "params.threshold",
        },
        "position_hint": {                        # Visual canvas placement
            "x": 200, "y": 100,
        },
    },
    # For custom user nodes:
    # "node_graph": {
    #     "node_type": "user_my_custom_indicator",
    #     "node_category": "entry",
    #     "param_mapping": {"feature": "params.featureName", ...},
    # },
}
```

### 2.4 GraphBuilder Implementation

```python
class GraphBuilder:
    def __init__(self, node_registry: NodeRegistry):
        self.registry = node_registry
        self._next_id = 0

    def _node_id(self, prefix: str = "n") -> str:
        self._next_id += 1
        return f"{prefix}_{self._next_id}"

    def build(self, spec: StrategySpec) -> tuple[list[dict], list[dict]]:
        """Convert StrategySpec into {nodes, edges} for StrategyEngine."""
        nodes = []
        edges = []

        # 1. Source node — always present
        src = {
            "id": self._node_id("src"),
            "type": "market_source",
            "params": {"source": "current"},
            "position": {"x": 50, "y": 200},
        }
        nodes.append(src)
        prev_id = src["id"]

        # 2. Regime node — if regime info is relevant
        if spec.entry.regime:
            regime = {
                "id": self._node_id("reg"),
                "type": "toto2_climate",
                "params": {"regime_filter": spec.entry.regime},
                "position": {"x": 200, "y": 50},
            }
            nodes.append(regime)
            edges.append({"from": src["id"], "to": regime["id"]})
            prev_id = regime["id"]

        # 3. Entry node — required
        entry = self._build_entry_node(spec.entry, prev_id)
        nodes.append(entry["node"])
        edges.append({"from": prev_id, "to": entry["node"]["id"]})
        prev_id = entry["node"]["id"]

        # 4. Risk node — optional
        if spec.risk:
            risk = self._build_risk_node(spec.risk, prev_id)
            nodes.append(risk["node"])
            edges.append({"from": prev_id, "to": risk["node"]["id"]})
            prev_id = risk["node"]["id"]

        # 5. Exit node — optional
        if spec.exit:
            exit_node = self._build_exit_node(spec.exit, prev_id)
            nodes.append(exit_node["node"])
            edges.append({"from": prev_id, "to": exit_node["node"]["id"]})
            prev_id = exit_node["node"]["id"]

        # 6. Sizing node — optional
        if spec.sizing:
            sizing = self._build_sizing_node(spec.sizing, prev_id)
            nodes.append(sizing["node"])
            edges.append({"from": prev_id, "to": sizing["node"]["id"]})
            prev_id = sizing["node"]["id"]

        # 7. Place bet node — always present
        bet = {
            "id": self._node_id("bet"),
            "type": "place_bet",
            "params": {"side": "yes"},
            "position": {"x": 800, "y": 200},
        }
        nodes.append(bet)
        edges.append({"from": prev_id, "to": bet["id"]})

        return nodes, edges

    def _build_entry_node(self, entry: EntryRule, prev_id: str) -> dict:
        """Build a threshold_condition node from an entry rule."""
        node = {
            "id": self._node_id("entry"),
            "type": "threshold_condition",
            "params": {
                "feature": entry.feature,
                "operator": entry.operator,
                "threshold": entry.threshold,
            },
            "position": {"x": 400, "y": 200},
        }
        return {"node": node}

    def _build_risk_node(self, risk: RiskRule, prev_id: str) -> dict:
        """Build a risk check node from a risk rule."""
        node_type_map = {
            "stop_loss": "stop_loss",
            "max_drawdown": "drawdown_monitor",
            "var_limit": "var_check",
            "max_positions": "max_positions_check",
        }
        actual_type = node_type_map.get(risk.type, "stop_loss")
        node = {
            "id": self._node_id("risk"),
            "type": actual_type,
            "params": {"limit": risk.limit},
            "position": {"x": 600, "y": 150},
        }
        return {"node": node}

    def _build_exit_node(self, exit: ExitRule, prev_id: str) -> dict:
        """Build a take_profit or trailing_stop node."""
        node_type_map = {
            "take_profit": "take_profit",
            "trailing_stop": "trailing_stop",
            "time_exit": "time_exit",
        }
        actual_type = node_type_map.get(exit.type, "take_profit")
        node = {
            "id": self._node_id("exit"),
            "type": actual_type,
            "params": {"value": exit.param_value},
            "position": {"x": 600, "y": 250},
        }
        return {"node": node}

    def _build_sizing_node(self, sizing: SizingRule, prev_id: str) -> dict:
        """Build a position_sizer node."""
        node = {
            "id": self._node_id("size"),
            "type": "position_sizer",
            "params": {
                "method": sizing.type,
                "value": sizing.value,
            },
            "position": {"x": 700, "y": 200},
        }
        return {"node": node}
```

## 3. Auto-Discovery of Custom Nodes

### 3.1 Current State

When a user creates a custom skill via HermesOrchestrator/SkillCreator:
1. The node handler is registered in `NodeRegistry` ✓
2. The skill becomes available in the orchestrator's skill list ✓
3. **pi-autoresearch has no awareness of it** ✗

### 3.2 CustomNodeTemplate Model

New model to bridge custom skills into the hypothesis template pool:

```python
class CustomNodeTemplate(Base):
    __tablename__ = "custom_node_templates"

    id: str = Column(String, primary_key=True, default=uuid4)
    skill_id: str = Column(String, nullable=False, index=True)  # FK to skill/orch record
    user_id: str = Column(String, nullable=False, index=True)
    node_type: str = Column(String, nullable=False)  # e.g. "user_my_custom_indicator"
    template_description: str = Column(String, nullable=False)
    default_params: dict = Column(JSON, default={})
    param_schema: dict = Column(JSON, default={})  # JSON Schema for the node's params
    regime_affinity: list = Column(JSON, default=["all"])
    is_active: bool = Column(Boolean, default=True)
    created_at: DateTime = Column(DateTime, default=now)
```

### 3.3 Auto-Creation Hook

When `SkillCreator.create_skill()` successfully registers a custom node, a hook fires:

```python
async def _on_skill_created(self, skill_record: dict, node_type: str) -> None:
    """Create a CustomNodeTemplate entry so pi-autoresearch discovers this skill."""
    template = CustomNodeTemplate(
        skill_id=skill_record["id"],
        user_id=skill_record["user_id"],
        node_type=node_type,
        template_description=f"Custom: {skill_record.get('name', node_type)} on {{feature}}",
        default_params=skill_record.get("default_params", {}),
        param_schema=skill_record.get("param_schema", {}),
        regime_affinity=skill_record.get("regime_affinity", ["all"]),
    )
    db.add(template)
    await db.commit()
```

### 3.4 Template Pool Discovery

The template pool that feeds `_generate_hypotheses()` now queries **two sources**:

```python
async def _get_available_templates(self, user_id: str) -> list[dict]:
    """Get all available templates including user's custom node templates."""
    built_in = list(HYPOTHESIS_TEMPLATES)

    custom = await db.execute(
        select(CustomNodeTemplate).where(
            CustomNodeTemplate.user_id == user_id,
            CustomNodeTemplate.is_active == True,
        )
    )

    for ct in custom.scalars():
        built_in.append({
            "id": f"custom_{ct.id}",
            "template": ct.template_description,
            "dimension": "entry",
            "params": {
                "feature": {"primary": "custom", "alternatives": []},
                "operator": "gt",
                "threshold_range": (0.4, 0.7),
            },
            "regime_affinity": ct.regime_affinity,
            "node_graph": {
                "node_type": ct.node_type,
                "node_category": "entry",
                "param_mapping": {},
            },
            "tags": ["custom", ct.node_type],
        })

    return built_in
```

### 3.5 Scope of Custom Node Visibility

| Scope | User sees | Others see | Marketplace potential |
|-------|-----------|------------|----------------------|
| Private (default) | Own custom nodes | Nothing | No |
| Public | Own custom nodes | Can see, can clone | Yes — sell on marketplace |
| Template (no params) | Own custom nodes | Can use as black box | Yes — usage-based pricing |

## 4. Monte Carlo Backtest via StrategyEngine

### 4.1 Current Flow (Simple Backtester)

```python
async def monte_carlo_backtest(backtest_config, market_history, n=50):
    backtester = Backtester()
    sharpes, win_rates, pnls = [], [], []
    for _ in range(n):
        bootstrapped = _bootstrap(market_history)
        result = await backtester.run(backtest_config, bootstrapped)
        sharpes.append(_sharpe_from_backtest(result))
        win_rates.append(result.win_rate)
        pnls.append(result.total_pnl)
    return aggregate(sharpes, win_rates, pnls)
```

### 4.2 New Flow (StrategyEngine Backtest)

```python
async def monte_carlo_backtest_via_engine(
    strategy_spec: StrategySpec,
    market_history: list[dict],
    n: int = 50,
    graph_builder: GraphBuilder | None = None,
    strategy_engine: StrategyEngine | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation using StrategyEngine with real node graphs."""
    graph_builder = graph_builder or GraphBuilder(NodeRegistry.default())
    nodes, edges = graph_builder.build(strategy_spec)
    strategy_engine = strategy_engine or StrategyEngine(NodeRegistry.default())

    sharpes, win_rates, pnls = [], [], []

    for i in range(n):
        bootstrapped = _bootstrap_market_history(market_history)
        context = ExecutionContext(
            market_data=bootstrapped,
            signal_data={},
            portfolio_data={},
            risk_calculator=RiskCalculator(),
            portfolio_manager=PortfolioManager(),
            tabpfn=TabPFNService(),
        )
        result = await strategy_engine.evaluate(nodes, edges, context)
        trades = _extract_trades_from_engine_result(result)
        sharpes.append(_sharpe_from_trades(trades))
        win_rates.append(_win_rate_from_trades(trades))
        pnls.append(_pnl_from_trades(trades))

    return aggregate(sharpes, win_rates, pnls)
```

### 4.3 Performance & Caching

The node graph is built once per hypothesis and cached across all 50 bootstrap runs.

| Step | Current | After Bridge |
|------|---------|--------------|
| Build graph | N/A (no graph) | ~2ms (cached per hypothesis) |
| Execute simulation | ~1ms | ~3-5ms |
| Monte Carlo ×50 | ~50ms | ~150-250ms |
| **Total per hypothesis** | **~50ms** | **~150-250ms** |

Mitigations: `functools.lru_cache` on `graph_builder.build()`; parallel bootstrap via `asyncio.gather()`.

### 4.4 Backward Compatibility

Feature flag on `ResearchSessionConfig`:

```python
use_strategy_engine: bool = False  # Opt-in during migration
```

When `False`: old `Backtester.run()` path. When `True`: new `StrategyEngine.evaluate()` path with GraphBuilder.

## 5. Custom User Nodes in the Three Modes

| Mode | Custom Node Behavior |
|------|---------------------|
| `CONSTRAINED_ALL` | Custom nodes appear in template pool. Regime pre-filter applies. GP evolves custom node params. |
| `CONSTRAINED_SELECTED` | Custom nodes appear in selection UI tagged as "custom" with creator attribution. |
| `UNCONSTRAINED` | LLM receives the custom node's param_schema. Can generate strategies using the custom node. |

## 6. Marketplace Implications

| Artifact | Bridge Enables | Marketplace Potential |
|----------|---------------|----------------------|
| Custom node (SkillCreator) | Auto-discovers as template | Sell as black-box template |
| Strategy (node graph) | Hypothesis → deployable strategy | Sell full node graphs |
| Template (hypothesis pattern) | Experiment results + node graph verified | Sell proven template with stats |
| Meta-strategy | Pool management + node graph integration | Sell as complete trading system |

## 7. Integration Points Summary

| Integration Point | Status | After Bridge |
|-------------------|--------|--------------|
| `autoresearch.py` imports StrategyEngine | No reference | Imports GraphBuilder, passes to monte_carlo |
| `monte_carlo.py` uses GraphBuilder | No reference | Imports GraphBuilder, builds nodes, calls StrategyEngine |
| Custom nodes visible to pi-autoresearch | Invisible | Queries CustomNodeTemplate table |
| SkillCreator registers custom templates | Nothing | Hook auto-creates CustomNodeTemplate entry |
| GraphBuilder builds valid node graphs | Doesn't exist | New component, uses NodeRegistry for validation |
| Backward compatibility | N/A | Feature flag: `use_strategy_engine: bool` |

## 8. Implementation Plan

### Phase 1: Foundation (Estimated: 2-3 sessions)

1. Create `GraphBuilder` class (`backend/app/services/graph_builder.py`)
2. Implement `StrategySpec → {nodes, edges}` translation for entry/exit/sizing/risk
3. Add `node_graph` mapping metadata to all 150+ `HYPOTHESIS_TEMPLATES` entries
4. Unit tests: verify every template dimension produces valid node graphs

### Phase 2: Custom Node Auto-Discovery (Estimated: 2 sessions)

1. Create `CustomNodeTemplate` model + migration
2. Add auto-creation hook in `SkillCreator.create_skill()`
3. Update template pool query to include custom node templates
4. Unit tests: custom nodes appear in hypothesis generation

### Phase 3: Monte Carlo Rewrite (Estimated: 3-4 sessions)

1. Create `monte_carlo_backtest_via_engine()` function
2. Add node graph caching (lru_cache on graph_builder.build)
3. Add parallel bootstrap execution (asyncio.gather)
4. Add `use_strategy_engine` feature flag to `ResearchSessionConfig`
5. Wire the new path in `AutoresearchService.run_iteration()`
6. Add backward compatibility path
7. Integration tests: Monte Carlo via StrategyEngine matches old Backtester results

### Phase 4: Marketplace Wiring (Estimated: 2-3 sessions)

1. Add `is_public`, `price`, `creator_id` fields to `CustomNodeTemplate`
2. Add clone endpoint for custom node templates
3. Add clone endpoint for strategies (clone + reassign user_id)
4. Add `POST /api/templates/{id}/clone-to-custom`
5. Add compliance checks: node type exists, params valid, no malicious code
