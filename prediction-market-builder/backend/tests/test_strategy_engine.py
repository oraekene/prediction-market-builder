import pytest
from app.services.node_executor import ExecutionContext
from app.services.strategy_engine import StrategyEngine, _get_registry


def test_engine_registry_has_performance_handler():
    registry = _get_registry()
    handler = registry.get("performance")
    assert handler is not None


def test_engine_evaluate_runs_performance_node():
    engine = StrategyEngine()
    ctx = ExecutionContext(performance_snapshot={"sharpe": 2.5})
    nodes = [
        {"id": "p1", "type": "performance", "position": {"x": 0, "y": 0}, "data": {"metric": "sharpe"}},
    ]
    result = engine.evaluate(nodes, [], ctx)
    assert result["value"] == 2.5
    assert result["metric"] == "sharpe"


def test_engine_evaluate_with_default_context():
    engine = StrategyEngine()
    nodes = [
        {"id": "p1", "type": "performance", "position": {"x": 0, "y": 0}, "data": {"metric": "sharpe"}},
    ]
    result = engine.evaluate(nodes, [])
    assert "value" in result


def test_engine_evaluate_with_threshold_and_performance():
    engine = StrategyEngine()
    ctx = ExecutionContext(performance_snapshot={"sharpe": 2.5})
    nodes = [
        {"id": "p1", "type": "performance", "position": {"x": 0, "y": 0}, "data": {"metric": "sharpe"}},
        {"id": "t1", "type": "threshold_condition", "position": {"x": 100, "y": 0}, "data": {"field": "current_odds", "operator": "gt", "threshold": 0.5}},
    ]
    edges = [{"id": "e1", "source": "p1", "target": "t1"}]
    result = engine.evaluate(nodes, edges, ctx)
    assert result is not None


@pytest.mark.asyncio
async def test_register_strategy_and_evaluate():
    engine = StrategyEngine()
    engine.register_strategy("strat-a", {"nodes": [], "edges": []})
    result = await engine.evaluate_strategy("strat-a", {})
    assert result is not None


@pytest.mark.asyncio
async def test_evaluate_unknown_strategy_returns_error():
    engine = StrategyEngine()
    result = await engine.evaluate_strategy("nonexistent", {})
    assert "error" in result
