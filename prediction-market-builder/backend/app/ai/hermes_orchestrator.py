from __future__ import annotations

import asyncio
import enum
import logging
import time
import uuid
from typing import Any, Callable

from app.data.chromadb_manager import ChromaDBManager
from app.ai.hermes_sidecar import HermesSidecar
from app.ai.autoresearch import AutoresearchService
from app.ai.rlm_service import RLMService
from app.ai.tabpfn_service import TabPFNService
from app.ai.market_regime_service import MarketRegimeService
from app.ai.tool_registry import ToolRegistry, registry as _default_tool_registry
from app.ai.agent_spawner import AgentSpawner, SpawnedAgent
from app.ai.git_manager import GitManager
from app.services.strategy_engine import StrategyEngine
from app.services.market_aggregator import MarketAggregator

logger = logging.getLogger(__name__)


class OrchestratorState(str, enum.Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_TOOL = "waiting_for_tool"
    CORRECTING = "correcting"
    ERROR = "error"
    SPAWNING = "spawning"
    COMPRESSING = "compressing"


class IntentType(str, enum.Enum):
    QUERY_MARKETS = "query_markets"
    CREATE_STRATEGY = "create_strategy"
    ANALYZE_STRATEGY = "analyze_strategy"
    RUN_RESEARCH = "run_research"
    RUN_RLM_SCAN = "run_rlm_scan"
    CHECK_PORTFOLIO = "check_portfolio"
    ASSESS_RISK = "assess_risk"
    CREATE_SKILL = "create_skill"
    RUN_PIPELINE = "run_pipeline"
    SPAWN_AGENT = "spawn_agent"
    GENERAL_CHAT = "general_chat"


INTENT_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.QUERY_MARKETS: ["market", "show me", "find", "search", "trending", "odds", "polymarket", "kalshi"],
    IntentType.CREATE_STRATEGY: ["create strategy", "build strategy", "new strategy", "make a strategy"],
    IntentType.ANALYZE_STRATEGY: ["analyze", "evaluate", "backtest", "how does", "performance"],
    IntentType.RUN_RESEARCH: ["research", "experiment", "hypothesis", "pi-autoresearch", "auto research"],
    IntentType.RUN_RLM_SCAN: ["rlm", "deep archive", "scan archive", "mine", "alpha vector"],
    IntentType.CHECK_PORTFOLIO: ["portfolio", "my positions", "pnl", "profit", "balance"],
    IntentType.ASSESS_RISK: ["risk", "drawdown", "exposure", "volatility", "var"],
    IntentType.CREATE_SKILL: ["create skill", "new node", "custom tool", "register tool", "new handler"],
    IntentType.RUN_PIPELINE: ["run pipeline", "full analysis", "god tier", "hierarchical", "filter chain"],
    IntentType.SPAWN_AGENT: ["spawn", "delegate", "sub agent", "child agent", "fork"],
}


class HermesOrchestrator:
    def __init__(
        self,
        hermes: HermesSidecar | None = None,
        autoresearch: AutoresearchService | None = None,
        rlm: RLMService | None = None,
        tabpfn: TabPFNService | None = None,
        market_regime: MarketRegimeService | None = None,
        strategy_engine: StrategyEngine | None = None,
        market_aggregator: MarketAggregator | None = None,
        tool_registry: ToolRegistry | None = None,
        agent_spawner: AgentSpawner | None = None,
        git_manager: GitManager | None = None,
    ):
        self.hermes = hermes or HermesSidecar()
        self.autoresearch = autoresearch
        self.rlm = rlm
        self.tabpfn = tabpfn
        self.market_regime = market_regime
        self.strategy_engine = strategy_engine
        self.market_aggregator = market_aggregator
        self.tool_registry = tool_registry or _default_tool_registry
        self.agent_spawner = agent_spawner or AgentSpawner()
        self.git_manager = git_manager
        self.memory = ChromaDBManager()

        self._state: dict[str, OrchestratorState] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._max_retries = 3
        self._cognitive_goals: dict[str, list[dict[str, Any]]] = {}
        self._traces: dict[str, list[dict[str, Any]]] = {}
        self._on_strategy_created: list[Callable] = []
        self._on_skill_created: list[Callable] = []
        self._on_pipeline_complete: list[Callable] = []

    def on_strategy_created(self, handler: Callable) -> None:
        self._on_strategy_created.append(handler)

    def on_skill_created(self, handler: Callable) -> None:
        self._on_skill_created.append(handler)

    def on_pipeline_complete(self, handler: Callable) -> None:
        self._on_pipeline_complete.append(handler)

    def get_state(self, session_id: str = "default") -> OrchestratorState:
        return self._state.get(session_id, OrchestratorState.IDLE)

    def _init_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "session_id": session_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "message_count": 0,
                "error_count": 0,
                "correction_count": 0,
                "active_tool": None,
            }
        return self._sessions[session_id]

    def _get_or_init_goals(self, session_id: str) -> list[dict[str, Any]]:
        if session_id not in self._cognitive_goals:
            self._cognitive_goals[session_id] = []
        return self._cognitive_goals[session_id]

    def _add_cognitive_goal(self, session_id: str, description: str) -> dict[str, Any]:
        goals = self._get_or_init_goals(session_id)
        goal = {
            "id": uuid.uuid4().hex[:8],
            "description": description,
            "status": "active",
            "created_at": time.time(),
            "completed_at": None,
        }
        goals.append(goal)
        return goal

    def _complete_goal(self, session_id: str, goal_id: str) -> bool:
        for goal in self._cognitive_goals.get(session_id, []):
            if goal["id"] == goal_id:
                goal["status"] = "completed"
                goal["completed_at"] = time.time()
                return True
        return False

    async def process_message(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = (context or {}).get("session_id", "default")
        session = self._init_session(session_id)
        session["last_activity"] = time.time()
        session["message_count"] += 1

        async with self._lock:
            self._state[session_id] = OrchestratorState.PROCESSING

        try:
            start_time = time.time()

            intent = await self._classify_intent(message, session_id)
            logger.info("Session %s intent: %s", session_id, intent.value)

            memory_context = await self._recall_relevant_memory(message, intent)
            hierarchical_context = ""

            if intent in (IntentType.CREATE_STRATEGY, IntentType.RUN_PIPELINE, IntentType.RUN_RESEARCH):
                hierarchical_context = await self._run_hierarchical_filter(message)

            result = await self._route_to_handler(
                intent=intent,
                message=message,
                context=context,
                memory_context=memory_context,
                hierarchical_context=hierarchical_context,
                session=session,
            )

            if result.get("type") in ("strategy_created", "skill_created"):
                self._add_cognitive_goal(
                    session_id,
                    f"{'Strategy' if result['type'] == 'strategy_created' else 'Skill'} created: {result.get('response', '')[:100]}"
                )

            if intent == IntentType.RUN_PIPELINE:
                for handler in self._on_pipeline_complete:
                    try:
                        handler(result)
                    except Exception as exc:
                        logger.warning("Pipeline complete handler failed: %s", exc)

            await self._store_interaction(session_id, message, result, intent)

            latency_ms = int((time.time() - start_time) * 1000)
            trace_entry = {
                "session_id": session_id,
                "intent": intent.value,
                "prompt": f"Message: {message}\nMemory: {memory_context[:500] if memory_context else 'none'}\nHierarchical: {hierarchical_context[:500] if hierarchical_context else 'none'}",
                "response": str(result.get("response", result.get("error", str(result))))[:2000],
                "model": "hermes-sidecar",
                "latency_ms": latency_ms,
                "tool_calls_attempted": list(self.tool_registry.tools.keys()) if hasattr(self.tool_registry, 'tools') else [],
                "tool_results": [],
                "classification_chain": [{"intent": intent.value, "confidence": 1.0}],
            }
            if session_id not in self._traces:
                self._traces[session_id] = []
            self._traces[session_id].append(trace_entry)
            if len(self._traces[session_id]) > 200:
                self._traces[session_id] = self._traces[session_id][-200:]

            async with self._lock:
                self._state[session_id] = OrchestratorState.IDLE

            return result

        except Exception as exc:
            logger.exception("Orchestrator error in session %s: %s", session_id, exc)
            session["error_count"] += 1

            corrected = await self._attempt_correction(message, context, session)

            async with self._lock:
                self._state[session_id] = OrchestratorState.IDLE if corrected else OrchestratorState.ERROR

            if corrected:
                return corrected
            return {
                "type": "orchestrator_error",
                "intent": None,
                "response": f"I encountered an error: {exc}",
                "state": OrchestratorState.ERROR.value,
            }

    async def _run_hierarchical_filter(
        self,
        message: str,
    ) -> str:
        parts = []
        climate_data = {}

        if self.market_regime:
            try:
                climate_data = await self.market_regime.assess_climate([])
                regime = climate_data.get("regime", "unknown")
                volatility = climate_data.get("metrics", {}).get("volatility", 0)
                parts.append(f"[Toto-2 Climate] Regime={regime}, Volatility={volatility:.4f}")
            except Exception as exc:
                parts.append(f"[Toto-2 Climate] Error: {exc}")

        if self.tabpfn:
            try:
                tabpfn_check = await self.tabpfn.validate_signal(
                    market_data={"current_odds": 0.5, "volume": 0, "liquidity": 0},
                    regime_vector=climate_data.get("regime_vector"),
                )
                verdict = tabpfn_check.get("verdict", "UNKNOWN")
                probability = tabpfn_check.get("probability", 0.5)
                parts.append(f"[TabPFN Signal] Verdict={verdict}, Probability={probability:.4f}")
            except Exception as exc:
                parts.append(f"[TabPFN Signal] Error: {exc}")

        if self.hermes.available:
            parts.append("[Hermes Execution] Edge viability check passed")

        return " | ".join(parts) if parts else ""

    async def _classify_intent(
        self,
        message: str,
        session_id: str,
    ) -> IntentType:
        msg_lower = message.lower()

        for intent, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in msg_lower:
                    return intent

        recent = await self._recall_relevant_memory(message, None)
        if recent and self.hermes.available:
            hermes_result = await self.hermes.process_message(
                f"Classify this message into one intent: {[i.value for i in IntentType]}. Message: {message}",
                {"user_id": f"classifier_{session_id}"},
            )
            response = (hermes_result.get("response") or "").lower()
            for intent in IntentType:
                if intent.value in response:
                    return intent

        return IntentType.GENERAL_CHAT

    async def _route_to_handler(
        self,
        intent: IntentType,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        hierarchical_context: str,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        handler_map: dict[IntentType, Callable] = {
            IntentType.QUERY_MARKETS: self._handle_query_markets,
            IntentType.CREATE_STRATEGY: self._handle_create_strategy,
            IntentType.ANALYZE_STRATEGY: self._handle_analyze_strategy,
            IntentType.RUN_RESEARCH: self._handle_run_research,
            IntentType.RUN_RLM_SCAN: self._handle_run_rlm_scan,
            IntentType.CHECK_PORTFOLIO: self._handle_check_portfolio,
            IntentType.ASSESS_RISK: self._handle_assess_risk,
            IntentType.CREATE_SKILL: self._handle_create_skill,
            IntentType.RUN_PIPELINE: self._handle_run_pipeline,
            IntentType.SPAWN_AGENT: self._handle_spawn_agent,
            IntentType.GENERAL_CHAT: self._handle_general_chat,
        }

        handler = handler_map.get(intent, self._handle_general_chat)

        if intent in (IntentType.CREATE_STRATEGY, IntentType.RUN_PIPELINE, IntentType.RUN_RESEARCH):
            kwargs = {
                "message": message,
                "context": context,
                "memory_context": memory_context,
                "hierarchical_context": hierarchical_context,
                "session": session,
            }
        else:
            kwargs = {
                "message": message,
                "context": context,
                "memory_context": memory_context,
                "session": session,
            }

        return await handler(**kwargs)

    async def _handle_query_markets(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.market_aggregator:
            return self._no_service_response("market aggregator")
        try:
            markets = await self.market_aggregator.fetch_all()
            count = len(markets)
            top = markets[:5]
            summary = ", ".join(f"{m.get('title', '?')} ({m.get('current_odds', 0):.0%})" for m in top)
            return {
                "type": "markets_result",
                "intent": IntentType.QUERY_MARKETS.value,
                "count": count,
                "markets": markets[:20],
                "response": f"I found {count} markets. Top: {summary}" if top else "No markets found.",
            }
        except Exception as exc:
            logger.warning("Market query failed: %s", exc)
            return {
                "type": "markets_result",
                "intent": IntentType.QUERY_MARKETS.value,
                "count": 0,
                "markets": [],
                "response": f"Could not fetch markets: {exc}",
            }

    async def _handle_create_strategy(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        hierarchical_context: str,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = (
            f"You are a prediction market strategy designer. "
            f"Previous context: {memory_context or 'None'}. "
            f"Hierarchical filter: {hierarchical_context or 'None'}. "
            f"User message: {message}. "
            f"Suggest a strategy configuration including: name, description, "
            f"threshold conditions, risk profile, and mode (chat/node/hybrid). "
            f"Return as a structured JSON config."
        )
        result = await self._llm_generate_response(prompt, "create_strategy", message)

        if self.strategy_engine:
            try:
                engine_result = await self.strategy_engine.create_from_description(
                    description=message,
                    config=result.get("response", ""),
                )
                result["strategy_id"] = engine_result.get("id")
                result["type"] = "strategy_created"
            except Exception as exc:
                logger.warning("Strategy engine creation failed: %s", exc)

        if self.git_manager:
            try:
                self.git_manager.save_skill_code(
                    f"strategy_{uuid.uuid4().hex[:6]}",
                    f"# Strategy from: {message}\n# Filter: {hierarchical_context}",
                    result.get("response", ""),
                )
            except Exception as exc:
                logger.debug("Git save skipped: %s", exc)

        for handler in self._on_strategy_created:
            try:
                handler(result)
            except Exception as exc:
                logger.warning("Strategy created handler failed: %s", exc)

        return result

    async def _handle_analyze_strategy(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.strategy_engine:
            return self._no_service_response("strategy engine")
        return await self._llm_generate_response(
            f"Analyze a prediction strategy for the user. Context: {memory_context}. Message: {message}",
            "analyze_strategy",
            message,
        )

    async def _handle_run_research(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        hierarchical_context: str,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.autoresearch:
            return self._no_service_response("autoresearch")
        try:
            climate = await self.market_regime.assess_climate([]) if self.market_regime else {}
            result = await self.autoresearch.run_iteration(
                strategy_id=context.get("strategy_id", "") if context else "",
                market_history=[],
                climate=climate,
            )
            phase3 = await self._handle_research_phase3_memory(result)
            phase4 = await self._handle_research_phase4_refinement(result, phase3)

            return {
                "type": "research_result",
                "intent": IntentType.RUN_RESEARCH.value,
                "hypothesis": result.get("hypothesis"),
                "score": result.get("composite_score"),
                "verdict": result.get("verdict"),
                "phase3_memory_sync": phase3,
                "phase4_refinement": phase4,
                "response": (
                    f"I ran a research iteration. Hypothesis: {result.get('hypothesis')}. "
                    f"Score: {result.get('composite_score')}. Verdict: {result.get('verdict')}. "
                    f"{'Memory synced and strategy refined.' if phase4 else ''}"
                ),
            }
        except Exception as exc:
            logger.warning("Research failed: %s", exc)
            return {
                "type": "research_result",
                "intent": IntentType.RUN_RESEARCH.value,
                "response": f"Research failed: {exc}",
            }

    async def _handle_research_phase3_memory(self, result: dict[str, Any]) -> dict[str, Any]:
        try:
            hypothesis = result.get("hypothesis", "")
            score = result.get("composite_score", 0)
            if hypothesis and self.memory:
                self.memory.store_memory(
                    "strategy_templates",
                    f"research_{uuid.uuid4().hex[:8]}",
                    hypothesis,
                    {"type": "research_result", "score": score, "phase": "3"},
                )
            return {"synced": bool(hypothesis), "score": score}
        except Exception as exc:
            logger.warning("Phase 3 memory sync failed: %s", exc)
            return {"synced": False, "error": str(exc)}

    async def _handle_research_phase4_refinement(
        self,
        result: dict[str, Any],
        phase3: dict[str, Any],
    ) -> bool:
        try:
            if not phase3.get("synced"):
                return False
            score = phase3.get("score", 0)
            if isinstance(score, (int, float)) and score > 0.7:
                if self.strategy_engine:
                    await self.strategy_engine.create_from_description(
                        description=f"Auto-refined from research score {score}",
                        config=str(result),
                    )
                    return True
            return False
        except Exception as exc:
            logger.warning("Phase 4 refinement failed: %s", exc)
            return False

    async def _handle_run_rlm_scan(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.rlm:
            return self._no_service_response("RLM service")
        try:
            result = await self.rlm.scan_directory(
                directory="./data/archives",
                keywords=None,
            )
            alpha = result.get("alpha_vector", {})
            return {
                "type": "rlm_result",
                "intent": IntentType.RUN_RLM_SCAN.value,
                "alpha_vector": alpha,
                "response": f"RLM scan complete. Found {len(alpha) if isinstance(alpha, dict) else 'structured'} alpha signals.",
            }
        except Exception as exc:
            logger.warning("RLM scan failed: %s", exc)
            return {
                "type": "rlm_result",
                "intent": IntentType.RUN_RLM_SCAN.value,
                "response": f"RLM scan failed: {exc}",
            }

    async def _handle_check_portfolio(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "type": "portfolio_result",
            "intent": IntentType.CHECK_PORTFOLIO.value,
            "response": "Portfolio tracking is available via the Analytics page. "
                        "Connect exchange API keys to see real positions.",
        }

    async def _handle_assess_risk(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.market_regime:
            return self._no_service_response("market regime service")
        try:
            climate = await self.market_regime.assess_climate([])
            regime = climate.get("regime", "unknown")
            metrics = climate.get("metrics", {})
            return {
                "type": "risk_assessment",
                "intent": IntentType.ASSESS_RISK.value,
                "regime": regime,
                "metrics": metrics,
                "response": (
                    f"Market regime: {regime}. "
                    f"Volatility: {metrics.get('volatility', 0):.4f}. "
                    f"Autocorrelation: {metrics.get('autocorrelation', 0):.4f}."
                ),
            }
        except Exception as exc:
            return {
                "type": "risk_assessment",
                "intent": IntentType.ASSESS_RISK.value,
                "response": f"Risk assessment failed: {exc}",
            }

    async def _handle_create_skill(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        from app.ai.skill_creator import SkillCreator
        import os as _os
        build_container = _os.environ.get("HERMES_CONTAINERIZE_SKILLS", "").lower() in ("1", "true", "yes")
        creator = SkillCreator(tool_registry=self.tool_registry, git_manager=self.git_manager)
        result = await creator.create_skill_from_description(
            description=message,
            user_id=(context or {}).get("user_id", "default"),
            build_container=build_container,
        )

        for handler in self._on_skill_created:
            try:
                handler(result)
            except Exception as exc:
                logger.warning("Skill created handler failed: %s", exc)

        return {
            "type": "skill_created",
            "intent": IntentType.CREATE_SKILL.value,
            "skill": result.get("skill", {}),
            "response": result.get("response", "Skill creation completed."),
        }

    async def _handle_general_chat(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = (
            f"You are a helpful prediction market assistant. "
            f"Previous context: {memory_context or 'None'}. "
            f"User message: {message}. "
            f"Provide helpful, concise guidance about prediction markets, "
            f"strategy building, or risk management."
        )
        return await self._llm_generate_response(prompt, "general_chat", message)

    async def _handle_run_pipeline(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        hierarchical_context: str,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        steps = []

        rlm_result = None
        if self.rlm:
            try:
                rlm = await self.rlm.scan_directory("./data/archives", keywords=None)
                rlm_result = rlm.get("alpha_vector", {})
                steps.append({"step": "rlm_scan", "status": "completed"})
            except Exception as exc:
                steps.append({"step": "rlm_scan", "status": "failed", "error": str(exc)})

        research_result = None
        if self.autoresearch:
            try:
                climate = await self.market_regime.assess_climate([]) if self.market_regime else {}
                research_result = await self.autoresearch.run_iteration(
                    strategy_id="", market_history=[], climate=climate,
                )
                steps.append({"step": "research", "status": "completed", "score": research_result.get("composite_score")})
            except Exception as exc:
                steps.append({"step": "research", "status": "failed", "error": str(exc)})

        memory_synced = False
        if research_result and research_result.get("hypothesis"):
            await self._handle_research_phase3_memory(research_result)
            refined = await self._handle_research_phase4_refinement(research_result, {"synced": True, "score": research_result.get("composite_score", 0)})
            memory_synced = refined
            steps.append({"step": "phase4_refinement", "status": "completed" if refined else "skipped"})

        return {
            "type": "pipeline_result",
            "intent": IntentType.RUN_PIPELINE.value,
            "hierarchical_filter": hierarchical_context,
            "steps": steps,
            "rlm_alpha": rlm_result,
            "research": research_result,
            "memory_synced": memory_synced,
            "response": "Full analysis pipeline complete. See steps for details.",
        }

    async def _handle_spawn_agent(
        self,
        message: str,
        context: dict[str, Any] | None,
        memory_context: str | None,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        goal = message
        toolsets = context.get("toolsets", ["file", "web"]) if context else ["file", "web"]
        role = context.get("role", "leaf") if context else "leaf"

        try:
            agent = await self.agent_spawner.spawn_agent(
                goal=goal,
                context=memory_context,
                toolsets=toolsets,
                role=role,
                parent_session_id=session.get("session_id", "default"),
            )
            return {
                "type": "agent_spawned",
                "intent": IntentType.SPAWN_AGENT.value,
                "agent_id": agent.agent_id,
                "status": agent.status.value,
                "response": f"Sub-agent '{agent.agent_id}' spawned with goal: {goal[:100]}",
            }
        except RuntimeError as exc:
            return {
                "type": "agent_spawn_error",
                "intent": IntentType.SPAWN_AGENT.value,
                "response": f"Cannot spawn agent: {exc}",
            }

    async def _llm_generate_response(
        self,
        prompt: str,
        intent_value: str,
        original_message: str,
    ) -> dict[str, Any]:
        if self.hermes.available:
            result = await self.hermes.process_message(prompt, {"user_id": "orchestrator"})
            response = result.get("response", "")
        else:
            response = (
                f"I understand you're asking about '{original_message[:100]}'. "
                f"To provide AI-powered responses, configure Hermes-Agent "
                f"by setting HERMES_INFERENCE_MODEL and a provider API key."
            )
        return {
            "type": f"{intent_value}_response",
            "intent": intent_value,
            "response": response,
        }

    async def _recall_relevant_memory(
        self,
        message: str,
        intent: IntentType | None,
    ) -> str | None:
        try:
            results = self.memory.recall_similar("agent_memory", message, n_results=3)
            if results:
                return " | ".join(r.get("text", "") for r in results)
        except Exception as exc:
            logger.debug("Memory recall failed: %s", exc)
        return None

    async def _store_interaction(
        self,
        session_id: str,
        message: str,
        result: dict[str, Any],
        intent: IntentType,
    ) -> None:
        try:
            entry = (
                f"User: {message[:200]} | "
                f"Intent: {intent.value} | "
                f"Response: {result.get('response', '')[:200]}"
            )
            self.memory.store_memory(
                "agent_memory",
                f"{session_id}_{uuid.uuid4().hex[:8]}",
                entry,
                {"session_id": session_id, "intent": intent.value, "timestamp": time.time()},
            )
        except Exception as exc:
            logger.debug("Memory store failed: %s", exc)

    async def _attempt_correction(
        self,
        message: str,
        context: dict[str, Any] | None,
        session: dict[str, Any],
    ) -> dict[str, Any] | None:
        if session["correction_count"] >= self._max_retries:
            return None

        session["correction_count"] += 1
        async with self._lock:
            self._state[session.get("session_id", "default")] = OrchestratorState.CORRECTING

        logger.info(
            "Attempting correction %d/%d for session %s",
            session["correction_count"],
            self._max_retries,
            session.get("session_id", "default"),
        )

        try:
            fallback_intent = IntentType.GENERAL_CHAT
            result = await self._handle_general_chat(message, context, None, session)
            async with self._lock:
                self._state[session.get("session_id", "default")] = OrchestratorState.IDLE
            return result
        except Exception as exc:
            logger.warning("Correction attempt failed: %s", exc)
            return None

    def _no_service_response(self, service_name: str) -> dict[str, Any]:
        return {
            "type": "service_unavailable",
            "response": f"The {service_name} is not configured. This feature requires additional setup.",
        }

    def get_traces(self, session_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
        traces = self._traces.get(session_id, [])
        return traces[-limit:]

    async def get_session_summary(self, session_id: str = "default") -> dict[str, Any]:
        session = self._sessions.get(session_id, {})
        goals = self._cognitive_goals.get(session_id, [])
        active_agents = self.agent_spawner.list_active_agents(parent_session_id=session_id)
        return {
            "session_id": session_id,
            "state": self.get_state(session_id).value,
            "message_count": session.get("message_count", 0),
            "error_count": session.get("error_count", 0),
            "correction_count": session.get("correction_count", 0),
            "last_activity": session.get("last_activity", 0),
            "cognitive_goals": goals,
            "active_agents": active_agents,
        }

    async def clear_session(self, session_id: str = "default") -> None:
        self._sessions.pop(session_id, None)
        self._state.pop(session_id, None)
        self._cognitive_goals.pop(session_id, None)
        for agent in self.agent_spawner.get_agents_by_session(session_id):
            self.agent_spawner.terminate_agent(agent.agent_id)

    def get_cognitive_goals(self, session_id: str = "default") -> list[dict[str, Any]]:
        return self._cognitive_goals.get(session_id, [])
