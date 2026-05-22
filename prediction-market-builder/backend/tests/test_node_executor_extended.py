import pytest
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.performance_node_handlers import handle_performance_metric


def test_cycle_detection_returns_error():
    registry = NodeRegistry()
    registry.register("noop", lambda n, i, c: {"result": 1})
    executor = GraphExecutor(registry)
    nodes = [
        {"id": "a", "type": "noop", "position": {"x": 0, "y": 0}, "data": {}},
        {"id": "b", "type": "noop", "position": {"x": 100, "y": 0}, "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b"},
        {"id": "e2", "source": "b", "target": "a"},
    ]
    result = executor.execute(nodes, edges, ExecutionContext())
    assert "error" in result or "Cycle detected" in str(result)


def test_self_loop_detected():
    registry = NodeRegistry()
    registry.register("noop", lambda n, i, c: {"result": 1})
    executor = GraphExecutor(registry)
    nodes = [
        {"id": "a", "type": "noop", "position": {"x": 0, "y": 0}, "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "a"},
    ]
    result = executor.execute(nodes, edges, ExecutionContext())
    assert "Cycle detected" in str(result)


def test_handle_performance_metric_reads_from_context():
    ctx = ExecutionContext(performance_snapshot={"sharpe": 1.5})
    node = {"id": "p1", "type": "performance", "data": {"metric": "sharpe"}}
    result = handle_performance_metric(node, {}, ctx)
    assert result["value"] == 1.5
    assert result["metric"] == "sharpe"


def test_handle_performance_metric_missing_metric_returns_none():
    ctx = ExecutionContext(performance_snapshot={})
    node = {"id": "p2", "type": "performance", "data": {"metric": "sortino"}}
    result = handle_performance_metric(node, {}, ctx)
    assert result["value"] is None
    assert result["metric"] == "sortino"


def test_performance_node_in_executor():
    registry = NodeRegistry()
    registry.register("performance", handle_performance_metric)
    executor = GraphExecutor(registry)
    ctx = ExecutionContext(performance_snapshot={"win_rate": 0.65})
    nodes = [
        {"id": "p1", "type": "performance", "position": {"x": 0, "y": 0}, "data": {"metric": "win_rate"}},
    ]
    result = executor.execute(nodes, [], ctx)
    assert result["value"] == 0.65
    assert result["metric"] == "win_rate"


def test_performance_node_with_empty_snapshot():
    registry = NodeRegistry()
    registry.register("performance", handle_performance_metric)
    executor = GraphExecutor(registry)
    ctx = ExecutionContext(performance_snapshot={})
    nodes = [
        {"id": "p1", "type": "performance", "position": {"x": 0, "y": 0}, "data": {"metric": "sharpe"}},
    ]
    result = executor.execute(nodes, [], ctx)
    assert result["value"] is None
