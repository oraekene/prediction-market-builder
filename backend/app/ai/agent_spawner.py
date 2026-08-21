from __future__ import annotations

import asyncio
import enum
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

SPAWN_HEARTBEAT_INTERVAL = 15
STALE_CYCLES_IDLE = 15
DEFAULT_MAX_ITERATIONS = 25
MAX_CONCURRENT_CHILDREN = 8


class AgentEvent(str, enum.Enum):
    SPAWNED = "agent.spawned"
    PROGRESS = "agent.progress"
    COMPLETED = "agent.completed"
    FAILED = "agent.failed"
    TIMEOUT = "agent.timeout"
    CANCELLED = "agent.cancelled"


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpawnedAgent:
    def __init__(
        self,
        agent_id: str,
        goal: str,
        context: str | None = None,
        toolsets: list[str] | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        role: str = "leaf",
        parent_session_id: str = "",
    ):
        self.agent_id = agent_id
        self.goal = goal
        self.context = context
        self.toolsets = toolsets or ["file", "web"]
        self.max_iterations = max_iterations
        self.role = role
        self.parent_session_id = parent_session_id
        self.status = AgentStatus.PENDING
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.created_at = time.time()
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self._heartbeat_at = 0.0
        self._iteration_count = 0
        self._events: list[dict[str, Any]] = []
        self._task: asyncio.Task | None = None

    def record_event(self, event_type: AgentEvent, detail: str = "") -> None:
        self._events.append({
            "type": event_type.value,
            "timestamp": time.time(),
            "detail": detail,
        })

    @property
    def duration(self) -> float | None:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_stale(self) -> bool:
        if self.status not in (AgentStatus.RUNNING, AgentStatus.PENDING):
            return False
        elapsed = time.time() - self._heartbeat_at
        stale_seconds = STALE_CYCLES_IDLE * SPAWN_HEARTBEAT_INTERVAL
        return elapsed > stale_seconds


class AgentSpawner:
    def __init__(self, tool_registry=None):
        self._agents: dict[str, SpawnedAgent] = {}
        self._lock = asyncio.Lock()
        self._concurrent_limit = MAX_CONCURRENT_CHILDREN
        self._tool_registry = tool_registry

    async def spawn_agent(
        self,
        goal: str,
        context: str | None = None,
        toolsets: list[str] | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        role: str = "leaf",
        parent_session_id: str = "",
    ) -> SpawnedAgent:
        async with self._lock:
            running = sum(1 for a in self._agents.values() if a.status == AgentStatus.RUNNING)
            if running >= self._concurrent_limit:
                raise RuntimeError(f"Too many concurrent agents ({running} >= {self._concurrent_limit})")

            agent_id = f"sa-{uuid.uuid4().hex[:12]}"
            agent = SpawnedAgent(
                agent_id=agent_id,
                goal=goal,
                context=context,
                toolsets=toolsets,
                max_iterations=max_iterations,
                role=role,
                parent_session_id=parent_session_id,
            )
            self._agents[agent_id] = agent
            agent.record_event(AgentEvent.SPAWNED)

        task = asyncio.create_task(self._run_agent(agent))
        agent._task = task
        return agent

    async def spawn_batch(
        self,
        tasks: list[dict[str, Any]],
        parent_session_id: str = "",
    ) -> list[SpawnedAgent]:
        agents = []
        for task in tasks:
            agent = await self.spawn_agent(
                goal=task.get("goal", ""),
                context=task.get("context"),
                toolsets=task.get("toolsets"),
                max_iterations=task.get("max_iterations", DEFAULT_MAX_ITERATIONS),
                role=task.get("role", "leaf"),
                parent_session_id=parent_session_id,
            )
            agents.append(agent)
        return agents

    async def _run_agent(self, agent: SpawnedAgent) -> None:
        if agent.status != AgentStatus.PENDING:
            return

        async with self._lock:
            agent.status = AgentStatus.RUNNING
            agent.started_at = time.time()
            agent._heartbeat_at = time.time()

        try:
            from app.ai.hermes_sidecar import HermesSidecar

            hermes = HermesSidecar()
            if self._tool_registry is not None:
                hermes.set_tool_registry(self._tool_registry)
            if not hermes.available:
                raise RuntimeError("Hermes not available for sub-agent")

            prompt = f"[Sub-agent: {agent.role}]\nGoal: {agent.goal}"
            if agent.context:
                prompt += f"\nContext: {agent.context}"
            prompt += f"\nToolsets: {', '.join(agent.toolsets)}"
            prompt += "\nYou are a focused sub-agent. Complete your goal and report results."

            for iteration in range(agent.max_iterations):
                agent._iteration_count = iteration + 1
                agent._heartbeat_at = time.time()

                try:
                    result = await asyncio.wait_for(
                        hermes.process_message(prompt, {"user_id": f"agent_{agent.agent_id}"}),
                        timeout=120,
                    )
                    agent.record_event(AgentEvent.PROGRESS, f"Iteration {iteration + 1} completed")
                except asyncio.TimeoutError:
                    agent.record_event(AgentEvent.TIMEOUT, f"Timeout at iteration {iteration + 1}")
                    async with self._lock:
                        agent.status = AgentStatus.TIMEOUT
                        agent.error = "Sub-agent timed out"
                    return

                response = result.get("response", "")
                final_phrases = ["task complete", "goal achieved", "done", "finished"]
                if any(p in response.lower() for p in final_phrases):
                    break

            async with self._lock:
                agent.status = AgentStatus.COMPLETED
                agent.result = result
                agent.completed_at = time.time()
            agent.record_event(AgentEvent.COMPLETED)

        except asyncio.CancelledError:
            async with self._lock:
                agent.status = AgentStatus.CANCELLED
                agent.error = "Cancelled"
                agent.completed_at = time.time()
            agent.record_event(AgentEvent.CANCELLED, "Cancelled")
        except Exception as exc:
            logger.exception("Sub-agent '%s' failed: %s", agent.agent_id, exc)
            async with self._lock:
                agent.status = AgentStatus.FAILED
                agent.error = str(exc)
                agent.completed_at = time.time()
            agent.record_event(AgentEvent.FAILED)

    def get_agent_status(self, agent_id: str) -> dict[str, Any] | None:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        return {
            "agent_id": agent.agent_id,
            "status": agent.status.value,
            "goal": agent.goal,
            "role": agent.role,
            "created_at": agent.created_at,
            "started_at": agent.started_at,
            "completed_at": agent.completed_at,
            "duration": agent.duration,
            "error": agent.error,
            "result": agent.result,
        }

    async def terminate_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent or agent.status not in (AgentStatus.PENDING, AgentStatus.RUNNING):
            return False
        if agent._task is not None and not agent._task.done():
            agent._task.cancel()
        agent.status = AgentStatus.CANCELLED
        agent.completed_at = time.time()
        agent.record_event(AgentEvent.CANCELLED, "Terminated by user")
        return True

    def list_active_agents(self, parent_session_id: str | None = None) -> list[dict[str, Any]]:
        agents = self._agents.values()
        if parent_session_id:
            agents = [a for a in agents if a.parent_session_id == parent_session_id]
        return [
            {
                "agent_id": a.agent_id,
                "status": a.status.value,
                "goal": a.goal[:100],
                "role": a.role,
                "created_at": a.created_at,
            }
            for a in agents
        ]

    def get_agents_by_session(self, session_id: str) -> list[SpawnedAgent]:
        return [a for a in self._agents.values() if a.parent_session_id == session_id]

    async def clean_stale_agents(self) -> list[str]:
        stale = []
        for agent_id, agent in list(self._agents.items()):
            if agent.is_stale:
                stale.append(agent_id)
                await self.terminate_agent(agent_id)
        if stale:
            logger.info("Cleaned %d stale agents: %s", len(stale), stale)
        return stale
