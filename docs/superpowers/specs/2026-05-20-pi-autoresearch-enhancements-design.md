# pi-autoresearch: NSGA-II, GP, Monte Carlo, Git Tracking, Hermes Plugin, and Frontend Dashboard

## Motivation

The existing `AutoresearchService` uses static hypothesis templates with random
threshold selection, a single weighted-sum composite score, and no persistence of
experiment state. The `git_commit_hash` field on `ExperimentResult` is always
`None`. This spec adds the six missing features from the pi-autoresearch design.

## Architecture

New package `backend/app/ai/pi_autoresearch/` with five submodules, integrated
into the existing `AutoresearchService.run_iteration()` flow:

```
backend/app/ai/pi_autoresearch/
├── __init__.py
├── nsgaii.py               # NSGA-II multi-objective optimizer
├── genetic_programming.py  # Hypothesis evolution (mutation, crossover)
├── monte_carlo.py          # Monte Carlo backtest simulation
├── experiment_tracker.py   # Git commit/rollback for experiments
└── hermes_plugin.py        # Hermes-Agent sub-process for hypothesis critique
```

`AutoresearchService` orchestrates the pipeline:
`GP evolve → Monte Carlo simulate → NSGA-II score → Git commit → Hermes critique`

Frontend: new `IterationChart` component in the ResearchPage using recharts.

## Feature Specifications

### 1. NSGA-II Multi-Objective Optimizer (`nsgaii.py`)

**Current state:** `_compute_composite_score` returns a scalar weighted sum.
Verdict (KEPT/WARN/REVERTED) is a simple threshold on that scalar.

**Goal:** Find Pareto-optimal frontiers across {Sharpe, win rate, -drawdown,
TabPFN probability} and use frontier membership to inform the verdict.

**Implementation plan:**

1. `Individual` dataclass
   - `objectives: list[float]` — one per objective (Sharpe, win rate, -drawdown,
     TabPFN probability)
   - `crowding_distance: float`
   - `rank: int`
   - `hypothesis: dict` — back-reference to the hypothesis config

2. `fast_non_dominated_sort(population: list[Individual]) -> list[list[Individual]]`
   - Standard NSGA-II algorithm: for each individual, track `domination_count`
     and `dominated_set`. First front = individuals with count == 0.
   - O(M * N²) where M = objectives and N = population size.

3. `crowding_distance(front: list[Individual]) -> None`
   - Sort each objective, assign infinite distance to boundary points,
     normalize distances.

4. `tournament_selection(population, k=2)`
   - Lower rank wins; if same rank, higher crowding distance wins.

5. `nsga2_optimize(hypotheses, objectives_matrix) -> list[Individual]`
   - Wrap existing hypotheses as Individuals, run non-dominated sort,
     assign crowding distance.
   - Returns ranked Individuals with Pareto front info.

**Integration:** `AutoresearchService.run_iteration()` calls `nsga2_optimize`
instead of `_compute_composite_score`. The rank and crowding distance become
part of the return dict. Verdict logic adds a "pareto_front_rank" check: rank 0
= KEPT, rank 1 = WARN, rank > 1 = REVERTED.

### 2. Genetic Programming for Hypothesis Evolution (`genetic_programming.py`)

**Current state:** `_generate_hypotheses` randomly samples from 5 static
templates with uniformly random thresholds.

**Goal:** Evolve new hypotheses by mutating and crossing over successful
(verdict == KEPT) past hypotheses. Templates serve as the initial seed
population; subsequent generations are produced by GP operators.

**Implementation plan:**

1. `HypothesisIndividual` dataclass
   - `template: str` — the hypothesis template string
   - `feature: str` — the feature name
   - `operator: str` — "gt" or "lt"
   - `threshold: float` — numeric threshold
   - `regime_affinity: list[str]`

2. `mutation(individual, mutation_rate=0.3) -> HypothesisIndividual`
   - Perturb threshold: `threshold += random.uniform(-0.05, 0.05)`, clamped to
     [0.0, 1.0]
   - Flip operator: 30% chance of swapping "gt" ↔ "lt"
   - Swap feature: 20% chance of replacing with a random top feature
   - Swap template: 10% chance of picking a different template

3. `crossover(parent_a, parent_b) -> tuple[HypothesisIndividual, HypothesisIndividual]`
   - Single-point crossover: swap threshold and operator between two parents.
   - 70% crossover rate; otherwise return clones.

4. `tournament_select(population, k=3) -> HypothesisIndividual`
   - Pick k random individuals from the population, return the one with
     highest composite_score.

5. `evolve_population(past_results, top_features, pop_size=10, elite_size=2)`
   - Seeds from successful past results + template-generated fresh individuals.
   - Elitism: carry top `elite_size` directly to next gen.
   - Remainder: tournament select parents → crossover → mutate.
   - Returns `list[HypothesisIndividual]`.

**Integration:** `AutoresearchService._generate_hypotheses` checks
`past_results` for KEPT entries. If 2+ exist, calls `evolve_population`
instead of template sampling.

### 3. Monte Carlo Simulation (`monte_carlo.py`)

**Current state:** Single deterministic backtest run via `Backtester.run()`.

**Goal:** Run N backtest simulations with bootstrapped trade sequences to
produce distribution statistics: mean, std, VaR_95, CVaR_95.

**Implementation plan:**

1. `MonteCarloResult` dataclass
   - `n_simulations: int`
   - `mean_sharpe: float`, `std_sharpe: float`
   - `mean_win_rate: float`, `std_win_rate: float`
   - `mean_total_pnl: float`, `std_total_pnl: float`
   - `var_95: float` — 5th percentile of PnL
   - `cvar_95: float` — mean of PnL below VaR
   - `simulations: list[dict]` — raw per-simulation results (optional)

2. `monte_carlo_backtest(backtest_config, market_history, n=500) -> MonteCarloResult`
   - Run `Backtester.run()` N times.
   - Each simulation: resample market_history with replacement (bootstrap) or
     add Gaussian noise to odds (noise = std of historical odds changes).
   - Collect trade-level metrics per simulation.
   - Compute distribution stats from N runs.

3. `_bootstrap_market_history(history, noise_std=0.01) -> list[dict]`
   - Resample `len(history)` entries with replacement, then add
     `N(0, noise_std)` noise to each `current_odds`.

**Integration:** `AutoresearchService.run_iteration()` calls
`monte_carlo_backtest` instead of single `Backtester.run()`. The distribution
stats (esp. VaR/CVaR) feed into the NSGA-II objectives as risk metrics.

### 4. Experiment Tracker (`experiment_tracker.py`)

**Current state:** `GitManager` exists in `app/ai/git_manager.py` but is only
used for skill management. `autoresearch.py` hardcodes `git_commit_hash: None`.

**Goal:** Commit each KEPT experiment result to a dedicated experiments Git
repository and support rollback to any previous experiment state.

**Implementation plan:**

1. `ExperimentTracker` class
   - Wraps an existing `GitManager` instance or creates its own.
   - Uses a dedicated `experiments/` directory under the repo path.
   - `commit_experiment(experiment_result: dict) -> str | None`
     - Write experiment JSON to `experiments/<session_id>/iter_<n>.json`
     - Git add + commit with structured message.
     - Returns commit hash (or None on failure).
   - `rollback_experiment(commit_hash: str) -> bool`
     - Git checkout specific commit, restore experiment files.
   - `get_experiment_history(session_id: str) -> list[dict]`
     - Git log for experiment files of a given session.

**Integration:** Constructed in `AutoresearchService` (or injected). Called
after verdict == KEPT. The commit hash is stored in the return dict and
persisted to `ExperimentResult.git_commit_hash`.

### 5. Hermes Plugin (`hermes_plugin.py`)

**Current state:** No Hermes integration in autoresearch at all. The
`HermesSidecar` exists for chat but is never invoked for research.

**Goal:** Optionally use Hermes-Agent as a sub-process to:
- Propose novel hypothesis descriptions (beyond templates)
- Critique results after backtesting

**Implementation plan:**

1. `HermesResearchPlugin` class
   - Accepts optional `HermesSidecar` instance.
   - `available: bool` property (delegates to sidecar.available).

   - `async propose_hypotheses(climate, feature_importance, top_features, n=3) -> list[str]`
     - Prompt: "Given market regime {regime}, top features {features}, propose
       {n} novel prediction market hypotheses."
     - Parse response into hypothesis description strings.
     - Returns empty list if Hermes unavailable.

   - `async critique_result(experiment_result: dict) -> dict`
     - Prompt: "Critique this experiment result: {result}. Suggest improvements
       for the next iteration."
     - Returns structured feedback dict.

**Integration:** `AutoresearchService` optionally accepts `HermesResearchPlugin`.
If available and Hermes is configured, `_generate_hypotheses` includes
LLM-proposed hypotheses alongside evolved ones. `_determine_verdict` can be
overridden by Hermes critique for KEPT/WARN that is within range.

### 6. Frontend Iteration-History Chart

**Current state:** ResearchPage has a table of iteration history (columns:
iteration, hypothesis, regime, score, sharpe, win rate, TabPFN, verdict).

**Goal:** Add a line chart showing composite_score, win_rate, and sharpe
trending over iterations, plus a Pareto-front scatter plot.

**Implementation plan:**

1. New component `frontend/src/components/research/IterationChart.tsx`
   - Uses `recharts` (already available as transitive dep or add explicitly).
   - `LineChart` with X = iteration, Y = value.
   - Three series: composite_score (white), backtest_sharpe (blue),
     backtest_win_rate (green).
   - Tooltip on hover, legend at top.
   - Props: `results: ExperimentResult[]`

2. Optional: Pareto scatter plot (Sharpe vs Win Rate)
   - `ScatterChart` with point color = verdict (green KEPT, yellow WARN, red REVERTED).
   - Helps visualize the Pareto frontier.

3. Integration: Render in ResearchPage below the iteration history table.
   - Only visible when `results.length > 0`.
   - Conditionally render if recharts import succeeds (graceful fallback to
     "Chart library not available").

**Data source:** Existing `GET /api/research/sessions/{id}/results` endpoint
that returns `{results: [...]}`. No new API needed.

## Dependencies

- `recharts` — needs to be in `frontend/package.json` (check existing deps)
- No new Python dependencies; all use stdlib + numpy + scipy (already present)
- `git` CLI — required for `ExperimentTracker` (same requirement as `GitManager`)

## Testing Strategy

Each new submodule gets its own test file:

| File | Tests |
|------|-------|
| `tests/test_pi_nsgaii.py` | fast_non_dominated_sort correctness, crowding_distance, tournament_selection, full nsga2_optimize with synthetic objectives |
| `tests/test_pi_genetic_programming.py` | mutation preserves structure, crossover produces valid children, evolve_population with 0/1/5+ past results |
| `tests/test_pi_monte_carlo.py` | bootstrap resampling preserves length, monte_carlo_backtest returns correct stats shapes, VaR < CVaR invariant |
| `tests/test_pi_experiment_tracker.py` | commit_experiment returns hash/None, rollback_experiment restores file |
| `tests/test_pi_hermes_plugin.py` | propose_hypotheses returns list when available/empty when not, critique_result structure |

Existing tests must still pass (69 backend + 13 frontend). The new NSGA-II
scoring replaces the old `_compute_composite_score` in `run_iteration`, so
existing tests that mock TabPFN and check verdicts should continue to pass
(with minor fixture adjustments for the new return fields).

## Performance Considerations

- **NSGA-II:** O(M * N²). N = population size (hypotheses per iteration),
  typically 5-10. Negligible cost.
- **Monte Carlo:** N × backtest cost. N = 500, each backtest on ~100 history
  rows = 50,000 trade evaluations. Acceptable for a background research
  iteration (takes ~1-2s).
- **GP evolution:** O(pop_size²) per generation. Single generation per
  iteration, negligible.
- **Git commit:** Subprocess call ~50ms. Only for KEPT results.
- **Hermes:** API call latency (~1-5s). Only when available and configured.

## Rollout

1. Implement submodules and tests in order: NSGA-II → GP → Monte Carlo →
   ExperimentTracker → HermesPlugin → Frontend chart.
2. Each submodule independently testable before integration.
3. Integration: modify `AutoresearchService.run_iteration()` and
   `_generate_hypotheses()` to use new components.
4. Run full test suite after each integration step.
