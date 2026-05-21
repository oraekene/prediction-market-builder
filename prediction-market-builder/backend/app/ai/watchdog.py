from __future__ import annotations

import asyncio
import enum
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30
STALL_THRESHOLD = 300
MAX_SESSION_AGE = 86400
HEARTBEAT_INTERVAL = 15


class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class WatchdogService:
    def __init__(self):
        self._checks: dict[str, Callable[[], bool | dict[str, Any]]] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._session_activity: dict[str, float] = {}
        self._task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._running = False
        self._on_unhealthy: list[Callable[[str, dict[str, Any]], None | dict[str, Any]]] = []
        self._on_recovery: list[Callable[[str], None]] = []
        self._previously_unhealthy: set[str] = set()

    def register_health_check(self, name: str, check_fn: Callable[[], bool | dict[str, Any]]) -> None:
        self._checks[name] = check_fn

    def on_unhealthy(self, handler: Callable[[str, dict[str, Any]], None | dict[str, Any]]) -> None:
        self._on_unhealthy.append(handler)

    def on_recovery(self, handler: Callable[[str], None]) -> None:
        self._on_recovery.append(handler)

    def track_session_activity(self, session_id: str) -> None:
        self._session_activity[session_id] = time.time()

    def untrack_session(self, session_id: str) -> None:
        self._session_activity.pop(session_id, None)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Watchdog started")

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._heartbeat_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        logger.info("Watchdog stopped")

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await self._check_heartbeats()
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Heartbeat check error: %s", exc)
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _check_heartbeats(self) -> None:
        for check_name, check_fn in self._checks.items():
            try:
                result = await asyncio.to_thread(check_fn) if not asyncio.iscoroutinefunction(check_fn) else await check_fn()
                healthy = result.get("healthy", bool(result)) if isinstance(result, dict) else bool(result)
                self._results[check_name] = (
                    {"healthy": healthy}
                    if not isinstance(result, dict)
                    else {**result, "healthy": healthy}
                )

                if not healthy:
                    if check_name not in self._previously_unhealthy:
                        self._previously_unhealthy.add(check_name)
                        logger.warning("Health check '%s' transitioned to UNHEALTHY", check_name)
                        for handler in self._on_unhealthy:
                            try:
                                handler(check_name, self._results[check_name])
                            except Exception as exc:
                                logger.error("Unhealthy handler failed for '%s': %s", check_name, exc)
                else:
                    if check_name in self._previously_unhealthy:
                        self._previously_unhealthy.discard(check_name)
                        logger.info("Health check '%s' RECOVERED", check_name)
                        for handler in self._on_recovery:
                            try:
                                handler(check_name)
                            except Exception as exc:
                                logger.error("Recovery handler failed for '%s': %s", check_name, exc)

            except Exception as exc:
                self._results[check_name] = {"healthy": False, "error": str(exc)}
                if check_name not in self._previously_unhealthy:
                    self._previously_unhealthy.add(check_name)
                    for handler in self._on_unhealthy:
                        try:
                            handler(check_name, self._results[check_name])
                        except Exception:
                            pass

    async def _watch_loop(self) -> None:
        while self._running:
            try:
                await self._run_checks()
                await self._check_sessions()
                await asyncio.sleep(CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog check error: %s", exc)
                await asyncio.sleep(CHECK_INTERVAL)

    async def _run_checks(self) -> None:
        for name, check_fn in self._checks.items():
            try:
                result = await asyncio.to_thread(check_fn) if not asyncio.iscoroutinefunction(check_fn) else await check_fn()
                if isinstance(result, dict):
                    self._results[name] = result
                else:
                    self._results[name] = {"healthy": bool(result)}
            except Exception as exc:
                self._results[name] = {"healthy": False, "error": str(exc)}
                logger.warning("Health check '%s' failed: %s", name, exc)

    async def _check_sessions(self) -> None:
        now = time.time()
        for session_id, last_active in list(self._session_activity.items()):
            elapsed = now - last_active
            if elapsed > STALL_THRESHOLD:
                logger.warning("Session %s stalled (inactive for %ds)", session_id, elapsed)
                self._session_activity[session_id] = now

    def get_health(self) -> dict[str, Any]:
        if not self._results:
            return {"status": HealthStatus.HEALTHY.value, "checks": {}}

        all_healthy = all(r.get("healthy", False) for r in self._results.values())
        any_unhealthy = any(not r.get("healthy", True) for r in self._results.values())

        if all_healthy:
            status = HealthStatus.HEALTHY
        elif any_unhealthy and len(self._results) <= 2:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DEGRADED

        return {
            "status": status.value,
            "checks": dict(self._results),
            "tracked_sessions": len(self._session_activity),
            "uptime_hours": None,
            "previously_unhealthy": list(self._previously_unhealthy),
        }

    def get_session_states(self) -> dict[str, dict[str, Any]]:
        now = time.time()
        return {
            sid: {
                "last_activity": last_active,
                "idle_seconds": round(now - last_active, 1),
                "stalled": (now - last_active) > STALL_THRESHOLD,
            }
            for sid, last_active in self._session_activity.items()
        }
