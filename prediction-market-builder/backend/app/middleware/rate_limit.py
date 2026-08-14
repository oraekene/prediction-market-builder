import hashlib
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_MAX_ENTRIES = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter, keyed per user (bearer token) or per IP.

    In-memory by design (single-process deployment); entries are pruned
    periodically to bound memory.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_prune = time.monotonic()

    def _key(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
            return f"user:{token_hash}"
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _prune_if_needed(self, now: float) -> None:
        if now - self._last_prune < 60 or len(self._requests) < _MAX_ENTRIES:
            return
        self._last_prune = now
        stale = [k for k, v in self._requests.items() if not v or now - v[-1] > 120]
        for k in stale:
            self._requests.pop(k, None)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health",):
            return await call_next(request)

        key = self._key(request)
        now = time.monotonic()
        window = 60.0

        bucket = self._requests[key]
        self._requests[key] = [t for t in bucket if now - t < window]

        if len(self._requests[key]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        self._requests[key].append(now)
        self._prune_if_needed(now)
        return await call_next(request)
