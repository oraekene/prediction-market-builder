# pi-autoresearch: Autonomous Strategy Discovery Engine

**Date:** 2026-05-19
**Status:** Design — approved for implementation
**Phase:** Phase 3 — Task 3.2 (pi-autoresearch Integration) + Task 3.3 (RLM Deep Archive Mining)
**Depends on:** Phases 1 & 2 complete (TabPFNService, Toto2Service, HermesSidecar, Backtester, StrategyEngine, RiskManager, ChromaDB, DuckDB)

---

## 1. Architecture Overview

### 1.1 The Five-Component Stack

| Component | Role | Data Transformation |
|-----------|------|---------------------|
| **RLM** (dspy.RLM) | Deep Librarian | Massive unstructured text → Structured Alpha Vector |
| **Hermes** (HermesSidecar) | CEO/Orchestrator | Alpha Vector + Memory → Executable Skills + Task State |
| **pi-autoresearch** (this system) | Lab/Scientist | Strategy parameters → Backtested code + Performance metrics |
| **Toto-2** (Toto2Service) | Climate Monitor | Market time series → Regime + Volatility + Anomalies |
| **TabPFN** (TabPFNService) | Oracle | Feature table → Calibrated Bayesian probability |

### 1.2 Research Pipeline

```
Phase 0: RLM Deep Mining (cron / on-demand / embedded)
  Input: Forums, PDFs, audit reports, news, transcripts, social media
  Process: dspy.RLM with async Python REPL
    → Recursive path traversal over file sources
    → Programmatic filter: Python scripts in REPL
    → Sub-agent spawning for large documents (200+ pages)
    → Linguistic change-point detection (semantic drift over time)
    → Historical pattern matching (vs. known crisis signatures)
  Output: Structured Alpha Vector (JSON) → ChromaDB + Hermes

     │
     ▼

Phase 1: Hermes (Orchestrator)
  Receives Alpha Vector from RLM
  → Creates/updates strategy skills based on discovered patterns
  → Stores alpha vector in ChromaDB with source + timestamp
  → Sets watchdog triggers for re-scan conditions
  → Passes structured context to pi-autoresearch loop

     │
     ▼

Phase 2: pi-autoresearch Loop (per iteration, 500ms–30s each)
  1. Hypothesis Generation (LLM + RLM + TabPFN + Toto-2 steer)
  2. Quick Rejection (TabPFN 500ms forward pass)
  3. Backtest (against historical market data)
  4. TabPFN Validation (final calibrated probability)
  5. Composite Scoring (Sharpe / Win-rate / Risk-adjusted)
  6. Git Commit or Rollback
  7. ChromaDB Memory Update

     │
     ▼

Phase 3: Toto-2 Climate Context (refreshed before each iteration)
  → Current regime (volatile/trending/ranging/calm)
  → Volatility surface (short/medium/long term)
  → Anomaly zones (odds/volume z-score events)
  → Exogenous covariate signals

     │
     ▼

Phase 4: TabPFN Final Validation (one forward pass per hypothesis)
  Input: [RLM_AlphaVector + Hypothesis_Params + Climate_Vector]
  Output: P(success), P(failure), confidence, edge
```

### 1.3 How TabPFN Steers Hypothesis Generation (Pre-Backtest)

| Stage | What Happens | Why |
|-------|-------------|-----|
| **1. Feature Importance Ranking** | TabPFN runs `get_feature_importance()` on the current strategy's feature table from past experiments. Returns top-N predictive features (e.g., `volume_momentum: 0.42`, `odds_volatility: 0.31`). | LLM focuses hypothesis space: "Generate hypotheses around volume momentum signals" |
| **2. Quick Rejection** | LLM drafts 5 hypothesis variants. Each variant's feature vector passes through TabPFN's predict_probability() — a single forward pass (~500ms) returns P(success). Any variant below P(success) < 0.55 is discarded before backtesting. | Filters ~70% of hypotheses without running costly backtests |
| **3. Embedding-Backed Mutation** | Past successful hypotheses (stored as embeddings in ChromaDB) anchor new mutations via cosine similarity. TabPFN's attention patterns reveal which historical conditions were most informative. | LLM generates hypotheses "adjacent" to proven ones rather than random |
| **4. Post-Validation** | After backtest, TabPFN validates the final signal with full feature table + climate vector. | Calibrated probability for scoring |

### 1.4 How Toto-2 Steers Hypothesis Generation

Toto-2 runs before each research iteration (or cached, refreshed every 5 min). Its output is injected as system context into the LLM hypothesis generator:

| Toto-2 Output | Steering Effect |
|---------------|-----------------|
| **regime** (volatile/trending/ranging/calm) | LLM filters out regime-incompatible strategies (e.g., no mean-reversion in trending regimes) |
| **volatility_surface** (short/med/long vol) | Sets parameter bounds: high short-term vol → tight thresholds, fast mean-reversion; low vol → wide thresholds, trend-following |
| **anomalies** (odds/volume z-scores ≥ 2.5) | Seeds specific hypotheses: "Market X had odds Z-score 3.2 at timestamp T. Hypothesis: trade reversion after odds anomalies > 2.5σ" |
| **direction_strength + autocorrelation** | If direction > 0.4 and autocorr > 0.3 → momentum hypotheses. If near-zero → mean-reversion hypotheses |

### 1.5 How RLM Integrates (Three Modes)

| Mode | Trigger | What It Does |
|------|---------|-------------|
| **Cron-based** | Every N hours | Scans configured data sources (forums, news, PDF archives) for new alpha vectors. Stores discovered patterns in ChromaDB. Watches for linguistic change-points. |
| **On-demand** | Manual trigger per research session | User specifies a target market, strategy, or hypothesis space. RLM recursively mines relevant unstructured data for that specific domain. |
| **Embedded** | Spawned by pi-autoresearch mid-loop | During hypothesis generation, if the LLM decides it needs qualitative data (e.g., "check social sentiment on this candidate"), it spawns RLM as a sub-skill to mine relevant sources and return structured alpha factors. |

---

## 2. Data Models

### 2.1 ResearchSession

```python
class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: str  # UUID
    user_id: str  # FK to users
    status: str  # running | paused | completed | failed
    mode: str  # manual | cron | continuous
    strategy_id: str | None  # FK — which strategy is being optimized
    trigger_type: str | None  # cron | manual | watchdog
    composite_preset: str  # sharpe_max | win_rate_max | risk_adjusted
    current_iteration: int
    total_kept: int
    avg_sharpe: float
    avg_win_rate: float
    best_sharpe: float
    best_win_rate: float
    rlm_alpha_vector_id: str | None  # FK to alpha vector used
    toto2_regime: str | None  # cached at session start
    toto2_volatility: float | None
    tabpfn_top_features: dict | None  # cached at session start
    hypothesis_count: int
    created_at: datetime
    updated_at: datetime
```

### 2.2 ExperimentResult

```python
class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    id: str  # UUID
    session_id: str  # FK to research_sessions
    iteration: int
    hypothesis: str  # LLM-generated description
    hypothesis_prompt: str  # Full prompt that generated it
    regime_at_time: str
    volatility_at_time: float
    feature_importance_at_time: dict
    rlm_alpha_vector_snapshot: dict | None  # what RLM contributed to this hypothesis
    backtest_config: dict  # strategy parameters used
    backtest_trades: int
    backtest_win_rate: float
    backtest_sharpe: float
    backtest_max_drawdown: float
    backtest_total_pnl: float
    tabpfn_probability: float
    tabpfn_confidence: float
    composite_score: float
    verdict: str  # KEPT | WARN | REVERTED
    git_commit_hash: str | None
    created_at: datetime
```

### 2.3 RLMAlphaVector

```python
class RLMAlphaVector(Base):
    __tablename__ = "rlm_alpha_vectors"
    id: str  # UUID
    source_type: str  # forum | audit | news | social | transcript | pdf_archive
    source_path: str  # file path or URL of source data
    source_hash: str  # content hash for dedup
    token_count: int  # approximate tokens processed
    alpha_vector: dict  # structured JSON output
    linguistic_signals: dict | None  # change-point detections, semantic drift
    sub_agent_traces: list | None  # trajectory inspection logs
    dspy_trajectory: str | None  # inspect_history() output
    used_in_sessions: int  # counter
    created_at: datetime
```

### 2.4 ResearchSessionConfig (per user)

```python
class ResearchSessionConfig(Base):
    __tablename__ = "research_session_configs"
    id: str  # UUID
    user_id: str  # FK, unique
    max_concurrent: int  # default 2
    composite_preset: str  # default "sharpe_max"
    cron_enabled: bool  # default False
    cron_interval_minutes: int  # default 360 (6 hours)
    continuous_enabled: bool  # default False
    rlm_sources: list[str]  # which data sources to scan
    rlm_cron_enabled: bool  # default False
    rlm_cron_interval_minutes: int  # default 1440 (24 hours)
    max_hypotheses_per_session: int  # default 50
    created_at: datetime
    updated_at: datetime
```

---

## 3. Service Architecture

### 3.1 New Files

```
backend/app/
├── ai/
│   ├── rlm_service.py          # NEW
│   └── autoresearch.py         # NEW — the pi-autoresearch loop
├── routers/
│   ├── research.py             # NEW — API endpoints
│   └── research_ws.py          # NEW — WebSocket handler
├── services/
│   └── research_scheduler.py   # NEW — loop lifecycle manager
├── models/
│   ├── research_session.py     # NEW
│   ├── experiment_result.py    # NEW
│   ├── rlm_alpha_vector.py     # NEW
│   └── research_config.py      # NEW
```

### 3.2 RLMService (`backend/app/ai/rlm_service.py`)

```python
class RLMService:
    """
    Wraps dspy.RLM for recursive deep archive mining.
    
    Three modes:
      - scan_directory: Recursive file traversal over archives
      - scan_text_batch: Programmatic search over loaded text corpus
      - detect_drift: Linguistic change-point detection on time-series text
    
    Uses dspy.RLM signatures, sub_lm parameter for cost-efficient
    recursion (cheap model for scanning, frontier for synthesis),
    and trajectory inspection for white-box debugging.
    """

    async def scan_directory(
        self,
        directory: str,
        keywords: list[str],
        file_pattern: str = "*.pdf|*.txt|*.json",
        max_tokens: int = 1_000_000,
        sub_lm: str = "gpt-4o-mini",  # cheap model for recursion
    ) -> RLMAlphaVector
        # 1. Recursive path traversal — RLM writes Python in REPL
        # 2. Content extraction per file
        # 3. Sub-agent spawning for files > 50 pages
        # 4. Keyword filtering + semantic scoring
        # 5. Aggregation into structured alpha vector
        # 6. SUBMIT() call to return result

    async def scan_text_batch(
        self,
        texts: list[str],
        query: str,
        sub_lm: str = "gpt-4o-mini",
    ) -> RLMAlphaVector
        # 1. Metadata peek: print(context[:1000])
        # 2. Programmatic search: writes Python filter
        # 3. Recursive analysis: calls llm_query on matches
        # 4. State accumulation into alpha_v1
        # 5. SUBMIT(alpha_v1)

    async def detect_linguistic_drift(
        self,
        texts_historical: list[str],
        texts_recent: list[str],
        target_entities: list[str],
    ) -> dict
        # 1. Compare sentiment vectors per entity
        # 2. Detect semantic shift (proximity search deltas)
        # 3. Return drift scores per entity

    async def spawn_sub_agent(
        self,
        document: str,
        instruction: str,
    ) -> str
        # 1. Split document into chunks
        # 2. Spawn child RLM with instruction
        # 3. Collect and return focused extraction

    def inspect_last_trajectory(self) -> str
        # Delegates to dspy.RLM's inspect_history()
        # Returns exact Python code RLM wrote
```

### 3.3 AutoresearchService (`backend/app/ai/autoresearch.py`)

```python
class AutoresearchService:
    """
    The pi-autoresearch experiment loop.
    
    Orchestrates one complete iteration:
      hypothesis → quick rejection → backtest → TabPFN validation → score → keep/revert
    
    Each iteration is stateless (all state in DB) so the loop
    survives server restarts — sessions auto-resume.
    """

    async def run_iteration(
        self,
        session: ResearchSession,
        strategy_id: str,
        market_history: list[dict],
        climate: dict,           # from Toto-2
        feature_importance: dict, # from TabPFN
        alpha_vector: dict | None, # from RLM (optional)
    ) -> ExperimentResult

    async def _generate_hypotheses(
        self,
        climate: dict,
        feature_importance: dict,
        alpha_vector: dict | None,
        past_results: list[ExperimentResult],
        n: int = 5,
    ) -> list[dict]
        # Build prompt with:
        #   - Toto-2 regime context (regime appropriateness filter)
        #   - TabPFN top features (topic selection)
        #   - RLM alpha vector (qualitative signals)
        #   - Past successful hypotheses from ChromaDB (mutation anchors)
        #   - Past failures (avoidance constraints)
        # LLM returns N hypothesis configs

    async def _quick_rejection(
        self,
        hypotheses: list[dict],
        market_snapshot: pd.DataFrame,
    ) -> list[dict]
        # For each hypothesis, build feature vector
        # Pass through TabPFN predict_probability()
        # Filter out any with P(success) < 0.55

    async def _compute_composite_score(
        self,
        backtest_result: BacktestResult,
        tabpfn_result: dict,
        preset: str,
    ) -> float
        # sharpe_max: 0.7 * sharpe + 0.3 * tabpfn_probability
        # win_rate_max: 0.7 * win_rate + 0.3 * tabpfn_probability
        # risk_adjusted: 0.4 * sharpe + 0.3 * (1 - max_dd) + 0.3 * tabpfn_probability
```

### 3.4 ResearchScheduler (`backend/app/services/research_scheduler.py`)

```python
class ResearchScheduler:
    """
    Manages the lifecycle of research sessions.
    
    - Spawns/resumes sessions as asyncio background tasks
    - Enforces per-user and global concurrency limits
    - Handles cron triggers, manual triggers, continuous mode
    - Exposes session state via WebSocket
    - Auto-resumes interrupted sessions on server start
    """

    _sessions: dict[str, asyncio.Task]
    _user_locks: dict[str, asyncio.Semaphore]
    _global_lock: asyncio.Semaphore

    async def start_session(self, user_id: str, config: dict) -> ResearchSession
        # Create session in DB
        # Acquire concurrency slot
        # Launch asyncio task running loop

    async def stop_session(self, session_id: str) -> None
        # Cancel asyncio task
        # Update DB status to paused/completed

    async def _session_loop(self, session: ResearchSession) -> None
        # 1. Load strategy + market history
        # 2. Fetch Toto-2 climate
        # 3. Fetch TabPFN feature importance
        # 4. Check for fresh RLM alpha vectors
        # 5. Run iteration via AutoresearchService
        # 6. Update DB
        # 7. Broadcast via WebSocket
        # 8. Sleep (configurable cooldown)
        # 9. Repeat until stopped or hypothesis limit hit

    async def _cron_worker(self) -> None
        # Check all users with cron_enabled
        # Launch sessions if cooldown elapsed

    async def resume_interrupted_sessions(self) -> None
        # On startup, find sessions with status=running
        # Resume each as asyncio task
```

---

## 4. API Endpoints

### 4.1 REST Endpoints

| Method | Path | Purpose |
|--------|------|--------|
| `POST` | `/api/research/run` | Trigger one iteration |
| `POST` | `/api/research/run-continuous` | Start continuous self-improvement loop |
| `POST` | `/api/research/stop` | Stop running session |
| `POST` | `/api/research/sessions` | Create new research session |
| `GET` | `/api/research/sessions` | List user's sessions |
| `GET` | `/api/research/sessions/{id}` | Session detail |
| `GET` | `/api/research/sessions/{id}/results` | All results for a session |
| `GET` | `/api/research/stats` | Aggregate stats across all sessions |
| `PUT` | `/api/research/config` | Update per-user config |
| `GET` | `/api/research/config` | Get per-user config |
| `GET` | `/api/research/climate` | Current Toto-2 regime + volatility |
| `GET` | `/api/research/features` | Current TabPFN feature importance ranking |
| `GET` | `/api/research/alpha-vectors` | List recent RLM alpha vectors |
| `POST` | `/api/research/rlm-scan` | Trigger on-demand RLM scan |

### 4.2 WebSocket Endpoint

Channel: `ws://host/ws/research/{session_id}`

Incoming: `{ "type": "pause" | "resume" | "stop" }`

Outgoing messages:
```json
{"type": "session_started", "session_id": "...", "total_iterations": 0}

{"type": "hypothesis", "session_id": "...", "iteration": 12,
 "hypothesis": "volume_momentum_breakout",
 "climate": {"regime": "trending", "volatility": 0.042},
 "features": ["volume_momentum_3h", "odds_acceleration"]}

{"type": "quick_rejection", "session_id": "...", "iteration": 12,
 "hypotheses_proposed": 5, "hypotheses_survived": 2,
 "rejected_reasons": ["P(success)=0.42", "P(success)=0.38", "P(success)=0.51"]}

{"type": "backtest_progress", "session_id": "...", "iteration": 12,
 "percent": 45, "current_step": 450, "total_steps": 1000}

{"type": "tabpfn_result", "session_id": "...", "iteration": 12,
 "probability": 0.73, "confidence": 0.68, "edge": 0.11,
 "feature_importance": {"volume_momentum": 0.38, "odds_acceleration": 0.29}}

{"type": "iteration_complete", "session_id": "...", "iteration": 12,
 "hypothesis": "volume_momentum_breakout",
 "score": 1.82, "sharpe": 1.82, "win_rate": 0.62,
 "max_drawdown": 0.08, "verdict": "KEPT",
 "git_hash": "abc123def"}

{"type": "session_summary", "session_id": "...",
 "total_iterations": 50, "kept": 31, "reverted": 19,
 "avg_sharpe": 1.64, "avg_win_rate": 0.58, "best_sharpe": 2.41}

{"type": "rlm_scan_complete", "alpha_vector_id": "...",
 "source": "polymarket_forum", "alpha_factors_found": 3}

{"type": "error", "message": "..."}
```

---

## 5. ExperimentDashboard UI

New route: `/analytics/research`

### 5.1 Components

```
ResearchPage.tsx           — Main page orchestrator
├── ResearchStatsBar       — Total iterations, kept %, avg Sharpe, best Sharpe
├── ResearchControls       — Run now, Continuous toggle, Cron config, Stop
├── QueuePanel             — Per-user queue (active + pending sessions)
├── ActiveSessionPanel     — Current iteration details
│   ├── HypothesisCard     — Current hypothesis + climate context
│   ├── ProgressBar        — Backtest progress with stage labels
│   ├── TabPFNResultCard   — Probability, confidence, edge, feature importance
│   └── VerdictBadge       — KEPT / WARN / REVERTED with color
├── IterationHistoryTable  — Paginated table of past iterations
│   Columns: #, Hypothesis, Regime, Score, Sharpe, Verdict, Git Hash
│   Sortable, filterable by verdict and regime
├── StrategyEvolutionChart — Line chart of Sharpe ratio over iterations
│   Annotated with regime changes (colored bands)
└── RLMAlphaPanel          — Recent alpha vectors from RLM scans
    ├── AlphaVectorCard    — Source, token count, factors found
    └── TriggerButton      — "Run RLM Scan Now"
```

### 5.2 Zustand Store (Research Store)

```typescript
interface ResearchStore {
  activeSession: ResearchSession | null
  currentIteration: ExperimentResult | null
  history: ExperimentResult[]
  stats: ResearchStats
  climate: ClimateData | null
  features: Record<string, number> | null
  rlmAlphaVectors: RLMAlphaVector[]
  wsConnected: boolean

  // Actions
  startSession: (config: StartConfig) => Promise<void>
  stopSession: () => Promise<void>
  updateConfig: (config: Partial<SessionConfig>) => Promise<void>
  triggerRlmScan: (source: string) => Promise<void>
}
```

---

## 6. Concurrency & Resource Limits

| Limit | Value | Enforced By |
|-------|-------|-------------|
| Per-user concurrent sessions | 2 | `asyncio.Semaphore(user_id)` in ResearchScheduler |
| Global concurrent sessions | 5 | `asyncio.Semaphore()` in ResearchScheduler |
| Max hypotheses per session | 50 | ResearchSessionConfig |
| Backtest data window | 90 days by default | AutoresearchService config |
| Toto-2 cache TTL | 5 minutes | AutoresearchService |
| TabPFN feature importance cache TTL | 10 minutes | AutoresearchService |
| RLM scan concurrency | 1 per user | ResearchScheduler |

---

## 7. DB Schema Changes

New tables (via Alembic migration):
- `research_sessions` — one row per session
- `experiment_results` — one row per iteration
- `rlm_alpha_vectors` — one row per RLM scan result
- `research_session_configs` — one row per user preferences

Existing tables used:
- `strategies` — linked via `strategy_id`
- `users` — linked via `user_id`

---

## 8. Implementation Order

### Step 1: Data Models + Migration
- Create SQLAlchemy models for all 4 new tables
- Create Alembic migration
- Add models to `backend/app/models/`

### Step 2: RLMService
- Create `backend/app/ai/rlm_service.py`
- Wrap `dspy.RLM` for the three modes
- Implement `sub_lm` parameter for cost-efficient recursion
- Handle graceful fallback when dspy is not installed

### Step 3: AutoresearchService
- Create `backend/app/ai/autoresearch.py`
- Implement the full iteration loop
- TabPFN quick rejection filter
- Composite scoring with three presets

### Step 4: ResearchScheduler
- Create `backend/app/services/research_scheduler.py`
- Background task lifecycle management
- Concurrency semaphores
- Cron worker
- Auto-resume on startup

### Step 5: API Endpoints
- Create `backend/app/routers/research.py`
- All REST endpoints
- WebSocket endpoint in `research_ws.py` or inline

### Step 6: Frontend Dashboard
- ResearchPage with all sub-components
- Zustand store
- WebSocket hook for research channel

### Step 7: Tests
- Unit tests for RLMService (mocked dspy)
- Unit tests for AutoresearchService (mocked TabPFN, Toto-2, Backtester)
- Integration tests for ResearchScheduler
- API endpoint tests

---

## 9. Key Runtime Behaviors

### Session Resumption
- Sessions with `status=running` at server start are auto-resumed
- Scheduler loads the last incomplete iteration from DB
- Continues from where it stopped (no data loss)

### Concurrency Backoff
- When concurrency limit is hit, the request is queued
- Queue order is FIFO per user
- WebSocket notifies when session moves from queued → running

### Error Handling
- Backtest failure → retry once, then skip hypothesis
- TabPFN failure → hypothesis proceeds without quick rejection
- RLM failure → hypothesis generation proceeds without alpha vector data
- Service restart → active sessions auto-resume within 30s

### Git Integration
- KEPT hypotheses commit strategy config to a research branch
- REVERTED hypotheses trigger `git revert` on the branch
- Each commit hash is stored in ExperimentResult
- Format: `research/{session_id}/{iteration}_{hypothesis_slug}`
