from unittest.mock import Mock, AsyncMock

import pytest
from fastapi import Request
from starlette.datastructures import URL, Headers

from app.middleware.rate_limit import RateLimitMiddleware


def _make_request(client_host: str = "127.0.0.1", path: str = "/api/test") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "client": (client_host, 12345),
        "server": ("test", 80),
        "scheme": "http",
    }
    req = Request(scope)
    return req


@pytest.mark.asyncio
async def test_rate_limit_allows_normal_traffic():
    app_mock = AsyncMock(return_value="ok")
    middleware = RateLimitMiddleware(app_mock, requests_per_minute=5)

    for _ in range(5):
        req = _make_request()
        resp = await middleware.dispatch(req, app_mock)
        assert resp == "ok"


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess():
    app_mock = AsyncMock(return_value="ok")
    middleware = RateLimitMiddleware(app_mock, requests_per_minute=3)

    for _ in range(3):
        req = _make_request()
        await middleware.dispatch(req, app_mock)

    req = _make_request()
    resp = await middleware.dispatch(req, app_mock)
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_skips_health():
    app_mock = AsyncMock(return_value="ok")
    middleware = RateLimitMiddleware(app_mock, requests_per_minute=1)

    req = _make_request(path="/health")
    resp = await middleware.dispatch(req, app_mock)
    assert resp == "ok"

    req = _make_request(path="/health")
    resp = await middleware.dispatch(req, app_mock)
    assert resp == "ok"


@pytest.mark.asyncio
async def test_rate_limit_per_ip():
    app_mock = AsyncMock(return_value="ok")
    middleware = RateLimitMiddleware(app_mock, requests_per_minute=2)

    req_a1 = _make_request(client_host="10.0.0.1")
    req_a2 = _make_request(client_host="10.0.0.1")
    req_b = _make_request(client_host="10.0.0.2")

    await middleware.dispatch(req_a1, app_mock)
    await middleware.dispatch(req_a2, app_mock)
    await middleware.dispatch(req_b, app_mock)

    resp = await middleware.dispatch(req_a1, app_mock)
    assert resp.status_code == 429

    resp = await middleware.dispatch(req_b, app_mock)
    assert resp == "ok"
