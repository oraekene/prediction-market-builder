import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

active_users = Gauge("active_users", "Currently active users")

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["db", "operation"],
)


def metrics_endpoint():
    return generate_latest(REGISTRY)


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        method = scope.get("method", "GET")
        path = scope.get("path", "/unknown")
        start = time.time()

        async def _send(message):
            if message.get("type") == "http.response.start":
                status = message.get("status", 200)
                http_requests_total.labels(method=method, path=path, status=status).inc()
            await send(message)

        await self.app(scope, receive, _send)
        duration = time.time() - start
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
