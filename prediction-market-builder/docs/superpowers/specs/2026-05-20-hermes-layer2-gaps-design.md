# Hermes Layer 2 Gaps: REPL, Alchemy, Containerization, GA

**Date:** 2026-05-20
**Status:** Design — pending approval
**Phase:** Phase 3 — Layer 2 Hermes capabilities
**Depends on:** Phases 1 & 2 complete (TabPFNService, MarketRegimeService, HermesSidecar, Backtester, StrategyEngine, RiskManager, ChromaDB, DuckDB)

---

## 1. Architecture Overview

### 1.1 The Four Missing Pieces

| # | Gap | Component | Layer | Status |
|---|-----|-----------|-------|--------|
| 1 | **Sandboxed REPL** | `REPLService` | Layer 2 Hermes | New |
| 2 | **Cross-Domain Alchemy** | `AlchemyService` | Layer 2 Hermes | New |
| 3 | **Skill Containerization** | `SkillCreator` Docker step | Layer 2 Hermes | Missing (generates code, no container) |
| 4 | **pi-autoresearch GA/NSGA-II** | `AutoresearchService` optimizer | Layer 3 Research | Missing (core loop works, no GA) |

### 1.2 How They Fit Together

```
Hermes-Agent (Orchestrator)
│
├── Tool Registry ─────────────── REPLService (1)
│                                     │
│                              ┌──────┴──────────┐
│                              │                  │
├── SkillCreator ──────── Containerization (3) ──┤
│                                                 │
├── AlchemyService (2) ──── Cross-domain signals ─┤
│                           │                      │
│                    ┌──────┴──────┐                │
│                    │             │                │
│              DomainProviders  ConnectionEngine   │
│                    │             │                │
├── AutoresearchService (4) ── GA/NSGA-II ─────────┤
│                           │                      │
├── MarketRegimeService ── Heuristic climate context ──┘
│
└── ChromaDB (memory, alchemy_memory, skill_store)
```

---

## 2. Sandboxed REPL (`REPLService`)

### 2.1 Purpose
Hermes writes and runs Python code on-the-fly for data analysis in a **RestrictedPython** sandbox. Each analysis session maintains a persistent namespace so users can load data once and query it iteratively. The PRD calls this "recursive Python REPL exploration."

### 2.2 Architecture

```
hermes_orchestrator.py
  └─→ repl_service.py                    # Public API
        ├─→ REPLSession                  # Per-session sandbox
        │     ├─ RestrictedPython compiler   # AST-level sandbox
        │     ├─ allowed_builtins            # Whitelist: print, len, range, min, max, sum, sorted, enumerate, zip, map, filter, any, all, str, int, float, bool, list, dict, set, tuple, type, isinstance, hasattr, getattr, dir, repr, abs, round, pow, hex, bin, ord, chr
        │     ├─ allowed_modules            # Whitelist: math, statistics, json, re, collections, itertools, functools, typing, datetime, random
        │     ├─ io.StringIO stdout cap      # Capture print() output
        │     └─ asyncio timeout (30s)       # Hard execution limit
        └─→ REPLSessionManager          # In-memory session store
              ├─ session_id → REPLSession
              ├─ auto-TTL expiry (30min idle)
              └─ max 50 concurrent sessions
```

### 2.3 Session Lifecycle

```
CREATE → [idle] → EXECUTE → [idle] → EXECUTE → ... → DESTROY
                    ↑                          |
                    └── auto-TTL (30 min) ──────┘
```

- **Stateless on execute**: Each `execute()` call is a fresh RestrictedPython run against the same namespace. The namespace persists across calls.
- **No persistence**: Namespaces are in-memory only. If the server restarts, sessions expire.
- **No file/network access**: RestrictedPython blocks `import`, `open`, `exec`, `eval`, `__import__`, `__subclasses__`, `__globals__`.

### 2.4 Data Models

```python
class REPLSessionState(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    variable_count: int            # number of keys in namespace
    variable_types: dict[str, str] # name → type name (for inspection)
    execution_count: int
    error_count: int

class REPLExecuteRequest(BaseModel):
    code: str                      # Python code to execute
    session_id: str

class REPLExecuteResponse(BaseModel):
    session_id: str
    stdout: str                    # captured print() output
    result: str | None             # repr() of last expression, if any
    error: str | None              # traceback if execution failed
    execution_time_ms: int
    variable_types: dict[str, str] # updated after execution
```

### 2.5 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/repl/create` | Create new REPL session |
| `POST` | `/ai/repl/{session_id}/execute` | Execute code in session |
| `GET` | `/ai/repl/{session_id}/state` | Inspect namespace (names + types) |
| `DELETE` | `/ai/repl/{session_id}` | Destroy session |

### 2.6 Hermes Tool Registration

```python
ToolRegistry.register(
    name="repl_create",
    description="Create a new Python REPL sandbox session for on-the-fly data analysis",
    handler=REPLService.create_session,
)

ToolRegistry.register(
    name="repl_execute",
    description="Execute Python code in a sandboxed REPL session. Variables persist across calls within the same session.",
    handler=REPLService.execute_code,
)
```

### 2.7 Security Model

| Layer | Mechanism |
|-------|-----------|
| **RestrictedPython** | AST-level sandbox — compiles code to restricted bytecode; blocks `import`, `exec`, `eval`, `open`, attribute access to `__subclasses__`/`__globals__` |
| **Pre-check** | `ast.parse()` before RestrictedPython — rejects malformed code early |
| **Timeout** | `asyncio.wait_for(executor, 30.0)` — hard limit |
| **Builtins** | Explicit whitelist only — no `__import__`, `getattr` on restricted objects |
| **Modules** | Import guard — only whitelisted modules are importable; others raise `ImportError` |
| **Future** | `ProcessPoolExecutor` spawn context for process-level isolation (Phase 4) |

---

## 3. Cross-Domain Alchemy (`AlchemyService`)

### 3.1 Purpose
Find novel, non-obvious connections across disparate data domains. PRD example: "legal filings + on-chain data." In practice: market odds correlated with news sentiment, on-chain whale movements preceding odds shifts, regulatory filings that predict market rule changes. These connections are surfaced as structured **alchemical signals** that Hermes can act on.

### 3.2 Architecture

```
hermes_orchestrator.py
  └─→ alchemy_service.py
        ├─→ DomainRegistry                     # Pluggable domain providers
        │     ├─ MarketDomainProvider           # Polymarket/Kalshi odds, volume, liquidity
        │     ├─ NewsDomainProvider             # Headlines via web fetch (Scrapling/httpx)
        │     ├─ OnChainDomainProvider          # Gas, TVL, whale moves (placeholder — Phase 4)
        │     ├─ MacrosDomainProvider           # CPI, rates, indices (placeholder — Phase 4)
        │     ├─ SocialDomainProvider           # Twitter/X sentiment (placeholder — Phase 4)
        │     ├─ LegalDomainProvider            # Regulatory filings (placeholder — Phase 4)
        │     └─ MemoryDomainProvider           # Past patterns from ChromaDB
        ├─→ ConnectionEngine                   # Core cross-domain matching
        │     ├─ 1. Embed each domain's data → sentence-transformers
        │     ├─ 2. Cross-domain cosine similarity (every domain × every other)
        │     ├─ 3. Threshold filter (similarity > 0.65)
        │     ├─ 4. Hermes synthesis: "Given X in domain A and Y in domain B, what's the connection?"
        │     └─ 5. Novelty scoring: compare against ChromaDB alchemy_memory
        ├─→ AlchemyBus                         # Event-based signal broadcast
        └─→ ChromaDB collection: "alchemy_memory"
```

### 3.3 Flow

```
1. TRIGGER: Hermes calls alchemy_service.analyze(query="Will ETH > $5K by Dec?")
        │
2. DOMAIN DISCOVERY: DomainRegistry.select(query)
   → MarketDomainProvider (odds for "ETH > $5K")
   → NewsDomainProvider (headlines about ETH, regulatory news)
   → MemoryDomainProvider (past alchemy reports about ETH)
        │
3. DATA RETRIEVAL: Each provider fetches data
   → Market: {current_odds: 0.32, volume_24h: 1.2M, liquidity: 4.5M}
   → News: ["SEC delays ETH ETF decision", "Whale moves 50K ETH to CEX", ...]
   → Memory: [{connection: "whale_movement + odds_drop", strength: 0.81}, ...]
        │
4. CROSS-DOMAIN MATCHING: ConnectionEngine
   a. Embed each data item into shared vector space
   b. Pairwise cosine similarity across domains
   c. Pairs > 0.65 threshold → candidate connections
        │
5. LLM SYNTHESIS: Hermes generates explanation for each candidate
   → "Whale movement to CEX historically precedes odds drops by 2-4 hours.
      Current whale movement + odds at 0.32 suggests odds may drop to 0.28."
        │
6. NOVELTY CHECK: Compare against alchemy_memory in ChromaDB
   → Seen before? Return original report + updated data
   → Novel? Store and return
        │
7. BROADCAST (if high-strength): Push signal to Hermes
   → Hermes may spawn a strategy, trigger watchdog, or store for next
     pi-autoresearch iteration
```

### 3.4 Data Models

```python
class AlchemyRequest(BaseModel):
    query: str                                 # e.g. "Will ETH > $5K by Dec?"
    market_id: str | None                      # optional — restrict to single market
    force_refresh: bool = False                # skip cached results

class AlchemyReport(BaseModel):
    id: str                                   # UUID
    query: str
    timestamp: datetime
    domains_queried: list[str]                 # which domains were available
    connections: list[AlchemyConnection]
    summary: str                              # LLM-generated executive summary
    novelty_score: float                      # 0.0–1.0 (aggregate)

class AlchemyConnection(BaseModel):
    source_domain: str                        # e.g. "markets"
    source_entity: str                        # e.g. "Will ETH > $5K by Dec?"
    target_domain: str                        # e.g. "onchain"
    target_entity: str                        # e.g. "whale_movement: 50K ETH to CEX"
    correlation_type: str                     # "leading_indicator" | "confirms" | "contradicts" | "causal"
    similarity_score: float                   # 0.0–1.0 (embedding cosine)
    strength: float                           # 0.0–1.0 (LLM confidence blended with similarity)
    novelty_score: float                      # 0.0–1.0 (1.0 = never seen before)
    explanation: str                          # LLM-generated: why this matters
    evidence: list[str]                       # Supporting data excerpts
```

### 3.5 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/alchemy/analyze` | Run cross-domain analysis |
| `GET` | `/ai/alchemy/history` | Past alchemy reports |
| `GET` | `/ai/alchemy/history/{id}` | Single report detail |

### 3.6 Hermes Tool Registration

```python
ToolRegistry.register(
    name="alchemy_analyze",
    description="Run cross-domain analysis to find non-obvious connections between disparate data domains (markets, news, on-chain, etc.)",
    handler=AlchemyService.analyze,
)

ToolRegistry.register(
    name="alchemy_check",
    description="Quick check: are there any known cross-domain connections for this market?",
    handler=AlchemyService.check_existing,
)
```

### 3.7 DomainProvider Interface

```python
class DomainProvider(ABC):
    """Pluggable data source for a specific domain."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def query(self, query: str, context: dict | None = None) -> DomainData:
        """Fetch data relevant to the query from this domain."""

class DomainData(BaseModel):
    domain: str
    items: list[DomainItem]
    query_time_ms: int
    error: str | None = None

class DomainItem(BaseModel):
    text: str                     # Human-readable content (for embedding + LLM)
    metadata: dict                # Structured fields (e.g. {"odds": 0.32, "volume": 1.2e6})
    source: str                   # Original URL or identifier
    timestamp: datetime | None
```

### 3.8 Deferred Providers (Phase 4)

- `SocialDomainProvider` — requires Twitter/X API key or scraping setup
- `LegalDomainProvider` — requires SEC/regulatory filing crawler
- `MacrosDomainProvider` — requires economic indicator data source
- `OnChainDomainProvider` — requires blockchain RPC or indexer

These are stubbed to return empty results with a `not_implemented` flag so the pipeline gracefully degrades.

---

## 4. Toto-2 Migration History

### 4.1 What Happened
The file `toto2_service.py` **was originally a heuristic mislabeled as Toto-2**. It used CV/z-score statistics, not the Datadog Toto-2 transformer. The real Toto-2 (2.5B param time-series foundation model) cannot coexist in this venv because it pins `numpy==1.26.4`, which conflicts with TabPFN v8 and DSPy.

### 4.2 Migration Completed
- **Renamed file** → `app/ai/market_regime_service.py`
- **Renamed class** → `MarketRegimeService` (86 lines)
- **Updated all 8 references** in: `main.py`, `research.py` router, `hermes_orchestrator.py`, `research_scheduler.py`, `test_ai_services.py`, `SOURCES.txt`
- **Kept DB column names** (`toto2_regime`, `toto2_volatility`) for API stability
- **Service interface** — methods: `assess_climate()`, `detect_anomalies()`, `compute_volatility_surface()`

### 4.3 Toto-2 Install Path (Separate Container)
The real Datadog Toto-2 model remains documented for deployment in a **separate Docker container** (not this venv):

```
# docker-compose.toto2.yml
services:
  toto2-inference:
    image: datadog/toto2:latest
    ports:
      - "8501:8501"   # gRPC inference endpoint
    environment:
      - MODEL_SIZE=2.5B
      - DEVICE=cuda   # requires GPU with 16GB+ VRAM
```

When deployed, `MarketRegimeService` would become a **fallback** — the system would call Toto-2's gRPC endpoint first, falling back to the heuristic if unavailable. This is a Phase 4 concern; the heuristic service is sufficient for Phase 3.

---

## 5. Skill Containerization (Docker Build Step)

### 5.1 Current State
`SkillCreator` generates Python code, validates it with `ast.parse()`, registers it as an in-memory callable, adds it to `ToolRegistry`, persists to Git, and stores metadata in ChromaDB. **But it never builds a Docker image or runs it in a container.** The PRD calls for "containerizes them" — this step is missing.

### 5.2 What Needs to Change

| Current | Target |
|---------|--------|
| Code generation → validation → registration | Code generation → validation → **Docker build** → container test → registration |
| In-memory `exec()` | In-memory `exec()` **for development**; Docker **for production** |
| Tool registered with Python callable | Tool registered with **either** callable **or** container endpoint |

### 5.3 Architecture

```
SkillCreator.create_skill_from_description()
  │
  ├── 1. _generate_code(description) → Python
  ├── 2. _validate_code(code) → ast.parse() + signature check
  ├── 3. _compile_and_register(code) → in-memory handler [DEV]
  │
  ├── [NEW] 4. _build_container(code) → Docker image
  │       ├── Generate Dockerfile inline:
  │       │   FROM python:3.12-slim
  │       │   WORKDIR /skill
  │       │   COPY skill.py .
  │       │   RUN pip install pydantic
  │       │   CMD ["python", "skill.py"]
  │       ├── Write code to temp dir
  │       ├── subprocess.run(["docker", "build", "-t", tag, "."])
  │       └── subprocess.run(["docker", "run", "--rm", tag])  # smoke test
  │
  ├── [NEW] 5. _test_container(tag) → run + verify handler output
  │
  ├── [NEW] 6. _register_container_tool(tag)
  │       → ToolRegistry entries can now point to a container
  │         (executed via Docker SDK) instead of an in-memory callable
  │
  ├── 7. _save_to_git(code)
  └── 8. _store_skill(metadata)
```

### 5.4 Data Model Changes

```python
# Add to ToolRegistry entry:
class ToolRegistryEntry(BaseModel):
    name: str
    description: str
    handler: Callable | None = None       # existing — in-memory mode
    container_image: str | None = None    # new — Docker image tag
    container_command: list[str] | None = None  # new — override CMD if needed
    execution_mode: Literal["in_memory", "container"] = "in_memory"
```

### 5.5 When Containerization Happens

| Mode | In-Memory | Container |
|------|-----------|-----------|
| Development | ✅ Default | Optional (docker not required) |
| Production | Fallback only | ✅ Required |
| CI/CD | Never | ✅ Always |

The `SkillCreator` checks `docker` availability at startup. If Docker is not available, it falls back to in-memory mode (current behavior).

### 5.6 Hermes Orchestrator Changes

When dispatching a tool call, `HermesOrchestrator` checks `execution_mode`:
- `in_memory`: call `handler()` directly (current)
- `container`: run `docker run --rm {image} {command}` with input via stdin or args, capture stdout as result

---

## 6. pi-autoresearch GA/NSGA-II Enhancement

### 6.1 Current State
`AutoresearchService` generates hypotheses using **5 template-based prompts** (`HYPOTHESIS_TEMPLATES`) with random parameter sampling. The core experiment loop (hypothesis → quick rejection → backtest → validate → score → keep/revert) works, but there is **no genetic programming, NSGA-II multi-objective optimization, or Monte Carlo simulation**.

### 6.2 What to Add

| Current | Target |
|---------|--------|
| 5 hard-coded hypothesis templates | Template parameters evolve via crossover + mutation |
| Random parameter sampling | NSGA-II multi-objective optimization (Sharpe + Win Rate + Risk) |
| Independent iterations | Population-based evolution with Pareto front tracking |
| No Monte Carlo simulation | Monte Carlo parameter sensitivity analysis before backtest |
| Single objective scoring | Multi-objective Pareto ranking with crowding distance |

### 6.3 Architecture

```
AutoresearchService
  ├── existing: _generate_hypotheses()    # LLM-based (existing)
  ├── new: _genetic_generation()          # NSGA-II optimizer
  │     ├── Population: hypotheses encoded as gene vectors
  │     ├── Selection: tournament selection on Pareto rank
  │     ├── Crossover: SBX (simulated binary crossover)
  │     ├── Mutation: polynomial mutation
  │     └── Elite preservation: top 20% by Pareto rank
  ├── new: _monte_carlo_sensitivity()     # Pre-backtest MC simulation
  │     ├── Sample N parameter variants around hypothesis
  │     ├── Run lightweight forward simulation
  │     ├── Filter: keep if median Sharpe > threshold
  │     └── Return: confidence interval for expected Sharpe
  └── existing: _compute_composite_score() # Three presets (existing)
```

### 6.4 Gene Encoding

Each hypothesis is encoded as a fixed-length gene vector:

```python
class HypothesisGene(BaseModel):
    """Fixed-length gene encoding a strategy hypothesis."""
    entry_threshold: float           # 0.0–1.0 — mapped from continuous gene
    exit_threshold: float            # 0.0–1.0
    position_size: float             # 0.0–1.0 (fraction of capital)
    stop_loss: float                 # 0.0–1.0
    take_profit: float               # 0.0–1.0
    lookback_window: int             # 1–100 (hours)
    min_confidence: float            # 0.0–1.0
    max_holding_period: int          # 1–72 (hours)
    # Categorical as one-hot:
    regime_filter: int               # 0=any, 1=trending, 2=volatile, 3=ranging, 4=calm
    signal_source: int               # 0=odds_only, 1=volume_accel, 2=sentiment, 3=hybrid
```

### 6.5 NSGA-II Algorithm

```python
class NSGAIIOptimizer:
    """
    Non-dominated Sorting Genetic Algorithm II for multi-objective
    optimization of strategy hypotheses.

    Objectives:
      1. Maximize Sharpe ratio
      2. Maximize Win Rate
      3. Minimize Max Drawdown

    Input: initial_population (from LLM templates or random)
    Output: Pareto-optimal set of HypothesisGenes
    """

    def __init__(self, population_size: int = 50, generations: int = 20):
        self.population_size = population_size
        self.generations = generations
        self.pareto_front: list[HypothesisGene] = []

    async def evolve(
        self,
        climate: dict,
        feature_importance: dict,
        market_history: pd.DataFrame,
        backtester: Backtester,
    ) -> list[HypothesisGene]:
        # 1. Initialize population from LLM templates + random perturbations
        # 2. For each generation:
        #    a. Backtest each individual (or quick-reject via TabPFN)
        #    b. Non-dominated sort → Pareto fronts
        #    c. Compute crowding distance
        #    d. Tournament selection
        #    e. SBX crossover + polynomial mutation
        #    f. Elite preservation
        # 3. Return final Pareto front

    def _non_dominated_sort(self, population: list[Individual]) -> list[list[Individual]]:
        """Classic NSGA-II fast non-dominated sort."""

    def _crowding_distance(self, front: list[Individual]) -> list[float]:
        """Per-objective crowding distance for diversity preservation."""

    def _tournament_selection(self, population: list[Individual]) -> Individual:
        """Crowded tournament: (rank, -distance) lexicographic."""

    def _sbx_crossover(self, parent1: HypothesisGene, parent2: HypothesisGene) -> tuple[HypothesisGene, HypothesisGene]:
        """Simulated binary crossover with η=15."""

    def _polynomial_mutation(self, gene: HypothesisGene, eta: float = 20) -> HypothesisGene:
        """Polynomial mutation with η=20."""
```

### 6.6 Monte Carlo Sensitivity Analysis

```python
class MonteCarloSensitivity:
    """
    Before running a full backtest, perform lightweight Monte Carlo
    simulation to estimate expected Sharpe and confidence interval.
    """

    async def analyze(
        self,
        hypothesis: HypothesisGene,
        market_history: pd.DataFrame,
        n_samples: int = 1000,
    ) -> MCSensitivityResult:
        # 1. Sample N parameter variants around base hypothesis
        #     (gaussian noise with σ=0.05 for continuous, random for categorical)
        # 2. Run quick forward simulation for each variant
        #     (simplified: estimate PnL from single signal + survival probability)
        # 3. Compute Sharpe distribution → median, CI, P(Sharpe > 0)
        # 4. Rank features by sensitivity (which params affect Sharpe most)
        # 5. Return: expected Sharpe, 90% CI, sensitivity ranking

class MCSensitivityResult(BaseModel):
    expected_sharpe: float
    ci_lower: float  # 5th percentile
    ci_upper: float  # 95th percentile
    prob_positive: float  # P(Sharpe > 0)
    sensitive_params: list[str]  # params with highest variance contribution
    recommendation: str  # "proceed" if CI entirely positive, "caution" if crosses zero
```

### 6.7 Integration into Existing Loop

```
Existing: LLM template → random params → TabPFN reject → backtest → score → keep/revert

Enhanced: LLM template (initial population) + NSGA-II evolution → MC sensitivity → TabPFN reject → backtest → score → Pareto rank → keep/revert

   1. Initial population: LLM generates 10 hypotheses (existing)
   2. First generation: backtest all 10 (existing)
   3. Subsequent generations:
      a. NSGA-II selects + breeds top individuals (NEW)
      b. Offspring pass through MC sensitivity filter (NEW)
      c. Only MC-approved hypotheses go to full backtest (NEW)
      d. Pareto rank replaces composite score for comparison (NEW)
   4. Memory: Pareto-optimal genes stored in ChromaDB (NEW)
   5. Each research session starts by loading prior Pareto front (NEW)
```

### 6.8 User-Facing Changes

- Research session config: new field `enable_genetic_optimization: bool` (default `False`)
- When enabled, the session runs NSGA-II instead of random template sampling
- UI shows Pareto front chart (Sharpe vs Win Rate scatter plot) in analytics dashboard
- "Generation X of Y" progress replaces generic iteration counter

---

## 7. API Endpoints Summary

### 7.1 New Endpoints

| Method | Path | Component |
|--------|------|-----------|
| `POST` | `/ai/repl/create` | REPL |
| `POST` | `/ai/repl/{session_id}/execute` | REPL |
| `GET` | `/ai/repl/{session_id}/state` | REPL |
| `DELETE` | `/ai/repl/{session_id}` | REPL |
| `POST` | `/ai/alchemy/analyze` | Alchemy |
| `GET` | `/ai/alchemy/history` | Alchemy |
| `GET` | `/ai/alchemy/history/{id}` | Alchemy |

### 7.2 Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| `POST` | `/api/research/config` | New field: `enable_genetic_optimization` |
| `GET` | `/api/research/sessions/{id}` | New field: `pareto_front` for GA sessions |

### 7.3 Hermes Tools (New Registrations)

| Tool Name | Component | Purpose |
|-----------|-----------|---------|
| `repl_create` | REPL | Create sandbox session |
| `repl_execute` | REPL | Execute code in session |
| `alchemy_analyze` | Alchemy | Full cross-domain analysis |
| `alchemy_check` | Alchemy | Quick known-connections check |

---

## 8. New & Modified Files

### 8.1 New Files

```
backend/app/
├── ai/
│   ├── repl_service.py          # NEW — Sandboxed REPL service
│   └── alchemy_service.py       # NEW — Cross-domain alchemy
│       └── domain_providers/     # NEW — Pluggable domain providers
│           ├── __init__.py
│           ├── market_provider.py
│           ├── news_provider.py
│           ├── memory_provider.py
│           ├── onchain_provider.py      # Stub
│           ├── macros_provider.py       # Stub
│           ├── social_provider.py       # Stub
│           └── legal_provider.py        # Stub
├── routers/
│   ├── repl.py                  # NEW — REPL endpoints
│   └── alchemy.py               # NEW — Alchemy endpoints
├── ai/
│   └── ga_optimizer.py          # NEW — NSGA-II genetic optimizer
│       └── mc_sensitivity.py    # NEW — Monte Carlo sensitivity analysis
```

### 8.2 Modified Files

```
backend/app/
├── ai/
│   ├── skill_creator.py         # MODIFY — Add containerization step
│   ├── tool_registry.py         # MODIFY — Add container_image, execution_mode fields
│   ├── autoresearch.py          # MODIFY — Add GA integration point
│   └── hermes_orchestrator.py   # MODIFY — Register 6 new tools, dispatch container tools
├── routers/
│   └── research.py              # MODIFY — pareto_front in session response
├── services/
│   └── research_scheduler.py    # MODIFY — GA config passthrough
└── tests/
    ├── test_repl.py             # NEW
    ├── test_alchemy.py          # NEW
    ├── test_ga_optimizer.py     # NEW
    ├── test_skill_creator.py    # MODIFY — Add containerization tests
    └── test_research.py         # MODIFY — Add GA integration tests
```

---

## 9. Service Dependencies

| Component | New Dependencies | Justification |
|-----------|-----------------|---------------|
| REPL | `RestrictedPython` | Python package for AST-level sandboxed execution |
| Alchemy | `sentence-transformers` | Already in pyproject.toml (via ChromaDB pipeline) |
| Containerization | `docker` CLI | Optional — `shutil.which("docker")` check at startup |
| GA/NSGA-II | None | Pure Python — no external optimizer needed |

---

## 10. Implementation Order

### Step 1: Sandboxed REPL
- Create `repl_service.py` with RestrictedPython executor
- Implement `REPLSessionManager` with TTL + concurrency limits
- Create `repl.py` router
- Register 2 REPL Hermes tools
- Tests

### Step 2: Skill Containerization
- Modify `skill_creator.py`: add `_build_container()` step
- Modify `tool_registry.py`: add container fields
- Modify `hermes_orchestrator.py`: container dispatch logic
- Tests (with Docker mock)

### Step 3: Cross-Domain Alchemy
- Create `domain_providers/` package with `MarketProvider`, `NewsProvider`, `MemoryProvider`
- Create `ConnectionEngine` with embedding + LLM synthesis
- Create `alchemy_service.py`
- Create `alchemy.py` router
- Register 2 Alchemy Hermes tools
- Tests

### Step 4: pi-autoresearch GA/NSGA-II
- Create `ga_optimizer.py` with NSGA-II core
- Create `mc_sensitivity.py`
- Modify `autoresearch.py`: add `_genetic_generation()` path
- Modify `research_scheduler.py`: GA config passthrough
- Modify `research.py`: `pareto_front` in responses
- Tests

### Step 5 (Phase 4): Deferred Domain Providers
- On-chain, macros, social, legal providers — stubs ready, flesh out in Phase 4

---

## 11. Key Runtime Behaviors

### REPL Session Expiry
- Sessions auto-expire after 30 minutes of inactivity
- Hermes is notified via tool response: `{"session_expired": true, "session_id": "..."}`
- Hermes should create a new session on next call

### Alchemy Domain Degradation
- If a domain provider fails (timeout, error), it is excluded from the current analysis
- The report includes: `domains_queried: ["markets", "news"], domains_failed: ["onchain"]`
- The pipeline continues with remaining domains

### Containerization Fallback
- If `docker` is not available, `SkillCreator` logs a warning and proceeds with in-memory registration
- Production deployment should ensure Docker is available

### GA Generation Pacing
- NSGA-II runs asynchronously (not blocking the request-response cycle)
- Each generation is a batch of backtests, each backtest is 500ms–30s
- Typical: 50 population × 20 generations = 1000 backtests → 15–60 minutes
- The UI shows generation progress via WebSocket
- User can stop mid-generation; best Pareto front so far is preserved

---

## 12. DB Schema Changes

### New Tables (via Alembic migration)
- `alchemy_reports` — one row per analysis
- `alchemy_connections` — one row per connection (child of alchemy_reports)


### Modified Tables
- `tool_registry_entries` — add columns: `container_image`, `execution_mode`
- `research_session_configs` — add column: `enable_genetic_optimization`
- `research_sessions` — already has `toto2_regime`, `toto2_volatility` (existing)
- `experiment_results` — already has needed fields (existing)
