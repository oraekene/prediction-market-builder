import pytest
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext


def make_handler(output):
    def handler(node, inputs, ctx):
        return output
    return handler


@pytest.mark.asyncio
async def test_empty_nodes_returns_safe_default():
    registry = NodeRegistry()
    executor = GraphExecutor(registry)
    result = await executor.execute([], [], ExecutionContext())
    assert result["approved"] is True
    assert result["suggested_size"] == 0.0


@pytest.mark.asyncio
async def test_single_node_dispatches_correct_handler():
    registry = NodeRegistry()
    registry.register("test_node", make_handler({"result": 42}))
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "test_node", "position": {"x": 0, "y": 0}, "data": {}}]
    result = await executor.execute(nodes, [], ExecutionContext())
    assert result == {"result": 42}


@pytest.mark.asyncio
async def test_two_nodes_chain():
    registry = NodeRegistry()
    registry.register("source", lambda n, i, c: {"value": 10})
    registry.register("double", lambda n, i, c: {"value": i.get("s", {}).get("value", 0) * 2})
    executor = GraphExecutor(registry)
    nodes = [
        {"id": "s", "type": "source", "position": {"x": 0, "y": 0}, "data": {}},
        {"id": "d", "type": "double", "position": {"x": 100, "y": 0}, "data": {}},
    ]
    edges = [{"id": "e1", "source": "s", "target": "d"}]
    result = await executor.execute(nodes, edges, ExecutionContext())
    assert result["value"] == 20


@pytest.mark.asyncio
async def test_handler_error_returns_error_dict():
    registry = NodeRegistry()
    def failing(node, inputs, ctx):
        raise ValueError("oops")
    registry.register("failing", failing)
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "failing", "position": {"x": 0, "y": 0}, "data": {}}]
    result = await executor.execute(nodes, [], ExecutionContext())
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_node_type_returns_empty():
    registry = NodeRegistry()
    executor = GraphExecutor(registry)
    nodes = [{"id": "n1", "type": "unknown", "position": {"x": 0, "y": 0}, "data": {}}]
    result = await executor.execute(nodes, [], ExecutionContext())
    assert result is not None


@pytest.mark.asyncio
async def test_passes_context_to_handlers():
    registry = NodeRegistry()
    def capture_ctx(node, inputs, ctx):
        return {"market_odds": ctx.market.get("current_odds")}
    registry.register("reader", capture_ctx)
    executor = GraphExecutor(registry)
    ctx = ExecutionContext(market={"current_odds": 0.65})
    nodes = [{"id": "n1", "type": "reader", "position": {"x": 0, "y": 0}, "data": {}}]
    result = await executor.execute(nodes, [], ctx)
    assert result["market_odds"] == 0.65
