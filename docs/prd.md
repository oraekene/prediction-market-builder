# PRD: Prediction Market Strategy Builder

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** Draft  

---

## Part 1: Executive Overview

### 1.1 Product Vision

A web-based prediction market terminal and strategy builder that allows users to discover, analyze, and trade prediction markets across Polymarket, Kalshi, and Drift through a hybrid chat+node interface. The platform combines institutional-grade AI/ML analysis (TabPFN, Toto-2, Hermes-Agent, RLM) with a simple, accessible UX — the "Robinhood of prediction markets."

### 1.2 Core Differentiators

- **Hybrid chat+node interface**: Beginners start with natural language chat; advanced users graduate to visual node-based strategy building
- **Zero-shot Bayesian inference** (TabPFN): Training-free, instant predictions without model tuning
- **Self-improving system**: Hermes-Agent + pi-autoresearch + RLM continuously discovers and validates new alpha factors
- **Full strategy expressiveness**: Users can construct ANY possible strategy with no artificial limits
- **Local-first, cloud-reasoning architecture**: Minimizes infrastructure costs while maximizing AI capability

### 1.3 Target Market

- **Primary**: Prediction market traders on Polymarket, Kalshi, Drift
- **Secondary**: Retail users interested in event-driven trading
- **Not targeting**: Crypto spot/futures traders, sports bettors (future expansion)

### 1.4 Platform Constraints

**Current (v1):** Web application only, hosted on Oracle Cloud + Postgres + Cloudflare

**Future allowance (post-v1):**
- WhatsApp trading bot
- Social media DM bots (TikTok DMs, Instagram DMs, Twitter/X DMs)
- Chrome extension (injects UI components into Polymarket/Kalshi web interfaces and social media platforms)

---

## Part 2: System Architecture

### 2.1 Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: USER INTERFACE                                         │
│  React + TypeScript | Vite | Shadcn/UI + Tailwind                │
│  TanStack Query + Zustand | Zod | React Flow | Recharts          │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: ORCHESTRATION (Hermes-Agent)                           │
│  State Machine | Memory System | Skill Creation                  │
│  Tool Registration | Sub-agent Spawning | Code Synthesis         │
│  Watchdog Triggers | Self-Correction Loop | Git Integration      │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: RESEARCH & ANALYSIS                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ TabPFN   │  │ Toto-2   │  │  RLM     │  │ pi-autoresearch│   │
│  │Bayesian  │  │Time Series│  │Recursive │  │ Hypothesis    │   │
│  │Inference │  │Forecast   │  │ Mining   │  │ Engine        │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: STRATEGY ENGINE                                        │
│  Node-Based Builder | Chat-to-Strategy | Backtester              │
│  Paper Trading | Risk Manager | Execution Dispatcher             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: DATA & INFRASTRUCTURE                                  │
│  LanceDB | DuckDB | ChromaDB | FastAPI | Sentence-Transformers   │
│  Puppeteer | ONNX Runtime | Oracle + Postgres | Cloudflare       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer 1: User Interface

| Component | Technology |
|---|---|
| UI Framework | React + TypeScript |
| Build Tool | Vite |
| Component Library | Shadcn/UI + Tailwind CSS (Radix primitives) |
| State Management | TanStack Query (server) + Zustand (UI/global) |
| Validation | Zod (schema-driven UI generation) |
| Node Canvas | React Flow |
| Charting | Lightweight Charts (TradingView-compatible) or Recharts |
| Real-time | WebSocket + Server-Sent Events |

**Interface Modes:**

1. **Chat Mode (Guided):** Sequential wizard for beginners. Natural language input. Progressive disclosure of complexity. Ideal for: simple strategy creation, market discovery, one-off trades, "what if" analysis.

2. **Chat Mode (Freeform):** Command-based for advanced users. Slash commands, inline parameters. Ideal for: power users who know what they want, quick actions.

3. **Node Canvas Mode:** Visual node-based strategy builder. Drag-and-drop, visual data flow, real-time validation. Ideal for: complex multi-condition strategies, debugging, visual understanding of strategy logic.

4. **Terminal Dashboard Mode:** Data aggregation view. Multi-market monitoring, real-time odds comparison, order book visualization, portfolio tracking.

### 2.3 Layer 2: Orchestration (Hermes-Agent)

Hermes-Agent is the executive brain and skeleton of the platform. Full capabilities:

| Capability | Description |
|---|---|
| **State Machine Management** | Initializes goals, tracks progress, manages task decomposition, handles state transitions |
| **Memory System** | ChromaDB vector store for long-term/short-term memory. Stores successes, failures, pattern recognition |
| **Automatic Skill Creation** | Writes Python classes on-the-fly, containers them, tests them, registers as new tools dynamically |
| **Tool Calling & Registration** | Discoverable tool registry. Self-healing when APIs change |
| **Self-Correction Loop** | Catches errors in generated code, fixes logic, retries execution |
| **Cognitive Goal Setting** | Sets quantitative targets (Target_RR, Min_Win_Rate), tracks progress in PRD.json |
| **Multi-Modal Scraping** | Uses agentic search pipeline (SearXNG → Scrapling → Camoufox/Playwright → LLM) to extract data from web, social media, court filings, satellite sources |
| **Git Integration** | Commits winning strategies to execution repo, rolls back failures via Git |
| **Feedback Loop** | Analyzes strategy failures, updates memory, creates new filters to prevent recurrence |
| **Sub-agent Spawning** | Delegates research to pi-autoresearch, analysis to TabPFN, climate to Toto-2 |
| **Cross-Domain Alchemy** | Finds novel connections across disparate domains (e.g., legal filings + on-chain data) |
| **REPL-based Execution** | Writes and runs Python code in sandboxed REPL for on-the-fly analysis |
| **Watchdog Triggers** | Monitors conditions (volatility thresholds, news events) and initiates downstream phases |

### 2.4 Layer 3: Research & Analysis

#### TabPFN (Bayesian Inference Engine)
- **Role:** Zero-shot classification and regression for tabular data
- **Key capability:** Training-free inference. No model tuning needed. Feed data, get instant Bayesian posterior probabilities
- **Versions:** TabPFN-2.5/2.6 (supports 50K samples, 2K features)
- **Extensions:** TabPFN-TS (time series recast as tabular), Distillation Engine (heavy model → lightweight MLP/tree for production)
- **Use cases:** Signal validation, regime detection, meta-labeling, calibrated probability estimation, feature importance ranking

#### Toto-2 (Time Series Foundation Model)
- **Role:** Macro-environmental analysis and infrastructure observability
- **Key capability:** Datadog-built 2.5B parameter model trained on trillions of observability data points. Multivariate attention, patch-based forecasting, exogenous covariate steering
- **Use cases:** Volatility forecasting, network congestion prediction (gas fees, mempool), macro-regime classification, anomaly detection, system health monitoring

#### RLM via DSPy (Recursive Language Model)
- **Role:** Deep unstructured data mining at scale
- **Key capability:** Recursive Python REPL exploration of massive archives (1M+ tokens). Programmatic search, sub-agent spawning, linguistic change-point detection
- **Use cases:** Narrative mining, legislative history analysis, social sentiment deep-dive, quantitative research expansion for pi-autoresearch

#### pi-autoresearch (Hypothesis Engine)
- **Role:** Automated scientific discovery loop
- **Key capability:** Writes and tests strategy hypotheses autonomously. Git-based experiment tracking. Multi-objective optimization (NSGA-II), genetic programming, Monte Carlo simulation
- **RLM integration:** Every pi-autoresearch task runs with RLM to expand its relevant capabilities — RLM is the "deep librarian" that surfaces structured alpha vectors from chaos, which pi-autoresearch then validates

### 2.5 Layer 4: Strategy Engine

- **Node-based strategy builder** using React Flow
- **Chat-to-strategy conversion** (natural language → node graph)
- **Backtester** with walk-forward analysis
- **Paper trading / demo mode**
- **Risk Manager** (full strategy template system, not just Kelly Criterion)
- **Execution dispatcher** (routes orders to Polymarket/Kalshi/Drift APIs)

### 2.6 Layer 5: Data & Infrastructure

| Component | Technology | Rationale |
|---|---|---|
| Vector Database | LanceDB (primary) + FAISS (lightweight) | Disk-native, zero-copy Arrow, low RAM, scales without memory constraints |
| Analytics SQL | DuckDB | OLAP powerhouse, columnar, Parquet compression, SQL-first for metadata filtering |
| Embeddings | sentence-transformers + all-MiniLM-L6-v2 | CPU-friendly, ~80MB, local inference, free. NOT replaceable by LLM API — embeddings run on every vector search (market discovery, memory recall, pattern matching). At thousands of calls/day, an API would cost ~$0.10/day + 50ms latency vs $0 + 1ms locally. This model is too small (80MB) for GPU to be beneficial — runs on CPU as FastAPI microservice |
| Re-ranker | jina-reranker-v1-tiny-en | Sub-40MB, boosts search quality. Re-ranks top-50 vector results by cross-encoder scoring. Running this via LLM API would be ~500x more expensive (50 separate LLM calls per search). Lightweight enough for CPU inference as FastAPI microservice |
| Agent Memory | ChromaDB | Purpose-built for agent memory, Hermes-Agent compatible |
| API Framework | FastAPI (Python) | Async-native, strong for AI pipelines |
| Agentic Search — Discovery | SearXNG | Metasearch across 240+ engines. Avoids rate limits |
| Agentic Search — Fast Parse | Scrapling | Lightweight static HTML DOM check. Gatekeeper before heavy tools |
| Agentic Search — Stealth Browser | Camoufox (via Playwright) | Hardened Firefox fork defeating Cloudflare/DataDome |
| Agentic Search — DOM Extraction | Playwright (`accessibility.snapshot()`) | 50K-line HTML → ~100 line Accessibility Tree for LLM |
| Agentic Search — Intelligence | LLM API (Claude/Gemini) | Interprets page content, extracts structured data |
| Local AI — Embeddings | ONNX Runtime | sentence-transformers, re-rankers — ONNX-native models |
| Local AI — LLMs | llama.cpp (GGUF, GPU-offloaded) | Reserved for future use (custom fine-tuned models, batch processing, offline operation). Not needed in v1 |
| Graph Analysis | DuckPGQ (DuckDB extension) | Turn DuckDB into graph DB for knowledge graph traversal |
| GPU Inference | Serverless GPU (RunPod, Banana, Replicate) | TabPFN / Toto-2 GPU-accelerated forward passes. llama.cpp GPU offloading |
| Cloud Hosting | Oracle Cloud (compute) + Postgres + Cloudflare (CDN) | Primary infrastructure |
| Object Storage | Cloudflare R2 (future) | Not needed at v1 scale — all data (Postgres, LanceDB, DuckDB, ChromaDB) fits on Oracle instance's attached storage. R2 needed later for multi-instance shared data, TB-scale archives, cross-region backups |

#### DuckDB vs LanceDB: Why Both Are Needed

These databases solve orthogonal problems and are used in a handover pattern:

| | DuckDB | LanceDB |
|---|---|---|
| **Type** | OLAP SQL engine (columnar) | Vector similarity search (disk-native) |
| **Data it handles** | Structured metadata: market IDs, timestamps, platforms, categories, odds, volume, user accounts, trade history | Embedding vectors: market descriptions, agent memories, news articles, social media posts |
| **Query type** | Precise SQL: *"markets where volume > $1M AND category = 'politics' AND close_time < next_week"* | Semantic: *"find markets similar to this one"* or *"recall past strategies that performed well in high-volatility regimes"* |
| **The Handover Pattern** | DuckDB narrows 1M markets → 5K candidates using precise SQL filters → passes their IDs to LanceDB | LanceDB ranks those 5K candidates by vector similarity → returns top 10 semantically relevant results |

**Concrete example — user searches for "election betting":**
1. **DuckDB**: `SELECT id FROM markets WHERE category IN ('politics', 'elections') AND volume > 50000 AND status = 'open'` → returns 3,412 market IDs (200ms)
2. **LanceDB**: Takes those 3,412 IDs + the embedding of "election betting" → ranks by cosine similarity → returns top 20 (50ms)
3. Combined result: markets that are BOTH politically relevant AND semantically about elections

Without DuckDB, LanceDB would need to scan and score millions of markets against the query vector — slow and noisy. Without LanceDB, DuckDB can only give you back what SQL can express (it can't understand that "election betting" means more than just the "politics" category).

---

## Part 3: Functional Requirements — Complete Node Catalog

Every node in the system, organized by category.

### 3.1 Source Nodes (Data Ingress)

| # | Node | Description | Input | Output |
|---|---|---|---|---|
| 1 | Polymarket Data | Real-time odds, volume, liquidity, order book from Polymarket | Market filter params | Structured market data |
| 2 | Kalshi Data | Real-time odds, volume from Kalshi | Market filter params | Structured market data |
| 3 | Drift Data | Real-time odds, volume from Drift | Market filter params | Structured market data |
| 4 | General Web Search | Web search via API (Google/Bing/DuckDuckGo) | Query string | Search results (titles, snippets, URLs) |
| 5 | Social Media Search | Keyword/semantic search across Twitter/X, Reddit, Discord, Telegram | Query, platforms, time range | Posts, engagement metrics, sentiment |
| 6 | News Aggregator | RSS/API-based news feed from specified sources | Topics, sources, date range | News articles with metadata |
| 7 | On-Chain Data | Mempool congestion, exchange inflows/outflows, wallet clustering | Chain, protocol, token | Blockchain metrics |
| 8 | Alternative Data | Agentic search pipeline (SearXNG → Scrapling → Camoufox/Playwright → LLM) for satellite imagery, shipping data, flight tracking, port congestion, social media mining, forum scraping | Target entity, data type | Structured alternative data |
| 9 | Legal/Regulatory | PACER filings, SEC EDGAR, court dockets, regulatory announcements | Case number, entity, filing type | Legal documents, metadata |
| 10 | Macro-Economic | CPI, PPI, DXY, treasury yields, employment data, oil prices | Indicators, timeframe | Economic time series |
| 11 | Odds Comparison | Multi-bookmaker odds aggregation | Markets, platforms | Unified odds table with best-price highlighting |
| 12 | Custom Data Source | User-defined API or data feed | URL, auth, schema definition | User-specified data structure |

### 3.2 Filter Nodes

| # | Node | Description |
|---|---|---|
| 13 | TabPFN Signal Check | Zero-shot Bayesian validation of entry/exit signals |
| 14 | Toto-2 Climate Filter | Macro-environmental regime check (is market stable enough for strategy?) |
| 15 | Toto-2 Anomaly Detection | VAE-based anomaly detection on order flow imbalance |
| 16 | Toto-2 Volatility Surface | Forecast volatility regime for the next N intervals |
| 17 | Hermes Execution Check | Gas fees, latency, slippage — is execution feasible? |
| 18 | pi-autoresearch Validator | Cross-checks proposed signal against discovered alpha factors |
| 19 | Semantic Sentiment | Legal-BERT or sentiment model scoring of text input |
| 20 | RLM Change-Point | Detects linguistic/semantic drift in time-series text data |
| 21 | KDE Filter | Kernel Density Estimation — finds distribution patterns in data |
| 22 | Granger Causality | Tests if one time series predicts another |
| 23 | DTW Divergence | Dynamic Time Warping — detects divergence between expected and actual odds movement |
| 24 | SHAP Feature Importance | Model-agnostic feature attribution for TabPFN predictions |

### 3.3 Condition Nodes

| # | Node | Description |
|---|---|---|
| 25 | Threshold | Greater than, less than, equal to, between |
| 26 | Time-Based | Schedule, delay, time window, expiry-aware |
| 27 | Combination Logic | AND, OR, NOT, XOR (multiple input branches) |
| 28 | Branch | If/elseif/else — multi-way conditional routing |
| 29 | RLM Semantic Match | Pattern matches against recursive text analysis output |

### 3.4 Action Nodes

| # | Node | Description |
|---|---|---|
| 30 | Place Bet | Execute market/limit order on connected platform |
| 31 | Send Alert | Push notification, email, webhook, Telegram |
| 32 | Forward Info | Route data to destination with format transformation |
| 33 | Create/Modify Strategy | Edit strategy dynamically based on conditions |
| 34 | Execute Liquidation | Trigger liquidation logic on DeFi protocol |
| 35 | Deploy to Paper Trading | Run strategy in simulation mode |
| 36 | Commit to Git | Persist strategy code to strategy repository |
| 37 | Webhook Call | HTTP request to external endpoint |
| 38 | Custom Script | User-defined Python/JavaScript execution |

### 3.5 Risk Management Nodes

| # | Node | Description |
|---|---|---|
| 39 | Kelly Criterion | Bankroll-optimized bet sizing (preset using TabPFN calibrated probabilities) |
| 40 | Dynamic Position Sizer | Adjusts position size based on portfolio volatility, drawdown state, conviction |
| 41 | Drawdown Protector | Caps cumulative loss, forced pause at threshold |
| 42 | Portfolio Rebalancer | Rebalances across strategies to maintain risk allocation |
| 43 | Correlation Hedger | Opens hedge positions when correlation between active strategies exceeds threshold |
| 44 | VaR Calculator | Value-at-Risk from TabPFN quantile regression (distributional output) |
| 45 | Expected Shortfall | Conditional VaR for tail-risk events |
| 46 | Stop-Loss / Take-Profit | Automated exit at predefined P&L levels |
| 47 | User Risk Strategy Template | Full strategy-builder integration — risk management as a first-class strategy |

Risk Manager is a full strategy template system, not just preset calculators. Kelly Criterion is ONE pre-built preset that users can quickly choose. Users can build arbitrary risk strategies using all the same mechanisms available for trading strategies — any condition, any filter, any action, combined with risk-specific primitives (drawdown limits, position sizing algorithms, portfolio-level constraints).

### 3.6 Analysis Nodes

| # | Node | Description |
|---|---|---|
| 48 | TabPFN Bayesian Inference | Zero-shot classification/regression. Input: feature table. Output: calibrated probability distribution |
| 49 | TabPFN-TS Forecast | Time series forecasting via TabPFN recast as tabular regression |
| 50 | TabPFN Feature Alchemist | Extract internal embeddings from TabPFN as high-signal features for downstream models |
| 51 | TabPFN Distillation | Export TabPFN logic to lightweight MLP or gradient-boosted tree for production |
| 52 | TabPFN Quantile Regression | Distributional forecasts (τ=0.1, 0.5, 0.9) for VaR and expected shortfall |
| 53 | SHAP Explainability | Feature attribution report for every TabPFN inference |
| 54 | pi-autoresearch Hypothesis | Propose new alpha factor based on discovered correlations |
| 55 | RLM Deep Archive Miner | Recursive scan of massive unstructured archives for signal |
| 56 | RLM Sub-Agent | Spawn recursive sub-agent for deep-dive analysis on specific subset |
| 57 | Genetic Programming | Evolve predictive score functions from base features |
| 58 | Multi-Objective Optimization | NSGA-II algorithm — optimizes multiple competing objectives (profit, drawdown, Sharpe) |
| 59 | Monte Carlo Simulation | 10K+ iteration simulation for strategy robustness testing |
| 60 | Cross-Correlation | CCF analysis to find lead-lag relationships between assets/markets |
| 61 | Bayesian Optimization | Hyperparameter-free optimization for strategy parameters |
| 62 | Walk-Forward Analysis | Rolling window validation across market regimes |
| 63 | Meta-Labeling | Primary signal → TabPFN validates probability of signal success given current regime |

### 3.7 Execution Nodes

| # | Node | Description |
|---|---|---|
| 64 | Rust Execution Bridge | High-performance order routing via ethers-rs or rust-based SDK |
| 65 | Smart Contract Interaction | Direct DeFi protocol interaction (Aave, Morpho, etc.) |
| 66 | Order Router | Route to CEX or DEX based on liquidity, fees, and speed |
| 67 | Slippage Calculator | Estimated price impact for order size on target platform |
| 68 | Gas Fee Optimizer | Toto-2 powered gas price forecast for optimal transaction timing |
| 69 | Multi-Platform Dispatcher | Simultaneous order routing to Polymarket, Kalshi, Drift |

### 3.8 Memory & Persistence Nodes

| # | Node | Description |
|---|---|---|
| 70 | Vector Store Query | Semantic search of ChromaDB for relevant past patterns |
| 71 | Memory Write | Persist outcome (success/failure) to agent memory |
| 72 | Memory Recall | Retrieve similar historical situations with outcomes |
| 73 | Git Branch Manager | Create, switch, merge strategy branches |
| 74 | Strategy Template | Save, load, and share strategy configurations |

---

## Part 4: Data Flows

### 4.1 Hierarchical Decision Pipeline

This is the core inference pipeline that achieves institutional-grade accuracy:

```
Step 1: Toto-2 Climate Check (Survival Filter)
  Input: Multivariate time series (market data, macro indicators, volatility)
  Algorithm: Patch-based multivariate attention + VAE anomaly detection
  Output: Climate Vector [reversal_prob, macro_risk, liquidity] or REJECT
  Purpose: Prevents trading in "Random Walk" or "Crash" conditions

Step 2: TabPFN Signal Check (Selection Filter)
  Input: Feature table (current market snapshot + climate vector + alpha factors)
  Algorithm: Transformer forward pass with in-context Bayesian inference
  Output: P(target_hit|data), P(stop_hit|data) — calibrated probability distribution
  Purpose: Finds specific high-probability setups

Step 3: Hermes Execution Check (Efficiency Filter)
  Input: Signal from TabPFN + Toto-2 gas/latency forecast
  Algorithm: Cost-benefit analysis (expected value vs execution costs)
  Output: EXECUTE, DEFER, or REJECT
  Purpose: Ensures edge isn't eaten by fees/slippage
```

### 4.2 Research Pipeline (Autonomous Alpha Discovery)

```
Phase 0: RLM Deep Mining
  Input: Massive archives (audits, filings, forums, news)
  Process: Recursive REPL → programmatic filter → sub-agent analysis → pattern detection
  Output: Structured Alpha Vector

Phase 1: Hermes Skill Creation
  Input: Structured Alpha Vector
  Process: Code synthesis → containerization → sandbox testing → tool registration
  Output: New executable skill/tool

Phase 2: pi-autoresearch Validation
  Input: Historical data + new skill
  Process: Hypothesis → code → TabPFN evaluation (500ms) → iterate → Git commit/rollback
  Algorithm: MOO (NSGA-II) for multi-objective optimization
  Output: Verified strategy logic with performance metrics

Phase 3: Memory Integration
  Input: Outcome of strategy deployment
  Process: Hermes analyzes success/failure → updates ChromaDB vector store
  Output: Improved agent memory for future pattern matching

Phase 4: Strategy Refinement
  Input: Failure analysis (e.g., false positive due to holiday calendar)
  Process: Hermes creates new filter → regenerates skill with fix
  Output: Self-improved strategy
```

### 4.3 User Strategy Creation Flow

```
Chat Mode (Guided for Beginners):
  "Create a strategy that buys No shares when Trump odds drop below 45%"
  → LLM interprets intent
  → Maps to node graph: [Polymarket Source] → [Threshold: odds < 45%] → [Place Bet: No shares]
  → User confirms in chat
  → Strategy deployed to paper trading

Node Mode (Visual for Advanced):
  User drags Source nodes onto canvas
  → Connect to Condition nodes
  → Connect to Action nodes
  → Configure each node's parameters via property panel
  → Real-time validation shows data types match
  → Click "Backtest" → results shown inline
  → Click "Deploy" → moves to live monitoring

Freeform Chat (Power Users):
  "/create strategy --source polymarket --condition 'odds < 0.45' --action 'buy no $50'"
  → Direct strategy creation via command syntax
  → Same node graph generated under the hood for visualization
```

### 4.4 Execution Pipeline

```
Strategy Trigger fires
  → TabPFN re-validates signal in current context (500ms)
  → Toto-2 checks macro climate hasn't shifted
  → Hermes calculates optimal execution parameters
  → Risk Manager checks position size against portfolio limits
  → Order routed to appropriate platform via Rust execution bridge
  → Toto-2 monitors mempool for optimal gas/timing
  → Order executed
  → Outcome recorded → Memory updated
  
If failure occurs:
  → Hermes analyzes failure
  → Identifies root cause (e.g., "holiday calendar not accounted for")
  → Creates new filter in strategy
  → Logs to memory to prevent recurrence
```

---

## Part 5: UI/UX Specification

### 5.1 Terminal Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER: [Logo] [Markets] [Strategies] [Analytics] [Account]    │
├───────────────────┬─────────────────────────────────────────────┤
│                   │                                             │
│   SIDEBAR         │        MAIN AREA                            │
│                   │                                             │
│  • Market Watch   │   [Content changes by selected tab]         │
│  • My Strategies  │                                             │
│  • Risk Manager   │   Markets → data table + charts             │
│  • Portfolio      │   Strategies → node canvas or chat          │
│  • Alerts         │   Analytics → dashboards                    │
│  • Settings       │   Portfolio → positions, P&L               │
│                   │                                             │
│                   │                                             │
├───────────────────┴─────────────────────────────────────────────┤
│  STATUS BAR: [Platform Status] [Last Updated] [Active Strategies]│
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Chat Interface

- Positioned as a slide-out panel from the right side of the terminal
- Can be toggled on/off
- Supports both guided (wizard) and freeform (command) modes
- Strategy creation via chat auto-generates the node graph for visual editing
- Command history, example prompts, progressive disclosure

### 5.3 Node Canvas

- React Flow-based drag-and-drop interface
- Left panel: node palette categorized by type (Source, Filter, Condition, Action, Risk, Analysis, Execution, Memory)
- Property panel opens on node selection for configuration
- Real-time data type validation on connections
- Inline backtest results
- Strategy version history

### 5.4 Onboarding Flow

1. **Welcome screen** — brief value proposition
2. **Market discovery** — browse trending markets with real-time odds
3. **First strategy** — chat-guided creation ("Create a simple strategy")
4. **Demo mode** — paper trade the strategy
5. **Results** — see performance, modify via chat or node editor
6. **Go live** — connect platform account, deploy

---

## Part 6: Technology Stack

| Layer | Technology |
|---|---|
| Frontend Framework | React + TypeScript + Vite |
| UI Components | Shadcn/UI + Tailwind CSS |
| State Management | TanStack Query + Zustand |
| Validation | Zod |
| Node Canvas | React Flow |
| Charts | Lightweight Charts / Recharts |
| API Framework | FastAPI (Python) |
| Vector DB (primary) | LanceDB |
| Vector DB (lightweight) | FAISS |
| Analytics SQL | DuckDB |
| Agent Memory | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Re-ranker | jina-reranker-v1-tiny-en |
| Local AI — Embeddings | ONNX Runtime |
| Local AI — LLMs | llama.cpp (GGUF) |
| Agentic Search — Discovery | SearXNG |
| Agentic Search — Fast Parse | Scrapling |
| Agentic Search — Stealth Browser | Camoufox (via Playwright) |
| Agentic Search — DOM Extraction | Playwright (Accessibility Tree) |
| Agentic Search — Intelligence | LLM API (Claude/Gemini) |
| Graph Analysis | DuckPGQ (DuckDB extension) |
| Bayesian Inference | TabPFN-2.5/2.6 |
| Time Series | Toto-2 |
| Recursive Research | dspy.RLM |
| Agent Orchestration | Hermes-Agent |
| Research Loop | pi-autoresearch |
| DSPy Framework | DSPy (for RLM + optimization) |
| Compute | Oracle Cloud + Serverless GPU (e.g. RunPod, Banana, Replicate) |
| Database | Postgres |
| CDN | Cloudflare |
| Object Storage | Cloudflare R2 (future) |

---

## Part 7: Development Roadmap

### Phase 1: Foundation (Weeks 1-6)

**Goal:** Working terminal with data aggregation + basic strategy creation

- Oracle + Postgres + Cloudflare infrastructure setup
- FastAPI backend with basic API layer
- React + Vite + Shadcn/UI frontend shell
- Real-time data ingestion from Polymarket, Kalshi, Drift APIs
- Market discovery view (table + search + filters)
- Basic chat interface (guided mode)
- Simple threshold-based strategy creation ("if odds < X, alert me")
- User authentication and account management

### Phase 2: Intelligence (Weeks 7-12)

**Goal:** AI-powered analysis and strategy refinement

- TabPFN integration (zero-shot signal validation)
- Toto-2 integration (macro climate filter)
- LanceDB vector store for market data
- DuckDB analytics layer for backtesting
- Hermes-Agent orchestration backbone
- Memory system (ChromaDB) for agent learning
- Node canvas strategy builder (React Flow)
- Backtester with basic metrics
- Strategy template save/load

### Phase 3: Autonomy (Weeks 13-18)

**Goal:** Self-improving strategies and advanced features

- pi-autoresearch integration (automated hypothesis testing)
- RLM via DSPy for deep archive mining
- Hermes automatic skill creation (writes, tests, registers new tools)
- Risk Manager with full strategy template system
- Paper trading environment
- Multi-strategy portfolio management
- SHAP-based explainability for all AI decisions
- Copy trading infrastructure

### Phase 4: Production (Weeks 19-24)

**Goal:** Production-hardened platform with execution

- Rust-based execution engine bridge
- Direct order placement on Polymarket/Kalshi/Drift
- Advanced backtester (walk-forward, Monte Carlo, multi-objective optimization)
- Distillation engine (TabPFN → lightweight production models)
- Performance optimization and scaling
- Security audit and penetration testing
- Documentation and onboarding flows

### Phase 5: Post-Launch (Future)

- WhatsApp bot integration
- Social media DM bots (TikTok, Instagram, Twitter/X)
- Chrome extension (inject UI into prediction market sites and social media)
- Mobile app
- API for external developers
- Marketplace for shared strategies

---

## Part 8: Data Models

### 8.1 Market Data Model

```typescript
interface Market {
  id: string;
  platform: 'polymarket' | 'kalshi' | 'drift';
  title: string;
  description: string;
  category: string;
  currentOdds: number;
  bid: number;
  ask: number;
  volume: number;
  liquidity: number;
  participants: number;
  closeTime: Date;
  resolutionTime?: Date;
  status: 'open' | 'closed' | 'resolved';
  outcome?: string;
  outcomes: string[];
}
```

### 8.2 Strategy Model

```typescript
interface Strategy {
  id: string;
  name: string;
  description: string;
  nodes: StrategyNode[];
  edges: Edge[];
  createdAt: Date;
  updatedAt: Date;
  status: 'draft' | 'active' | 'paused' | 'archived';
  mode: 'chat' | 'node' | 'hybrid';
  riskProfile: RiskProfile;
  performance?: StrategyPerformance;
}
```

### 8.3 Risk Profile Model

```typescript
interface RiskProfile {
  maxDrawdown: number;
  maxPositionSize: number;
  portfolioAllocation: number;
  kellyFraction: number;
  stopLoss: number;
  takeProfit: number;
  riskStrategyId?: string; // reference to a user-created risk strategy
  customParams: Record<string, unknown>;
}
```

### 8.4 Agent Memory Model

```typescript
interface AgentMemory {
  id: string;
  type: 'success' | 'failure' | 'pattern' | 'insight';
  domain: 'crypto' | 'prediction_market' | 'sports';
  timestamp: Date;
  context: string;
  factors: Record<string, number>;
  outcome: string;
  embedding: number[]; // vector for similarity search
  relatedMemories: string[];
  skillsCreated: string[];
}
```

### 8.5 Strategy Performance Model

```typescript
interface StrategyPerformance {
  totalTrades: number;
  winRate: number;
  profitLoss: number;
  sharpeRatio: number;
  maxDrawdown: number;
  avgRR: number;
  kellyOptimal: number;
  calibration: number; // Brier score
  regimeBuckets: Record<string, RegimePerformance>;
}
```

---

## Part 9: Dependency Map

```
User Interface (React + Vite)
├── Chat Interface
│   └── LLM Gateway (Hermes-Agent)
├── Node Canvas
│   └── Strategy Engine
└── Terminal Dashboard
    └── Real-time Data Pipeline

Hermes-Agent (Orchestrator)
├── FastAPI Backend
├── ChromaDB (Memory)
├── pi-autoresearch (Research)
│   └── dspy.RLM (Deep Mining)
├── TabPFN (Bayesian Analysis)
├── Toto-2 (Time Series)
└── Skill Manager (Code Synthesis)
    └── Sandbox Execution Environment

Data Layer
├── LanceDB (Vector Store)
├── DuckDB (Analytics)
├── Postgres (Relational)
├── sentence-transformers (Embeddings)
└── API Connectors
    ├── Polymarket API
    ├── Kalshi API
    ├── Drift API
    └── Web Scraper (Puppeteer)

Infrastructure
├── Oracle Cloud (Compute)
├── Cloudflare (CDN)
├── Cloudflare R2 (Object Storage - future)
└── Git Repository (Strategy Versioning)
```

---

## Part 10: Implementation Plan Outline

The full implementation plan will be detailed in a separate document. High-level phases:

1. **Week 1-2:** Infrastructure + data ingestion
2. **Week 3-4:** Terminal UI + market discovery
3. **Week 5-6:** Chat interface + basic strategy creation
4. **Week 7-8:** TabPFN + Toto-2 AI pipeline
5. **Week 9-10:** Node canvas + backtesting
6. **Week 11-12:** Hermes-Agent orchestration + memory
7. **Week 13-14:** pi-autoresearch + RLM
8. **Week 15-16:** Risk Manager + advanced strategies
9. **Week 17-18:** Paper trading + copy trading
10. **Week 19-20:** Execution engine + Rust bridge
11. **Week 21-22:** Production hardening + security
12. **Week 23-24:** Launch + documentation

---

*End of PRD*
