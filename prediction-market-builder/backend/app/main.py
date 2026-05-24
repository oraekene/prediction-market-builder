import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from sqlalchemy import select
from app.database import engine, create_tables
from app.routers import auth, markets, strategies, chat, portfolio, analytics, research, risk, orchestrator, repl, alchemy, risk_templates, trades, paper_trading, meta_strategies, explainability
from app.agentic_search import search_router
from app.routers.auth import get_current_user
from app.services.research_scheduler import ResearchScheduler
from app.services.market_aggregator import MarketAggregator
from app.services.strategy_engine import StrategyEngine
from app.ai.autoresearch import AutoresearchService
from app.ai.tabpfn_service import TabPFNService
from app.ai.market_regime_service import MarketRegimeService
from app.ai.rlm_service import RLMService
from app.ai.hermes_sidecar import HermesSidecar
from app.ai.hermes_orchestrator import HermesOrchestrator
from app.ai.skill_creator import SkillCreator
from app.ai.watchdog import WatchdogService, HealthStatus
from app.ai.tool_registry import ToolRegistry, registry as tool_registry
from app.ai.agent_spawner import AgentSpawner
from app.ai.git_manager import GitManager
from app.ai.repl_service import REPLService
from app.ai.shap_explainer import ShapExplainer
from app.services.explainability_service import ExplainabilityService
from app.ai.alchemy_service import AlchemyService, AlchemyRequest, ConnectionEngine
from app.ai.domain_providers import DomainRegistry
from app.agentic_search.search_orchestrator import SearchOrchestrator
from app.ai.domain_providers.market_provider import MarketDomainProvider
from app.ai.domain_providers.news_provider import NewsDomainProvider
from app.ai.domain_providers.memory_provider import MemoryDomainProvider
from app.ai.domain_providers.onchain_provider import OnChainDomainProvider
from app.ai.domain_providers.macros_provider import MacrosDomainProvider
from app.ai.domain_providers.social_provider import SocialDomainProvider
from app.ai.domain_providers.legal_provider import LegalDomainProvider

logger = logging.getLogger(__name__)

tabpfn = TabPFNService()
market_regime = MarketRegimeService()
rlm = RLMService()
autoresearch = AutoresearchService(tabpfn_service=tabpfn)
shap_explainer = ShapExplainer()
explainability_service = ExplainabilityService(
    shap_explainer=shap_explainer,
    tabpfn_service=tabpfn,
)
scheduler = ResearchScheduler(
    autoresearch=autoresearch,
    tabpfn=tabpfn,
    market_regime=market_regime,
    rlm=rlm,
    explainability=explainability_service,
)

hermes = HermesSidecar()
market_aggregator = MarketAggregator()
strategy_engine = StrategyEngine()
git_manager = GitManager(repo_path=Path("./data/skills_repo"))
agent_spawner = AgentSpawner()
repl_service = REPLService()

try:
    alchemy_registry = DomainRegistry()
    alchemy_registry.register(MarketDomainProvider(market_aggregator=market_aggregator))
    alchemy_registry.register(NewsDomainProvider())
    alchemy_registry.register(MemoryDomainProvider())
    alchemy_registry.register(OnChainDomainProvider())
    alchemy_registry.register(MacrosDomainProvider())
    alchemy_registry.register(SocialDomainProvider())
    alchemy_registry.register(LegalDomainProvider())
    alchemy_service = AlchemyService(
        domain_registry=alchemy_registry,
        hermes=hermes,
    )
except Exception as exc:
    logger.warning("AlchemyService init failed: %s", exc)
    alchemy_service = None  # type: ignore[assignment]

orchestrator_instance = HermesOrchestrator(
    hermes=hermes,
    autoresearch=autoresearch,
    rlm=rlm,
    tabpfn=tabpfn,
    market_regime=market_regime,
    strategy_engine=strategy_engine,
    market_aggregator=market_aggregator,
    tool_registry=tool_registry,
    agent_spawner=agent_spawner,
    git_manager=git_manager,
)
skill_creator = SkillCreator(
    tool_registry=tool_registry,
    git_manager=git_manager,
)
search_orchestrator = SearchOrchestrator()
watchdog = WatchdogService()


def _check_chromadb() -> bool:
    try:
        from app.data.chromadb_manager import ChromaDBManager
        ChromaDBManager()
        return True
    except Exception:
        return False


async def _on_unhealthy_handler(check_name: str, check_result: dict) -> None:
    logger.error("UNHEALTHY trigger: %s - %s", check_name, check_result.get("error", "unknown"))
    if check_name == "hermes":
        orchestrator_instance.hermes = HermesSidecar()
    await watchdog.track_session_activity("_system")


def _on_recovery_handler(check_name: str) -> None:
    logger.info("RECOVERY: %s is healthy again", check_name)


watchdog.register_health_check("hermes", lambda: orchestrator_instance.hermes.available)
watchdog.register_health_check("chromadb", _check_chromadb)
watchdog.register_health_check("scheduler_running", lambda: getattr(scheduler, '_running', False))

watchdog.on_unhealthy(_on_unhealthy_handler)
watchdog.on_recovery(_on_recovery_handler)


@asynccontextmanager
async def _migrate_passwords():
    from app.database import async_session
    from app.models.user import User
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        migrated = 0
        for u in users:
            if not u.hashed_password.startswith("$2b$"):
                u.hashed_password = pwd_ctx.hash(u.hashed_password)
                migrated += 1
        if migrated:
            await session.commit()
            logger.info("Migrated %d plain-text passwords to bcrypt", migrated)


async def lifespan(app: FastAPI):
    git_manager.init_repo()
    await create_tables()
    await _migrate_passwords()
    await explainability_service.initialize()

    _register_rlm_tools(tool_registry, rlm)
    _register_search_tools(tool_registry, search_orchestrator)
    _register_repl_tools(tool_registry, repl_service)
    if alchemy_service is not None:
        _register_alchemy_tools(tool_registry, alchemy_service)
        alchemy.init_alchemy(alchemy_service)
    explainability.init_explainability(explainability_service)
    strategies.init_strategy_engine(
        strategy_engine=strategy_engine,
        tabpfn=tabpfn,
        market_regime=market_regime,
        explainability_service=explainability_service,
        hermes=hermes,
        rlm=rlm,
        market_aggregator=market_aggregator,
    )
    scheduler.set_broadcast(research.broadcast_to_session)
    research.init_scheduler(scheduler)
    orchestrator.init_orchestrator(orchestrator_instance, watchdog, skill_creator)
    search_router.init_search_orchestrator(search_orchestrator)
    await scheduler.start()
    await watchdog.start()
    yield
    await watchdog.stop()
    await scheduler.stop()
    await engine.dispose()


def _register_rlm_tools(tr: ToolRegistry, rlm_service: RLMService) -> None:
    tr.register(
        name="rlm_scan_directory",
        toolset="rlm",
        schema={
            "description": "Recursively scan a directory for alpha signals using dspy.RLM",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Path to scan"},
                    "keywords": {"type": "string", "description": "Comma-separated keywords"},
                },
            },
        },
        handler=lambda **kw: {"result": "rlm_scan_dispatched"},
        check_fn=lambda: rlm_service.check_available(),
        shared_check_key="dspy",
    )
    tr.register(
        name="rlm_detect_drift",
        toolset="rlm",
        schema={
            "description": "Detect linguistic drift between historical and recent texts",
            "parameters": {
                "type": "object",
                "properties": {
                    "historical_texts": {"type": "array", "items": {"type": "string"}},
                    "recent_texts": {"type": "array", "items": {"type": "string"}},
                    "entities": {"type": "string", "description": "Comma-separated entities"},
                },
            },
        },
        handler=lambda **kw: {"result": "rlm_drift_dispatched"},
        check_fn=lambda: rlm_service.check_available(),
        shared_check_key="dspy",
    )
    tr.register(
        name="rlm_sub_agent",
        toolset="rlm",
        schema={
            "description": "Spawn a recursive sub-agent for deep document analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "Document text to analyze"},
                    "instruction": {"type": "string", "description": "What to extract"},
                },
            },
        },
        handler=lambda **kw: {"result": "rlm_sub_agent_dispatched"},
        check_fn=lambda: rlm_service.check_available(),
        shared_check_key="dspy",
    )


def _register_alchemy_tools(tr: ToolRegistry, alchemy_service: AlchemyService) -> None:
    tr.register(
        name="alchemy_analyze",
        toolset="alchemy",
        schema={
            "description": "Run cross-domain analysis to find non-obvious connections between disparate data domains (markets, news, on-chain, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Analysis query, e.g. 'Will ETH > $5K by Dec?'"},
                    "force_refresh": {"type": "boolean", "description": "Skip cached results"},
                },
                "required": ["query"],
            },
        },
        handler=lambda **kw: alchemy_service.analyze(AlchemyRequest(query=kw.get("query", ""), force_refresh=kw.get("force_refresh", False))),
    )
    tr.register(
        name="alchemy_check",
        toolset="alchemy",
        schema={
            "description": "Quick check: are there any known cross-domain connections for this market or query?",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Market question or search term"},
                },
                "required": ["query"],
            },
        },
        handler=lambda **kw: alchemy_service.check_existing(kw.get("query", "")),
    )


def _register_repl_tools(tr: ToolRegistry, repl_service: REPLService) -> None:
    tr.register(
        name="repl_create",
        toolset="repl",
        schema={
            "description": "Create a new Python REPL sandbox session for on-the-fly data analysis",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=lambda **kw: repl_service.create_session(),
    )
    tr.register(
        name="repl_execute",
        toolset="repl",
        schema={
            "description": "Execute Python code in a sandboxed REPL session. Variables persist across calls within the same session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "REPL session ID"},
                    "code": {"type": "string", "description": "Python code to execute"},
                },
                "required": ["session_id", "code"],
            },
        },
        handler=lambda **kw: repl_service.execute_code(kw["session_id"], kw["code"]),
    )


def _register_search_tools(tr: ToolRegistry, search: SearchOrchestrator) -> None:
    from app.agentic_search import search_router as sr
    sr.register_search_tools(tr, search)


app = FastAPI(title="PM Strategy Builder", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


app.include_router(auth.router)
app.include_router(markets.router, dependencies=[Depends(get_current_user)])
app.include_router(strategies.router, dependencies=[Depends(get_current_user)])
app.include_router(chat.router, dependencies=[Depends(get_current_user)])
app.include_router(portfolio.router, dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, dependencies=[Depends(get_current_user)])
app.include_router(research.router, dependencies=[Depends(get_current_user)])
app.include_router(risk.router, dependencies=[Depends(get_current_user)])
app.include_router(orchestrator.router, dependencies=[Depends(get_current_user)])
app.include_router(repl.router, dependencies=[Depends(get_current_user)])
app.include_router(alchemy.router, dependencies=[Depends(get_current_user)])
app.include_router(risk_templates.router, dependencies=[Depends(get_current_user)])
app.include_router(trades.router, dependencies=[Depends(get_current_user)])
app.include_router(paper_trading.router, dependencies=[Depends(get_current_user)])
app.include_router(meta_strategies.router, dependencies=[Depends(get_current_user)])
app.include_router(explainability.router, dependencies=[Depends(get_current_user)])
app.include_router(search_router.router, dependencies=[Depends(get_current_user)])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
