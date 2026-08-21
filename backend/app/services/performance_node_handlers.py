from app.services.node_executor import NodeHandler


def handle_performance_metric(node: dict, inputs: dict, ctx) -> dict:
    data = node.get("data", {})
    metric = data.get("metric", "")
    snapshot = getattr(ctx, "performance_snapshot", {})
    value = snapshot.get(metric)
    return {"value": value, "metric": metric}


PERFORMANCE_HANDLERS: dict[str, NodeHandler] = {
    "performance": handle_performance_metric,
}
