# Unified Platform Roadmap

The Prediction Market Strategy Builder is an end-to-end platform for designing, evaluating, and deploying trading strategies on prediction markets (Polymarket, Kalshi, drift protocols).

---

## Phase 0: Foundation (Complete)

| Component | Status | Notes |
|-----------|--------|-------|
| Database schema (SQLAlchemy async) | Complete | PostgreSQL via asyncpg |
| Market aggregator (`MarketAggregatorRest`) | Complete | Fetches from Polymarket/Kalshi |
| TabPFN service | Complete | Tabular Prior-Data Fitted Network inference |
| Market regime service | Complete | Heuristic volatility/regime detection |
| SHAP explainability service | Complete | `PermutationExplainer`, `Independent` masker |
| ChromaDB vector store | Complete | Document embeddings & retrieval |
| Hermes sidecar | Complete | Tool-calling agent via Hermes-Agent |
| RLM service | Complete | Recursive Language Model with sub-agents |
| DSPy integration | Complete | LLM-as-program synthesis |
| DuckDB analytics | Complete | In-process OLAP |
| Risk manager | Complete | Kelly criterion, VaR, drawdown limits |
| Backtester | Complete | Historical simulation framework |
| Strategy engine (canvas) | Complete | Async DAG executor with 12+ service context |

---

## Phase 1: Core Strategy Canvas (Complete)

- [x] `NodeExecutor` with async DAG execution
- [x] `StrategyEngine.evaluate()` async
- [x] 17 palette node handlers (data sources, gates, transforms, ML, risk)
- [x] SHAP canvas node with real `PermutationExplainer`
- [x] Frontend evaluation wiring (`POST /api/strategies/evaluate`)
- [x] Strategy lifecycle (deploy/pause/resume/archive/rollback)
- [x] Hermes CoT transparency (traces, tool-calling)
- [x] RLM full trace logging (scan/synthesis/drift stages)

---

## Phase 2: Research & Intelligence (Complete)

- [x] `AutoresearchService` core loop
- [x] RLM directory scanning with keyword filter
- [x] RLM drift detection (embedding + DSPy)
- [x] Hermes orchestrator with conversation history
- [x] Research endpoints (`/api/research/rlm/*`, `/api/research/orchestrator/*`)

---

## Phase 3: Layer 2 Hermes Capabilities (Partial)

| Item | Status | Priority |
|------|--------|----------|
| Tool-calling agent loop | Done | Critical |
| Multi-turn CoT with tool result feedback | Done | Critical |
| Sandboxed REPL (`REPLService`) | **Not started** | High |
| Cross-domain Alchemy (`AlchemyService`) | **Not started** | High |
| Skill containerization (Docker) | **Not started** | Medium |
| pi-autoresearch GA/NSGA-II optimizer | **Not started** | Medium |

### Still Needed

- **REPLService**: Hermes writes and runs Python in a RestrictedPython sandbox with persistent namespace
- **AlchemyService**: Cross-domain signal synthesis from OnChain/Macros/Social/Legal providers
- **DomainProviders**: 4 provider interfaces for fetching cross-domain data
- **SkillCreator Docker**: Take generated skill code and produce a runnable container
- **GA/NSGA-II**: Multi-objective optimization over strategy hyperparameters

---

## Phase 4: Production Hardening (Deferred)

| Item | Notes |
|------|-------|
| Toto-2 gRPC service | Real model deployment via gRPC |
| OnChain provider | On-chain data indexing |
| Macros provider | Macroeconomic indicators |
| Social provider | Social sentiment streams |
| Legal provider | Regulatory/legal filings |
| Rust Execution Engine | High-performance order execution in Rust |
| Agentic Search Pipeline | Autonomous research agent swarm |
| `ProcessPoolExecutor` REPL isolation | Production sandbox for REPL |
| Real order execution (`place_bet` → live) | Replace stub with real execution |
| Rate limiting & auth | API key management, request throttling |
| Monitoring & alerting | Prometheus, Grafana, PagerDuty |
| Horizontal scaling | Multi-worker, distributed queue |

---

## Architecture Overview (Present State)

```
Frontend (React/Next.js)
    │
    ▼
FastAPI Router Layer
    │
    ├── /api/strategies ────── StrategyEngine → NodeExecutor (async DAG)
    │                              │
    │                              └── ExecutionContext (12 services)
    │
    ├── /api/research/rlm ───── RLMService → DriftDetector
    │                              │
    │                              └── Sub-agents (DSPy synthesis)
    │
    ├── /api/research/orchestrator ─ HermesOrchestrator → HermesSidecar
    │                                                         │
    │                                                         └── ToolRegistry
    │
    └── /api/markets ───────── MarketAggregatorRest
```

### ExecutionContext Services (12)

1. `market` — Current market data dict
2. `tabpfn` — `TabPFNService` for ML inference
3. `market_regime` — `MarketRegimeService` for volatility detection
4. `explainability_service` — `ShapExplainer` for feature attribution
5. `hermes` — `HermesSidecar` for agentic reasoning
6. `rlm` — `RLMService` for recursive language model analysis
7. `market_aggregator` — `MarketAggregatorRest` for live market data
8. `chromadb_manager` — `ChromaDBManager` for vector retrieval
9. `portfolio` — Portfolio state
10. `risk_calculator` — Risk calculation service
11. `portfolio_manager` — Portfolio management
12. `signal` — Signal generation

### Palette Node Handlers (17)

| Category | Handlers |
|----------|----------|
| Data Sources | `polymarket_source`, `kalshi_source`, `drift_source`, `web_search`, `news_source` |
| Logic | `time_condition`, `and_or_gate`, `branch` |
| Actions | `place_bet`, `forward`, `webhook` |
| Transforms | `bayesian_inference`, `monte_carlo`, `backtest`, `sentiment_filter` |
| ML | `tabpfn_signal` |
| Climate | `toto2_climate` (stub) |

---

## Next Actions

1. **Immediate**: Implement REPLService for agentic Python execution
2. **Immediate**: Wire ToolRegistry into HermesSidecar for tool discovery
3. **Short-term**: Implement DomainProviders + AlchemyService for cross-domain signals
4. **Short-term**: GA/NSGA-II optimizer in AutoresearchService
5. **Medium-term**: Skill containerization pipeline
6. **Long-term**: Phase 4 production hardening (Rust engine, gRPC, scaling)

## Key Design Decisions

- **PermutationExplainer over KernelExplainer**: 2-3x faster, comparable accuracy
- **Traces in memory not DB**: 200-trace rolling window avoids async DB overhead
- **All times UTC**: `time_condition` and all timestamps use `datetime.now(timezone.utc)`
- **`place_bet` is a stub**: Returns `{"approved": True}` but does not execute — Phase 4 item
- **Synthetic backtest data**: `SimulatedMarketHistory` until real data pipelines exist
- **No real model deployment**: Toto-2, TabPFN run in-process — gRPC deferred to Phase 4
