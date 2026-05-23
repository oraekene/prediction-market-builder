# Deployment Pipeline: StrategySpec → Node Graph

## 1. Current Gap

A research iteration produces a KEPT hypothesis (StrategySpec). That StrategySpec contains a complete entry/exit/sizing/risk rule. But the Strategy's `nodes` and `edges` — which produce live signals — are never updated. Research and live execution are two separate universes.

```
RESEARCH                           LIVE
─────────────────────────          ─────────────────────────
StrategySpec {                     Strategy {nodes, edges}
  entry: momentum_breakout           entry: simple_threshold
  exit: trailing_stop                exit: none
  sizing: kelly                      sizing: fixed_fraction
  risk: stop_loss                    risk: none
  score: 1.2 Sharpe                  live_signals: not_based_on_research
}
```

## 2. The Champion/Challenger Model

Each Strategy maintains exactly **one deployed champion** (the StrategySpec that powers live signals) and optionally **N challengers** (KEPT StrategySpecs running in shadow mode).

```
Strategy
  |
  |-- champion_id: str | null
  |     `-- The StrategySpec currently deployed as live node graph
  |
  |-- challengers: [StrategySpec, ...]
  |     `-- KEPT StrategySpecs from research, deployed in shadow
  |         (executed against live data, results logged, no trades)
  |
  `-- retired: [StrategySpec, ...]
        `-- Former champions, archived with performance history
            Available for rollback if regime reverts
```

## 3. Data Model Changes

New fields on `Strategy`:

```python
class Strategy(Base):
    # ... existing fields ...

    # Deployment tracking
    active_strategy_spec_id: str | None = Column(String, nullable=True)
    shadow_spec_ids: list = Column(JSON, default=list)
    deployment_mode: str = Column(String, default="research_only")
    champion_since: datetime | None = Column(DateTime, nullable=True)
    last_promotion_at: datetime | None = Column(DateTime, nullable=True)
    last_rollback_at: datetime | None = Column(DateTime, nullable=True)
```

New table `strategy_specs` (persistent, deployable versions of hypotheses):

```python
class StrategySpecRecord(Base):
    __tablename__ = "strategy_specs"

    id: str = Column(String, primary_key=True, default=uuid4)
    strategy_id: str = Column(String, nullable=False, index=True)
    source_iteration: int = Column(Integer, nullable=True)
    entry: dict = Column(JSON, nullable=False)
    exit: dict = Column(JSON, nullable=True)
    sizing: dict = Column(JSON, nullable=True)
    risk: dict = Column(JSON, nullable=True)

    champion_score: float = Column(Float, default=0.0)
    shadow_score: float = Column(Float, nullable=True)
    shadow_trades: int = Column(Integer, default=0)
    shadow_sharpe: float = Column(Float, nullable=True)
    shadow_win_rate: float = Column(Float, nullable=True)
    shadow_since: datetime | None = Column(DateTime, nullable=True)

    status: str = Column(String, default="challenger")
    promoted_at: datetime | None = Column(DateTime, nullable=True)
    retired_at: datetime | None = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=now)
```

## 4. Pipeline: StrategySpec → Node Graph

When a StrategySpec is promoted to champion, its rules must be translated into the Strategy's `nodes` and `edges`. This is where the **GraphBuilder** (from the bridge design) finds its correct use — not for Monte Carlo backtesting, but for deployment.

```
StrategySpec {entry, exit, sizing, risk}
       |
       v
+-------------------------------------------+
|              GraphBuilder                  |
|                                            |
|  entry  = threshold_condition node         |
|  exit   = trailing_stop node               |
|  sizing = position_sizer node              |
|  risk   = stop_loss node                   |
|                                            |
|  Builds standard topology:                 |
|  source -> entry -> risk -> sizing ->      |
|  exit -> place_bet                         |
+----------------------+--------------------+
                       |
                       v
            {nodes: [...], edges: [...]}
                       |
                       v
            Strategy.nodes = nodes
            Strategy.edges = edges
            Strategy.active_strategy_spec_id = spec.id
```

The `place_bet` node template:

```python
_build_place_bet_node():
    return {
        "id": "place_bet_1",
        "type": "place_bet",
        "params": {
            "side": "yes",
            "max_position_size": 0.1,  # From sizing rule
        }
    }
```

The `threshold_condition` node receives the entry rule:

```python
_build_entry_node(entry: EntryRule):
    return {
        "id": "entry_1",
        "type": "threshold_condition",
        "params": {
            "field": entry.feature,
            "operator": entry.operator,
            "threshold": entry.threshold,
        }
    }
```

If the StrategySpec has an exit rule:

```python
_build_exit_node(exit: ExitRule):
    type_map = {
        "take_profit": "take_profit",
        "trailing_stop": "trailing_stop",
        "time_exit": "time_exit",
    }
    return {
        "id": "exit_1",
        "type": type_map.get(exit.type, "take_profit"),
        "params": {"value": exit.param_value}
    }
```

## 5. Promotion Flow

### 5.1 Auto-Deploy Mode

```
Step 1: Research iteration completes
  -> KEPT StrategySpec produced with composite_score

Step 2: GraphBuilder converts to node graph
  -> {nodes, edges} = GraphBuilder.build(spec)

Step 3: Shadow deploy
  -> spec inserted into strategy_specs with status="challenger"
  -> StrategyEngine evaluates both champion AND challenger against live data
  -> Champion outputs logged as live signals
  -> Challenger outputs logged to strategy_specs.shadow_* fields (no trades)

Step 4: Compare performance
  -> Every N minutes (configurable, default 60), compare:
  -> champion.shadow_sharpe vs challenger.shadow_sharpe
  -> If challenger.sharpe > champion.sharpe x (1 + promotion_margin) for minimum_window hours:
      -> Auto-promote

Step 5: Promote
  -> Strategy.nodes = challenger.nodes
  -> Strategy.edges = challenger.edges
  -> Champion's status = "retired"
  -> Challenger's status = "champion"
  -> Notify user: "Strategy upgraded to new hypothesis (Sharpe improved from X to Y)"
```

### 5.2 Hybrid Mode

Same as auto-deploy through Step 3. Step 4 becomes:

```
Step 4: User decision
  -> Dashboard shows:
    +----------------------------------------------+
    |  Champion (current live)     Challenger #1    |
    |  Sharpe: 0.72                 Sharpe: 0.88    |
    |  Win rate: 58%                Win rate: 62%   |
    |  Trades: 34                   Trades: 28      |
    |  Since: Jan 15                Since: Jan 20   |
    |                                                |
    |       [Promote to champion]  [Dismiss]         |
    +----------------------------------------------+
  -> User clicks "Promote to champion" -> execute Step 5

Step 4b: User dismisses
  -> Challenger stays in shadow (continues evaluation)
  -> Or user can "retire" it explicitly
```

### 5.3 Research-Only Mode

```
Step 1: Research iteration completes
  -> KEPT StrategySpec stored in strategy_specs with status="research_only"
  -> No node graph changes
  -> No shadow deployment
  -> User reviews in research dashboard and manually promotes if desired
```

## 6. Rollback

If a promoted champion underperforms, automatic rollback:

```
Trigger: champion's trailing sharpe < retired champion's sharpe x (1 - rollback_margin)
         AND champion has been active for < minimum_champion_window

Action:
  -> Restore previous champion's node graph
  -> Current champion's status = "retired" with note "auto-rollback"
  -> Previous champion's status = "champion"
  -> Notify user: "Auto-rollback: new hypothesis underperformed expectation"
```

## 7. Shadow Deployment Details

Shadow deployment uses a **paper-only execution path**:

```
StrategyEngine.evaluate_strategy(strategy_id, market_data)
  -> Loads Strategy.nodes (champion) + all challenger specs
  -> Executes champion: produces live signal, stored as Trade or Signal
  -> For each challenger:
      -> GraphBuilder.build() converts StrategySpec -> temp nodes
      -> StrategyEngine.evaluate(temp_nodes, temp_edges, market_data)
      -> Result stored in strategy_specs.shadow_* fields
      -> Result is logged, never executed as a trade
      -> Paper wallet tracks: "would have entered at price X, would have exited at price Y"
```

## 8. Promotion Decision Engine

```python
class PromotionEngine:
    def __init__(self, strategy_id: str):
        self.strategy = load_strategy(strategy_id)

    async def evaluate_challengers(self):
        champion = get_champion(self.strategy)
        challengers = get_challengers(self.strategy)

        for challenger in challengers:
            shadow_stats = await self._compute_shadow_stats(challenger)
            challenger.shadow_sharpe = shadow_stats.sharpe
            challenger.shadow_win_rate = shadow_stats.win_rate
            challenger.shadow_trades = shadow_stats.total_trades

            if self._should_promote(champion, challenger):
                if self.strategy.deployment_mode == "auto_deploy":
                    await self._promote(challenger)
                elif self.strategy.deployment_mode == "hybrid":
                    self._flag_for_user_review(challenger)

    def _should_promote(self, champion, challenger) -> bool:
        margin = 0.05
        min_window_hours = 24
        if challenger.shadow_trades < 10:
            return False
        if challenger.shadow_duration_hours < min_window_hours:
            return False
        if challenger.shadow_sharpe > champion.champion_score * (1 + margin):
            return True
        return False

    def _should_rollback(self, champion) -> bool:
        rollback_margin = 0.1
        min_window_hours = 48
        if champion.champion_duration_hours < min_window_hours:
            return False
        previous = self._get_previous_champion()
        if not previous:
            return False
        if champion.shadow_sharpe < previous.champion_score * (1 - rollback_margin):
            return True
        return False

    async def _promote(self, challenger):
        previous_champion = get_champion(self.strategy)
        if previous_champion:
            previous_champion.status = "retired"
            previous_champion.retired_at = now()

        new_nodes, new_edges = GraphBuilder(self.registry).build(challenger.to_strategy_spec())
        self.strategy.nodes = new_nodes
        self.strategy.edges = new_edges
        challenger.status = "champion"
        challenger.promoted_at = now()
        self.strategy.active_strategy_spec_id = challenger.id
        self.strategy.last_promotion_at = now()

        await db.commit()
        await notify_user(
            f"Strategy '{self.strategy.name}' promoted to new hypothesis. "
            f"Sharpe: {challenger.shadow_sharpe:.2f} (was {previous_champion.champion_score:.2f})"
        )
```

## 9. User Settings API

```python
PATCH /api/strategies/{id}/deployment

Request:
{
    "deployment_mode": "hybrid",
    "promotion_margin": 0.05,
    "min_shadow_hours": 24,
    "min_champion_hours": 48,
    "auto_rollback": True,
    "notify_on_promotion": True,
    "notify_on_candidate": True,
}
```

## 10. Dashboard Views

**Champion view:**
```
+-----------------------------------------------+
|  Active Strategy: Momentum Breakout v3        |
|                                                |
|  Champion StrategySpec (live since Jan 20):   |
|    Entry: Momentum breakout on odds_momentum_3h|
|    Exit: Trailing stop at 2.5%                |
|    Sizing: Kelly fraction at 0.25             |
|    Sharpe: 1.02 . Win rate: 61% . Trades: 142 |
|                                                |
|  [Rollback to previous]                        |
+-----------------------------------------------+
```

**Challengers view:**
```
+-----------------------------------------------+
|  Shadow Candidates                             |
|                                                |
|  +------------+--------+-------+-------+------+|
|  |StrategySpec| Sharpe | Win%  | Trades| Since||
|  +------------+--------+-------+-------+------+|
|  | #4 (v2.1)  | 1.15   | 64%   | 28    | 3d   ||
|  | #3 (mean   | 0.89   | 58%   | 22    | 5d   ||
|  |  reversion)|        |       |       |      ||
|  +------------+--------+-------+-------+------+|
|                                                |
|  [Promote #4]  [Dismiss #3]                    |
+-----------------------------------------------+
```

**History view:**
```
+-----------------------------------------------+
|  Deployment History                            |
|                                                |
|  Jan 20 -> Present  Momentum Breakout v3 (0.88)|
|  Jan 15 -> Jan 20   Mean Reversion v2  (0.72)  |
|  Jan 01 -> Jan 15   Momentum Breakout v1 (0.65)|
|  Dec 20 -> Jan 01   Manual strategy    (0.58)  |
|                                                |
|  [Rollback to "Mean Reversion v2"]             |
+-----------------------------------------------+
```

## 11. Edge Cases

| Situation | Behavior |
|-----------|----------|
| No champion exists yet | First KEPT StrategySpec becomes champion automatically. User gets a notification. |
| All challengers underperform champion | No promotion. Dashboard shows "All challengers below champion threshold." |
| User edits strategy node graph manually | Champion is invalidated. active_strategy_spec_id = null. User is prompted to re-link a champion or run new research. |
| Research is disabled | No change to champion. Status quo preserved. |
| Challenger produces negative Sharpe | Auto-dismissed: "Challenger #3 (mean reversion) produced negative Sharpe. Rejected." |
| Multiple challengers qualify simultaneously | Best-scoring challenger promoted. Others remain in shadow. |

## 12. Summary: Three Deployment Modes

| Aspect | Research Only | Hybrid | Auto-Deploy |
|--------|---------------|--------|-------------|
| Research affects live | Never | On user approval | Automatically |
| Shadow tracking | No | Yes | Yes |
| User involvement | Manual deploy | Review dashboard | Notifications only |
| Rollback | Manual | Manual | Automatic |
| Use case | "I want to understand" | "Improve but stay in control" | "Trust the system to optimize" |
