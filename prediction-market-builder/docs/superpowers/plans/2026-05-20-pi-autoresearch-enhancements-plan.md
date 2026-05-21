# pi-autoresearch Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add NSGA-II multi-objective optimization, genetic programming hypothesis evolution, Monte Carlo simulation, Git experiment tracking, Hermes-Agent sub-process plugin, and frontend iteration-history chart.

**Architecture:** New `backend/app/ai/pi_autoresearch/` package with 5 submodules. Each is independently testable. Integration modifies `AutoresearchService.run_iteration()` to orchestrate the pipeline: GP evolve → Monte Carlo simulate → NSGA-II score → Git commit → Hermes critique. Frontend gets a recharts LineChart component.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, numpy, recharts 3.x, TypeScript, vitest

---
Models/API already have `pareto_front` column and `enable_genetic_optimization` config — no model changes needed.

### Task 1: Create `pi_autoresearch` package and NSGA-II module

**Files:**
- Create: `backend/app/ai/pi_autoresearch/__init__.py`
- Create: `backend/app/ai/pi_autoresearch/nsgaii.py`
- Test: `backend/tests/test_pi_nsgaii.py`

- [ ] **Step 1: Create the package `__init__.py`**

Write `backend/app/ai/pi_autoresearch/__init__.py`:
```python
from __future__ import annotations
```

- [ ] **Step 2: Write the test file for NSGA-II**

Write `backend/tests/test_pi_nsgaii.py`:
```python
from __future__ import annotations

import pytest
import numpy as np
from app.ai.pi_autoresearch.nsgaii import (
    Individual,
    fast_non_dominated_sort,
    crowding_distance,
    tournament_selection,
    nsga2_optimize,
)


def test_individual_defaults():
    ind = Individual(objectives=[1.0, 2.0])
    assert ind.objectives == [1.0, 2.0]
    assert ind.crowding_distance == 0.0
    assert ind.rank == -1
    assert ind.hypothesis == {}


def test_fast_non_dominated_sort_two_fronts():
    # 3 individuals: A dominates B, B dominates C
    pop = [
        Individual(objectives=[1.0, 2.0], hypothesis={"id": "A"}),
        Individual(objectives=[0.5, 1.0], hypothesis={"id": "B"}),
        Individual(objectives=[0.1, 0.5], hypothesis={"id": "C"}),
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 1  # all comparable, single chain
    assert len(fronts[0]) == 3
    # A should dominate all
    assert pop[0].rank == 0


def test_fast_non_dominated_sort_incomparable():
    # A dominates B on both, C is incomparable with A
    pop = [
        Individual(objectives=[1.0, 2.0], hypothesis={"id": "A"}),
        Individual(objectives=[0.3, 1.0], hypothesis={"id": "B"}),
        Individual(objectives=[0.9, 2.2], hypothesis={"id": "C"}),
    ]
    fronts = fast_non_dominated_sort(pop)
    # A and C should both be rank 0 (neither dominates the other)
    # B is rank 1 (dominated by both A and C)
    assert len(fronts) >= 2
    assert len(fronts[0]) == 2  # A and C in first front


def test_crowding_distance_boundary():
    front = [
        Individual(objectives=[0.0, 0.0]),
        Individual(objectives=[0.5, 0.5]),
        Individual(objectives=[1.0, 1.0]),
    ]
    crowding_distance(front)
    # Boundary points (first and last) should have infinite distance
    assert front[0].crowding_distance == float("inf")
    assert front[2].crowding_distance == float("inf")
    # Middle point should have finite distance
    assert front[1].crowding_distance < float("inf")


def test_tournament_selection_rank():
    pop = [
        Individual(objectives=[1.0, 2.0], hypothesis={"id": "A"}, rank=0, crowding_distance=float("inf")),
        Individual(objectives=[0.5, 1.0], hypothesis={"id": "B"}, rank=1, crowding_distance=1.0),
    ]
    selected = tournament_selection(pop, k=2)
    assert selected in pop


def test_nsga2_optimize_basic():
    hypotheses = [
        {"id": "A", "threshold": 0.6, "operator": "gt"},
        {"id": "B", "threshold": 0.5, "operator": "gt"},
        {"id": "C", "threshold": 0.4, "operator": "lt"},
    ]
    objectives_matrix = [
        [1.5, 0.6, -0.1, 0.7],
        [0.8, 0.5, -0.2, 0.6],
        [0.3, 0.4, -0.3, 0.5],
    ]
    result = nsga2_optimize(hypotheses, objectives_matrix)
    assert len(result) == 3
    for ind in result:
        assert len(ind.objectives) == 4
        assert "id" in ind.hypothesis
        assert "pareto_rank" in ind.hypothesis
        assert "crowding_distance" in ind.hypothesis


def test_nsga2_optimize_empty():
    assert nsga2_optimize([], []) == []


@pytest.mark.asyncio
async def test_nsga2_optimize_single():
    hypotheses = [{"id": "only"}]
    objectives_matrix = [[1.0, 0.5, -0.1, 0.5]]
    result = nsga2_optimize(hypotheses, objectives_matrix)
    assert len(result) == 1
    assert result[0].rank == 0
    assert result[0].crowding_distance == float("inf")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_pi_nsgaii.py -v`
Expected: FAIL with ImportError (no nsgaii module yet)

- [ ] **Step 4: Implement NSGA-II module**

Write `backend/app/ai/pi_autoresearch/nsgaii.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Individual:
    objectives: list[float]
    crowding_distance: float = 0.0
    rank: int = -1
    hypothesis: dict[str, Any] = field(default_factory=dict)


def fast_non_dominated_sort(population: list[Individual]) -> list[list[Individual]]:
    n = len(population)
    domination_count = [0] * n
    dominated_sets: list[list[int]] = [[] for _ in range(n)]
    fronts: list[list[int]] = [[]]

    for i in range(n):
        for j in range(i + 1, n):
            if _dominates(population[i], population[j]):
                dominated_sets[i].append(j)
                domination_count[j] += 1
            elif _dominates(population[j], population[i]):
                dominated_sets[j].append(i)
                domination_count[i] += 1
        if domination_count[i] == 0:
            fronts[0].append(i)
            population[i].rank = 0

    i = 0
    while fronts[i]:
        next_front: list[int] = []
        for idx in fronts[i]:
            for dominated_idx in dominated_sets[idx]:
                domination_count[dominated_idx] -= 1
                if domination_count[dominated_idx] == 0:
                    next_front.append(dominated_idx)
                    population[dominated_idx].rank = i + 1
        i += 1
        fronts.append(next_front)

    fronts.pop()
    return [[population[idx] for idx in front] for front in fronts]


def _dominates(a: Individual, b: Individual) -> bool:
    better_in_one = False
    for oa, ob in zip(a.objectives, b.objectives):
        if oa > ob:
            better_in_one = True
        elif ob > oa:
            return False
    return better_in_one


def crowding_distance(front: list[Individual]) -> None:
    if len(front) <= 2:
        for ind in front:
            ind.crowding_distance = float("inf")
        return

    m = len(front[0].objectives)
    for ind in front:
        ind.crowding_distance = 0.0

    for obj_idx in range(m):
        front.sort(key=lambda ind: ind.objectives[obj_idx])
        obj_min = front[0].objectives[obj_idx]
        obj_max = front[-1].objectives[obj_idx]
        obj_range = obj_max - obj_min
        if obj_range == 0:
            continue
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")
        for i in range(1, len(front) - 1):
            front[i].crowding_distance += (
                front[i + 1].objectives[obj_idx] - front[i - 1].objectives[obj_idx]
            ) / obj_range


def tournament_selection(population: list[Individual], k: int = 2) -> Individual:
    candidates = np.random.choice(population, size=min(k, len(population)), replace=False).tolist()
    best = candidates[0]
    for candidate in candidates[1:]:
        if candidate.rank < best.rank:
            best = candidate
        elif candidate.rank == best.rank and candidate.crowding_distance > best.crowding_distance:
            best = candidate
    return best


def nsga2_optimize(
    hypotheses: list[dict[str, Any]],
    objectives_matrix: list[list[float]],
) -> list[Individual]:
    if not hypotheses or not objectives_matrix:
        return []

    population = [
        Individual(objectives=list(objectives_matrix[i]), hypothesis=dict(hypotheses[i]))
        for i in range(len(hypotheses))
    ]

    fronts = fast_non_dominated_sort(population)
    for front in fronts:
        crowding_distance(front)

    for i, ind in enumerate(population):
        ind.hypothesis["pareto_rank"] = ind.rank
        ind.hypothesis["crowding_distance"] = ind.crowding_distance

    return population
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_pi_nsgaii.py -v`
Expected: 8 PASSED

---

### Task 2: Genetic Programming module

**Files:**
- Create: `backend/app/ai/pi_autoresearch/genetic_programming.py`
- Test: `backend/tests/test_pi_genetic_programming.py`

- [ ] **Step 1: Write the test file**

Write `backend/tests/test_pi_genetic_programming.py`:
```python
from __future__ import annotations

import pytest
from app.ai.pi_autoresearch.genetic_programming import (
    HypothesisIndividual,
    mutation,
    crossover,
    tournament_select,
    evolve_population,
)


def test_hypothesis_individual_defaults():
    h = HypothesisIndividual(template="test {feature}", feature="odds", operator="gt", threshold=0.6)
    assert h.template == "test {feature}"
    assert h.description == "test odds"
    assert h.threshold == 0.6
    assert h.operator == "gt"


def test_mutation_perturbs_threshold():
    h = HypothesisIndividual(template="{feature} breakout", feature="volume", operator="gt", threshold=0.5)
    mutated = mutation(h, mutation_rate=1.0)
    assert mutated.threshold != 0.5 or mutated.operator != "gt"


def test_mutation_preserves_structure():
    h = HypothesisIndividual(template="{feature} breakout", feature="volume", operator="gt", threshold=0.5)
    mutated = mutation(h, mutation_rate=0.0)
    assert mutated.threshold == 0.5
    assert mutated.operator == "gt"
    assert mutated.feature == "volume"


def test_crossover_swaps():
    a = HypothesisIndividual(template="{feature} a", feature="odds", operator="gt", threshold=0.6)
    b = HypothesisIndividual(template="{feature} b", feature="volume", operator="lt", threshold=0.3)
    c1, c2 = crossover(a, b, crossover_rate=1.0)
    assert c1.operator == b.operator or c2.operator == a.operator


def test_crossover_no_crossover():
    a = HypothesisIndividual(template="{feature} a", feature="odds", operator="gt", threshold=0.6)
    b = HypothesisIndividual(template="{feature} b", feature="volume", operator="lt", threshold=0.3)
    c1, c2 = crossover(a, b, crossover_rate=0.0)
    assert c1.threshold == a.threshold
    assert c2.threshold == b.threshold


def test_tournament_select_returns_best():
    pop = [
        HypothesisIndividual(template="{f} a", feature="o", operator="gt", threshold=0.5, composite_score=0.1),
        HypothesisIndividual(template="{f} b", feature="o", operator="gt", threshold=0.5, composite_score=1.5),
        HypothesisIndividual(template="{f} c", feature="o", operator="gt", threshold=0.5, composite_score=0.8),
    ]
    selected = tournament_select(pop, k=3)
    assert selected.composite_score == 1.5


def test_evolve_population_empty_past():
    result = evolve_population(past_results=[], top_features=["odds", "volume"])
    assert len(result) >= 5


def test_evolve_population_with_past():
    past = [
        {"composite_score": 1.5, "verdict": "KEPT", "backtest_config": {"threshold": 0.6, "operator": "gt"},
         "hypothesis": "momentum on odds", "regime_affinity": ["trending"]},
    ]
    result = evolve_population(past_results=past, top_features=["odds", "volume"])
    assert len(result) >= 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_pi_genetic_programming.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement GP module**

Write `backend/app/ai/pi_autoresearch/genetic_programming.py`:
```python
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

HYPOTHESIS_TEMPLATES = [
    "Momentum breakout on {feature}",
    "Mean reversion on {feature}",
    "Volatility contraction entry on {feature}",
    "Volume spike confirmation on {feature}",
    "Spread contraction scalp on {feature}",
]

OPERATORS = ["gt", "lt"]
REGIMES = ["trending", "ranging", "calm", "volatile"]


@dataclass
class HypothesisIndividual:
    template: str
    feature: str
    operator: str
    threshold: float
    regime_affinity: list[str] = field(default_factory=list)
    composite_score: float = 0.0

    @property
    def description(self) -> str:
        return self.template.format(feature=self.feature)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "template": self.template,
            "feature": self.feature,
            "operator": self.operator,
            "threshold": self.threshold,
            "regime_affinity": self.regime_affinity,
            "composite_score": self.composite_score,
        }


def mutation(ind: HypothesisIndividual, mutation_rate: float = 0.3, top_features: list[str] | None = None) -> HypothesisIndividual:
    new = HypothesisIndividual(
        template=ind.template,
        feature=ind.feature,
        operator=ind.operator,
        threshold=ind.threshold,
        regime_affinity=list(ind.regime_affinity),
        composite_score=ind.composite_score,
    )
    if random.random() < mutation_rate:
        new.threshold = max(0.0, min(1.0, new.threshold + random.uniform(-0.05, 0.05)))
        new.threshold = round(new.threshold, 3)
    if random.random() < 0.3:
        new.operator = "lt" if new.operator == "gt" else "gt"
    if top_features and random.random() < 0.2:
        new.feature = random.choice(top_features)
    if random.random() < 0.1:
        new.template = random.choice([t for t in HYPOTHESIS_TEMPLATES if t != new.template] or HYPOTHESIS_TEMPLATES)
    return new


def crossover(parent_a: HypothesisIndividual, parent_b: HypothesisIndividual, crossover_rate: float = 0.7) -> tuple[HypothesisIndividual, HypothesisIndividual]:
    if random.random() > crossover_rate:
        return (
            HypothesisIndividual(template=parent_a.template, feature=parent_a.feature, operator=parent_a.operator, threshold=parent_a.threshold, regime_affinity=list(parent_a.regime_affinity)),
            HypothesisIndividual(template=parent_b.template, feature=parent_b.feature, operator=parent_b.operator, threshold=parent_b.threshold, regime_affinity=list(parent_b.regime_affinity)),
        )
    child_a = HypothesisIndividual(
        template=parent_a.template,
        feature=parent_a.feature,
        operator=parent_b.operator,
        threshold=parent_b.threshold,
        regime_affinity=list(parent_a.regime_affinity),
    )
    child_b = HypothesisIndividual(
        template=parent_b.template,
        feature=parent_b.feature,
        operator=parent_a.operator,
        threshold=parent_a.threshold,
        regime_affinity=list(parent_b.regime_affinity),
    )
    return child_a, child_b


def tournament_select(population: list[HypothesisIndividual], k: int = 3) -> HypothesisIndividual:
    candidates = random.sample(population, min(k, len(population)))
    return max(candidates, key=lambda ind: ind.composite_score)


def _past_to_individual(r: dict[str, Any], top_features: list[str]) -> HypothesisIndividual | None:
    config = r.get("backtest_config") or {}
    return HypothesisIndividual(
        template=r.get("hypothesis", "Momentum breakout on {feature}"),
        feature=top_features[0] if top_features else "odds",
        operator=config.get("operator", "gt"),
        threshold=config.get("threshold", 0.5),
        regime_affinity=r.get("regime_affinity", ["calm"]),
        composite_score=r.get("composite_score", 0.0),
    )


def _fresh_individual(top_features: list[str]) -> HypothesisIndividual:
    template = random.choice(HYPOTHESIS_TEMPLATES)
    feature = random.choice(top_features) if top_features else "odds"
    operator = random.choice(OPERATORS)
    threshold = round(random.uniform(0.3, 0.7), 3)
    regime = random.choice(REGIMES)
    return HypothesisIndividual(
        template=template, feature=feature, operator=operator,
        threshold=threshold, regime_affinity=[regime],
    )


def evolve_population(
    past_results: list[dict[str, Any]],
    top_features: list[str],
    pop_size: int = 10,
    elite_size: int = 2,
) -> list[dict[str, Any]]:
    kept = [r for r in past_results if r.get("verdict") == "KEPT"]
    population: list[HypothesisIndividual] = []

    for r in kept[:elite_size]:
        ind = _past_to_individual(r, top_features)
        if ind:
            population.append(ind)

    while len(population) < pop_size:
        if len(population) >= 2:
            parent_a = tournament_select(population, k=3)
            parent_b = tournament_select(population, k=3)
            for child in crossover(parent_a, parent_b):
                if len(population) < pop_size:
                    mutated = mutation(child, top_features=top_features)
                    population.append(mutated)
        else:
            population.append(_fresh_individual(top_features))

    return [ind.to_dict() for ind in population]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_pi_genetic_programming.py -v`
Expected: 7 PASSED

---

### Task 3: Monte Carlo Simulation module

**Files:**
- Create: `backend/app/ai/pi_autoresearch/monte_carlo.py`
- Test: `backend/tests/test_pi_monte_carlo.py`

- [ ] **Step 1: Write the test file**

Write `backend/tests/test_pi_monte_carlo.py`:
```python
from __future__ import annotations

import pytest
from app.ai.pi_autoresearch.monte_carlo import (
    MonteCarloResult,
    monte_carlo_backtest,
    _bootstrap_market_history,
    _bootstrap_trades,
)


def test_bootstrap_market_history_preserves_length():
    history = [{"current_odds": 0.5}, {"current_odds": 0.6}, {"current_odds": 0.55}]
    result = _bootstrap_market_history(history)
    assert len(result) == len(history)


def test_bootstrap_market_history_empty():
    assert _bootstrap_market_history([]) == []


def test_bootstrap_market_history_noise():
    history = [{"current_odds": 0.5, "volume": 1000}]
    results = []
    for _ in range(10):
        bootstrapped = _bootstrap_market_history(history, noise_std=0.0)
        results.append(bootstrapped[0]["current_odds"])
    # With noise_std=0, should be deterministic
    assert all(r == 0.5 for r in results)


def test_bootstrap_trades_preserves_structure():
    trades = [{"pnl": 10, "type": "exit"}, {"pnl": -5, "type": "entry"}]
    result = _bootstrap_trades(trades)
    assert len(result) == len(trades)
    for t in result:
        assert "pnl" in t


@pytest.mark.asyncio
async def test_monte_carlo_backtest_shape():
    result = await monte_carlo_backtest({}, [], n=10)
    assert isinstance(result, MonteCarloResult)
    assert result.n_simulations == 10
    assert isinstance(result.mean_sharpe, float)
    assert isinstance(result.mean_win_rate, float)
    assert isinstance(result.mean_total_pnl, float)
    assert isinstance(result.var_95, float)
    assert isinstance(result.cvar_95, float)


@pytest.mark.asyncio
async def test_monte_carlo_var_less_than_cvar():
    result = await monte_carlo_backtest({}, [], n=20)
    # CVaR should be <= VaR (more extreme)
    assert result.cvar_95 <= result.var_95 + 1e-9


@pytest.mark.asyncio
async def test_monte_carlo_with_history():
    history = [{"current_odds": 0.5 + i * 0.01, "volume": 1000, "liquidity": 500, "bid": 0.48, "ask": 0.52, "participants": 50} for i in range(20)]
    result = await monte_carlo_backtest({"threshold": 0.55, "operator": "gt", "side": "yes"}, history, n=10)
    assert result.n_simulations == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_pi_monte_carlo.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Monte Carlo module**

Write `backend/app/ai/pi_autoresearch/monte_carlo.py`:
```python
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.services.backtester import Backtester

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    n_simulations: int
    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    mean_win_rate: float = 0.0
    std_win_rate: float = 0.0
    mean_total_pnl: float = 0.0
    std_total_pnl: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    simulations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_simulations": self.n_simulations,
            "mean_sharpe": round(self.mean_sharpe, 4),
            "std_sharpe": round(self.std_sharpe, 4),
            "mean_win_rate": round(self.mean_win_rate, 4),
            "std_win_rate": round(self.std_win_rate, 4),
            "mean_total_pnl": round(self.mean_total_pnl, 2),
            "std_total_pnl": round(self.std_total_pnl, 2),
            "var_95": round(self.var_95, 4),
            "cvar_95": round(self.cvar_95, 4),
        }


def _bootstrap_market_history(history: list[dict[str, Any]], noise_std: float = 0.01) -> list[dict[str, Any]]:
    if not history:
        return []
    n = len(history)
    indices = np.random.choice(n, size=n, replace=True)
    bootstrapped = []
    for idx in indices:
        entry = dict(history[idx])
        if noise_std > 0 and "current_odds" in entry:
            entry["current_odds"] = max(0.01, min(0.99, entry["current_odds"] + np.random.normal(0, noise_std)))
        bootstrapped.append(entry)
    return bootstrapped


def _bootstrap_trades(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    n = len(trades)
    indices = np.random.choice(n, size=n, replace=True)
    return [dict(trades[idx]) for idx in indices]


async def monte_carlo_backtest(
    backtest_config: dict[str, Any],
    market_history: list[dict[str, Any]],
    n: int = 50,
) -> MonteCarloResult:
    if not market_history:
        return MonteCarloResult(n_simulations=n)

    backtester = Backtester()
    all_sharpes: list[float] = []
    all_win_rates: list[float] = []
    all_pnls: list[float] = []
    simulations: list[dict[str, Any]] = []

    backtest_result = await backtester.run(backtest_config, market_history)
    base_trades = getattr(backtest_result, "trades", [])

    for _ in range(n):
        bootstrapped_history = _bootstrap_market_history(market_history)
        try:
            sim_result = await backtester.run(backtest_config, bootstrapped_history)
            all_sharpes.append(_sharpe_from_backtest(sim_result))
            all_win_rates.append(sim_result.win_rate)
            all_pnls.append(sim_result.total_pnl)
            simulations.append({"sharpe": all_sharpes[-1], "win_rate": all_win_rates[-1], "pnl": all_pnls[-1]})
        except Exception as exc:
            logger.warning("Monte Carlo simulation %d failed: %s", _, exc)
            continue

    sharpes = np.array(all_sharpes)
    pnls = np.array(all_pnls)
    win_rates = np.array(all_win_rates)

    result = MonteCarloResult(n_simulations=len(sharpes))
    result.mean_sharpe = float(np.mean(sharpes)) if len(sharpes) > 0 else 0.0
    result.std_sharpe = float(np.std(sharpes)) if len(sharpes) > 1 else 0.0
    result.mean_win_rate = float(np.mean(win_rates)) if len(win_rates) > 0 else 0.0
    result.std_win_rate = float(np.std(win_rates)) if len(win_rates) > 1 else 0.0
    result.mean_total_pnl = float(np.mean(pnls)) if len(pnls) > 0 else 0.0
    result.std_total_pnl = float(np.std(pnls)) if len(pnls) > 1 else 0.0
    result.var_95 = float(np.percentile(pnls, 5)) if len(pnls) > 0 else 0.0
    result.cvar_95 = float(np.mean(pnls[pnls <= np.percentile(pnls, 5)])) if len(pnls[pnls <= np.percentile(pnls, 5)]) > 0 else 0.0
    result.simulations = simulations[:10]
    return result


def _sharpe_from_backtest(result: Any) -> float:
    trades = getattr(result, "trades", [])
    if len(trades) < 2:
        return 0.0
    returns = []
    for t in trades:
        if t.get("type") == "exit":
            pnl = t.get("pnl", 0)
            entry_price = t.get("entry_price", 0.5)
            if entry_price > 0:
                returns.append(pnl / (entry_price * 1000))
    if not returns:
        return 0.0
    mean_r = np.mean(returns)
    std_r = np.std(returns) + 1e-8
    return float(mean_r / std_r * np.sqrt(252))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_pi_monte_carlo.py -v`
Expected: 7 PASSED

---

### Task 4: Experiment Tracker module

**Files:**
- Create: `backend/app/ai/pi_autoresearch/experiment_tracker.py`
- Test: `backend/tests/test_pi_experiment_tracker.py`

- [ ] **Step 1: Write the test file**

Write `backend/tests/test_pi_experiment_tracker.py`:
```python
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from app.ai.pi_autoresearch.experiment_tracker import ExperimentTracker


@pytest.mark.asyncio
async def test_commit_experiment_returns_hash():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        result = {"session_id": "sess-1", "iteration": 1, "hypothesis": "test", "verdict": "KEPT"}
        commit_hash = await tracker.commit_experiment(result)
        assert commit_hash is not None
        assert len(commit_hash) > 0


@pytest.mark.asyncio
async def test_commit_experiment_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        result = {"session_id": "sess-1", "iteration": 1, "hypothesis": "test", "verdict": "KEPT"}
        await tracker.commit_experiment(result)
        exp_dir = Path(tmpdir) / "experiments" / "sess-1"
        assert exp_dir.exists()
        files = list(exp_dir.glob("*.json"))
        assert len(files) >= 1


@pytest.mark.asyncio
async def test_commit_experiment_returns_none_on_failure():
    tracker = ExperimentTracker(repo_path="/nonexistent/path/xyz")
    result = {"session_id": "sess-1", "iteration": 1, "hypothesis": "test", "verdict": "KEPT"}
    commit_hash = await tracker.commit_experiment(result)
    assert commit_hash is None


@pytest.mark.asyncio
async def test_get_experiment_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        await tracker.commit_experiment({"session_id": "s-1", "iteration": 1, "verdict": "KEPT", "hypothesis": "h1"})
        await tracker.commit_experiment({"session_id": "s-1", "iteration": 2, "verdict": "KEPT", "hypothesis": "h2"})
        history = await tracker.get_experiment_history("s-1")
        assert len(history) >= 2
        assert "experiments/s-1/iter_1.json" in history[0]["file"]


@pytest.mark.asyncio
async def test_get_experiment_history_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        history = await tracker.get_experiment_history("nonexistent")
        assert history == []


@pytest.mark.asyncio
async def test_rollback_experiment():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        hash1 = await tracker.commit_experiment({"session_id": "s-1", "iteration": 1, "verdict": "KEPT", "hypothesis": "original"})
        assert hash1 is not None
        hash2 = await tracker.commit_experiment({"session_id": "s-1", "iteration": 2, "verdict": "KEPT", "hypothesis": "modified"})
        assert hash2 is not None
        success = await tracker.rollback_experiment(hash1)
        assert success is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_pi_experiment_tracker.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Experiment Tracker**

Write `backend/app/ai/pi_autoresearch/experiment_tracker.py`:
```python
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentTracker:
    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self._experiments_dir = self.repo_path / "experiments"

    async def commit_experiment(self, experiment_result: dict[str, Any]) -> str | None:
        session_id = experiment_result.get("session_id", "unknown")
        iteration = experiment_result.get("iteration", 0)
        session_dir = self._experiments_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        file_path = session_dir / f"iter_{iteration}.json"
        try:
            file_path.write_text(json.dumps(experiment_result, indent=2, default=str))
            result = subprocess.run(
                ["git", "add", f"experiments/{session_id}/iter_{iteration}.json"],
                cwd=self.repo_path, capture_output=True, text=True,
            )
            if result.returncode != 0:
                return None
            hypothesis = experiment_result.get("hypothesis", "")[:60]
            result = subprocess.run(
                ["git", "commit", "-m", f"experiment: {session_id} iter {iteration} - {hypothesis}"],
                cwd=self.repo_path, capture_output=True, text=True,
            )
            if result.returncode != 0:
                return None
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines:
                if "[" in line and "]" in line:
                    return line.split("]")[-1].strip().split()[0] if line.split("]")[-1].strip() else None
            return None
        except Exception as exc:
            logger.warning("Git commit failed for experiment: %s", exc)
            return None

    async def rollback_experiment(self, commit_hash: str) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", commit_hash, "--", "experiments/"],
                cwd=self.repo_path, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"rollback experiment to {commit_hash[:8]}"],
                cwd=self.repo_path, capture_output=True, text=True,
            )
            return True
        except Exception as exc:
            logger.warning("Git rollback failed: %s", exc)
            return False

    async def get_experiment_history(self, session_id: str) -> list[dict[str, Any]]:
        session_dir = self._experiments_dir / session_id
        if not session_dir.exists():
            return []
        entries: list[dict[str, Any]] = []
        for fpath in sorted(session_dir.glob("iter_*.json")):
            parts = fpath.stem.split("_")
            iteration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            data = json.loads(fpath.read_text())
            entries.append({
                "iteration": iteration,
                "file": str(fpath.relative_to(self.repo_path)),
                "verdict": data.get("verdict", ""),
                "hypothesis": data.get("hypothesis", ""),
                "composite_score": data.get("composite_score", 0.0),
            })
        return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_pi_experiment_tracker.py -v`
Expected: 6 PASSED

---

### Task 5: Hermes Plugin module

**Files:**
- Create: `backend/app/ai/pi_autoresearch/hermes_plugin.py`
- Test: `backend/tests/test_pi_hermes_plugin.py`

- [ ] **Step 1: Write the test file**

Write `backend/tests/test_pi_hermes_plugin.py`:
```python
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from app.ai.pi_autoresearch.hermes_plugin import HermesResearchPlugin


@pytest.mark.asyncio
async def test_propose_hypotheses_unavailable():
    plugin = HermesResearchPlugin()
    result = await plugin.propose_hypotheses(
        climate={"regime": "trending"},
        feature_importance={"odds": 0.5},
        top_features=["odds"],
        n=3,
    )
    assert result == []


@pytest.mark.asyncio
async def test_propose_hypotheses_with_sidecar():
    mock_sidecar = AsyncMock()
    mock_sidecar.available = True
    mock_sidecar.process_message.return_value = {
        "response": "1. Momentum breakout on odds\n2. Mean reversion on volume\n3. Volatility scalp"
    }
    plugin = HermesResearchPlugin(hermes_sidecar=mock_sidecar)
    result = await plugin.propose_hypotheses(
        climate={"regime": "trending"},
        feature_importance={"odds": 0.5, "volume": 0.3},
        top_features=["odds", "volume"],
        n=3,
    )
    assert len(result) >= 1
    assert isinstance(result[0], str)


@pytest.mark.asyncio
async def test_critique_result_unavailable():
    plugin = HermesResearchPlugin()
    result = await plugin.critique_result({"composite_score": 1.2, "verdict": "WARN"})
    assert result == {"critique": "", "suggestions": ""}


@pytest.mark.asyncio
async def test_critique_result_with_sidecar():
    mock_sidecar = AsyncMock()
    mock_sidecar.available = True
    mock_sidecar.process_message.return_value = {
        "response": "The hypothesis is reasonable but the threshold is too aggressive. Consider reducing from 0.6 to 0.55."
    }
    plugin = HermesResearchPlugin(hermes_sidecar=mock_sidecar)
    result = await plugin.critique_result({"composite_score": 1.2, "verdict": "WARN"})
    assert "critique" in result


@pytest.mark.asyncio
async def test_available_property():
    plugin = HermesResearchPlugin()
    assert plugin.available is False
    mock_sidecar = AsyncMock()
    mock_sidecar.available = True
    plugin2 = HermesResearchPlugin(hermes_sidecar=mock_sidecar)
    assert plugin2.available is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_pi_hermes_plugin.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement Hermes Plugin**

Write `backend/app/ai/pi_autoresearch/hermes_plugin.py`:
```python
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HermesResearchPlugin:
    def __init__(self, hermes_sidecar: Any = None):
        self._sidecar = hermes_sidecar

    @property
    def available(self) -> bool:
        if self._sidecar is None:
            return False
        try:
            return bool(self._sidecar.available)
        except Exception:
            return False

    async def propose_hypotheses(
        self,
        climate: dict[str, Any],
        feature_importance: dict[str, float],
        top_features: list[str],
        n: int = 3,
    ) -> list[str]:
        if not self.available:
            return []
        regime = climate.get("regime", "unknown")
        features_str = ", ".join(top_features[:5]) if top_features else "odds"
        prompt = (
            f"Given market regime '{regime}' and top features [{features_str}], "
            f"propose {n} novel prediction market hypotheses. "
            f"Return one hypothesis per line, starting with a number."
        )
        try:
            result = await self._sidecar.process_message(prompt, {"user_id": "research_plugin"})
            response = result.get("response", "")
            lines = [line.strip() for line in response.split("\n") if line.strip() and any(c.isalpha() for c in line)]
            hypotheses = []
            for line in lines:
                cleaned = line.split(". ", 1)[-1] if ". " in line[:4] else line
                hypotheses.append(cleaned)
            return hypotheses[:n]
        except Exception as exc:
            logger.warning("Hermes hypothesis proposal failed: %s", exc)
            return []

    async def critique_result(self, experiment_result: dict[str, Any]) -> dict[str, str]:
        if not self.available:
            return {"critique": "", "suggestions": ""}
        score = experiment_result.get("composite_score", 0.0)
        verdict = experiment_result.get("verdict", "UNKNOWN")
        hypothesis = experiment_result.get("hypothesis", "unknown")
        prompt = (
            f"Critique this experiment result:\n"
            f"Hypothesis: {hypothesis}\n"
            f"Score: {score}\n"
            f"Verdict: {verdict}\n\n"
            f"Suggest improvements for the next iteration."
        )
        try:
            result = await self._sidecar.process_message(prompt, {"user_id": "research_critique"})
            response = result.get("response", "")
            return {
                "critique": response,
                "suggestions": response,
            }
        except Exception as exc:
            logger.warning("Hermes critique failed: %s", exc)
            return {"critique": "", "suggestions": ""}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_pi_hermes_plugin.py -v`
Expected: 5 PASSED

---

### Task 6: Integrate into AutoresearchService

**Files:**
- Modify: `backend/app/ai/autoresearch.py` — full rewrite of `run_iteration`, `_generate_hypotheses`, `_determine_verdict`
- Modify: `backend/app/ai/__init__.py` — export pi_autoresearch package
- Test: `backend/tests/test_research.py` — existing tests should still pass

- [ ] **Step 1: Update `__init__.py` exports**

Edit `backend/app/ai/__init__.py`:
```python
from __future__ import annotations
```

No change needed — it's already empty (the package works by importing directly).

- [ ] **Step 2: Rewrite `autoresearch.py`**

Write `backend/app/ai/autoresearch.py` (full replacement):
```python
from __future__ import annotations

import logging
import random
from typing import Any

import numpy as np

from app.services.backtester import Backtester, BacktestResult
from app.ai.tabpfn_service import TabPFNService
from app.ai.pi_autoresearch.nsgaii import nsga2_optimize
from app.ai.pi_autoresearch.monte_carlo import monte_carlo_backtest
from app.ai.pi_autoresearch.genetic_programming import evolve_population

logger = logging.getLogger(__name__)

HYPOTHESIS_TEMPLATES = [
    {
        "template": "Momentum breakout on {feature}",
        "params": {"feature": "odds_momentum_3h", "operator": "gt", "threshold_range": (0.55, 0.75)},
        "regime_affinity": ["trending"],
    },
    {
        "template": "Mean reversion on {feature}",
        "params": {"feature": "odds_deviation", "operator": "gt", "threshold_range": (0.08, 0.2)},
        "regime_affinity": ["ranging", "calm"],
    },
    {
        "template": "Volatility contraction entry on {feature}",
        "params": {"feature": "volatility_20h", "operator": "lt", "threshold_range": (0.02, 0.06)},
        "regime_affinity": ["calm", "ranging"],
    },
    {
        "template": "Volume spike confirmation on {feature}",
        "params": {"feature": "volume_spike_ratio", "operator": "gt", "threshold_range": (1.5, 3.0)},
        "regime_affinity": ["volatile", "trending"],
    },
    {
        "template": "Spread contraction scalp on {feature}",
        "params": {"feature": "spread_width", "operator": "lt", "threshold_range": (0.01, 0.04)},
        "regime_affinity": ["calm", "ranging"],
    },
]


class AutoresearchService:
    def __init__(
        self,
        tabpfn_service: TabPFNService | None = None,
        experiment_tracker: Any = None,
        hermes_plugin: Any = None,
    ):
        self.tabpfn = tabpfn_service or TabPFNService()
        self.experiment_tracker = experiment_tracker
        self.hermes_plugin = hermes_plugin

    async def run_iteration(
        self,
        strategy_id: str,
        market_history: list[dict[str, Any]],
        climate: dict[str, Any],
        feature_importance: dict[str, float] | None = None,
        alpha_vector: dict[str, Any] | None = None,
        past_results: list[dict[str, Any]] | None = None,
        preset: str = "sharpe_max",
        session_id: str | None = None,
        enable_genetic: bool = False,
    ) -> dict[str, Any]:
        hypotheses = await self._generate_hypotheses(
            climate=climate,
            feature_importance=feature_importance or {},
            alpha_vector=alpha_vector,
            past_results=past_results or [],
            enable_genetic=enable_genetic,
        )

        market_snapshot = market_history[-1] if market_history else {"current_odds": 0.5}
        surviving = await self._quick_rejection(hypotheses, market_snapshot)

        if not surviving:
            return {
                "iteration": -1,
                "hypothesis": "No hypothesis passed quick rejection",
                "verdict": "SKIPPED",
                "composite_score": 0.0,
                "mc_result": None,
                "pareto_front": [],
            }

        best = surviving[0]
        mc_result = await monte_carlo_backtest(
            {"threshold": best["threshold"], "operator": best["operator"], "side": "yes"},
            market_history,
            n=50,
        )

        tabpfn_features = self._build_feature_vector(market_snapshot, climate, best)
        tabpfn_result = await self.tabpfn.validate_signal(
            market_data=market_snapshot,
            regime_vector=[climate.get("metrics", {}).get("volatility", 0.5)],
        )

        objectives = [
            mc_result.mean_sharpe,
            mc_result.mean_win_rate,
            -abs(mc_result.var_95),
            tabpfn_result.get("probability", 0.5),
        ]
        ranked = nsga2_optimize(
            [{"hypothesis": best, "threshold": best["threshold"], "operator": best["operator"]}],
            [objectives],
        )

        pareto_rank = ranked[0].rank if ranked else 0
        composite_score = float(np.mean([abs(o) for o in objectives]))
        verdict = self._determine_verdict(composite_score, pareto_rank)

        git_commit_hash = None
        if verdict == "KEPT" and self.experiment_tracker and session_id:
            try:
                exp_result = {
                    "session_id": session_id,
                    "iteration": 1,
                    "hypothesis": best.get("description", "unknown"),
                    "composite_score": composite_score,
                    "verdict": verdict,
                    "mc_stats": mc_result.to_dict(),
                    "pareto_rank": pareto_rank,
                }
                git_commit_hash = await self.experiment_tracker.commit_experiment(exp_result)
            except Exception as exc:
                logger.warning("Experiment commit failed: %s", exc)

        hermes_critique = None
        if self.hermes_plugin and self.hermes_plugin.available:
            try:
                hermes_critique = await self.hermes_plugin.critique_result({
                    "hypothesis": best.get("description", "unknown"),
                    "composite_score": composite_score,
                    "verdict": verdict,
                })
            except Exception as exc:
                logger.warning("Hermes critique failed: %s", exc)

        return {
            "iteration": 1,
            "hypothesis": best.get("description", "unknown"),
            "hypothesis_prompt": "",
            "backtest_config": {"threshold": best["threshold"], "operator": best["operator"]},
            "backtest_trades": 0,
            "backtest_win_rate": round(mc_result.mean_win_rate, 4),
            "backtest_sharpe": round(mc_result.mean_sharpe, 4),
            "backtest_max_drawdown": round(abs(mc_result.var_95), 4),
            "backtest_total_pnl": round(mc_result.mean_total_pnl, 2),
            "tabpfn_probability": tabpfn_result.get("probability", 0.5),
            "tabpfn_confidence": tabpfn_result.get("confidence", 0.0),
            "composite_score": round(composite_score, 4),
            "verdict": verdict,
            "git_commit_hash": git_commit_hash,
            "mc_result": mc_result.to_dict(),
            "mc_var_95": round(mc_result.var_95, 4),
            "mc_cvar_95": round(mc_result.cvar_95, 4),
            "pareto_rank": pareto_rank,
            "hermes_critique": hermes_critique,
        }

    async def _generate_hypotheses(
        self,
        climate: dict[str, Any],
        feature_importance: dict[str, float],
        alpha_vector: dict[str, Any] | None = None,
        past_results: list[dict[str, Any]] | None = None,
        enable_genetic: bool = False,
        n: int = 5,
    ) -> list[dict[str, Any]]:
        regime = climate.get("regime", "calm")
        top_features = sorted(feature_importance.items(), key=lambda x: -x[1])[:3] if feature_importance else []
        top_feature_names = [f[0] for f in top_features]

        kept_count = len([r for r in (past_results or []) if r.get("verdict") == "KEPT"])
        if enable_genetic and kept_count >= 2 and top_feature_names:
            return evolve_population(
                past_results=past_results or [],
                top_features=top_feature_names,
                pop_size=n,
            )

        matched_templates = [
            t for t in HYPOTHESIS_TEMPLATES
            if regime in t["regime_affinity"] or "calm" in t["regime_affinity"]
        ]
        if not matched_templates:
            matched_templates = HYPOTHESIS_TEMPLATES

        selected = random.sample(matched_templates, min(n, len(matched_templates)))
        hypotheses = []
        for t in selected:
            lo, hi = t["params"]["threshold_range"]
            threshold = round(random.uniform(lo, hi), 3)
            hypotheses.append({
                "description": t["template"].format(feature=top_feature_names[0] if top_feature_names else "odds"),
                "operator": t["params"]["operator"],
                "threshold": threshold,
                "regime_affinity": t["regime_affinity"],
            })

        if self.hermes_plugin and self.hermes_plugin.available:
            try:
                hermes_hypotheses = await self.hermes_plugin.propose_hypotheses(
                    climate=climate,
                    feature_importance=feature_importance,
                    top_features=top_feature_names,
                    n=2,
                )
                for h in hermes_hypotheses:
                    hypotheses.append({
                        "description": h,
                        "operator": random.choice(["gt", "lt"]),
                        "threshold": round(random.uniform(0.4, 0.7), 3),
                        "regime_affinity": [regime],
                    })
            except Exception as exc:
                logger.warning("Hermes hypothesis generation failed: %s", exc)

        return hypotheses

    async def _quick_rejection(
        self,
        hypotheses: list[dict[str, Any]],
        market_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        surviving = []
        for h in hypotheses:
            try:
                features = self._build_feature_vector(market_snapshot, {}, h)
                df = _dict_to_df(features)
                prob = await self.tabpfn.predict_probability(df)
                if prob >= 0.55:
                    surviving.append(h)
            except Exception as exc:
                logger.warning("Quick rejection failed for hypothesis %s: %s", h.get("description"), exc)
                surviving.append(h)
        return surviving

    def _build_feature_vector(
        self,
        market_snapshot: dict[str, Any],
        climate: dict[str, Any],
        hypothesis: dict[str, Any],
    ) -> dict[str, float]:
        vector = {
            "odds": market_snapshot.get("current_odds", 0.5),
            "volume": market_snapshot.get("volume", 0) / 1_000_000,
            "liquidity": market_snapshot.get("liquidity", 0) / 1_000_000,
            "spread": (market_snapshot.get("ask", 0) or 0) - (market_snapshot.get("bid", 0) or 0),
            "participants": market_snapshot.get("participants", 0) / 1000,
            "hypothesis_threshold": hypothesis.get("threshold", 0.5),
        }
        metrics = climate.get("metrics", {})
        vector["volatility"] = metrics.get("volatility", 0.5)
        vector["autocorrelation"] = metrics.get("autocorrelation", 0.0)
        return vector

    def _compute_composite_score(
        self,
        backtest_result: BacktestResult,
        tabpfn_result: dict[str, Any],
        preset: str = "sharpe_max",
    ) -> float:
        win_rate = backtest_result.win_rate
        sharpe = self._sharpe_approximation(backtest_result)
        tabpfn_prob = tabpfn_result.get("probability", 0.5)
        if preset == "sharpe_max":
            return 0.7 * sharpe + 0.3 * tabpfn_prob
        elif preset == "win_rate_max":
            return 0.7 * win_rate + 0.3 * tabpfn_prob
        elif preset == "risk_adjusted":
            max_dd = 0.15
            dd_penalty = 1.0 - max_dd
            return 0.4 * sharpe + 0.3 * dd_penalty + 0.3 * tabpfn_prob
        return 0.7 * sharpe + 0.3 * tabpfn_prob

    def _sharpe_approximation(self, result: BacktestResult) -> float:
        if result.total_trades < 2:
            return 0.0
        returns = []
        for t in result.trades:
            if t.get("type") == "exit":
                pnl = t.get("pnl", 0)
                entry_price = t.get("entry_price", 0.5)
                if entry_price > 0:
                    returns.append(pnl / (entry_price * 1000))
        if not returns:
            return 0.0
        mean_r = np.mean(returns)
        std_r = np.std(returns) + 1e-8
        return float(mean_r / std_r * np.sqrt(252))

    def _determine_verdict(self, score: float, pareto_rank: int = 0) -> str:
        if pareto_rank == 0 and score >= 1.0:
            return "KEPT"
        elif pareto_rank <= 1 and score >= 0.6:
            return "WARN"
        return "REVERTED"


def _dict_to_df(d: dict[str, float]):
    import pandas as pd
    return pd.DataFrame([d])
```

- [ ] **Step 3: Run existing tests to verify they still pass**

Run: `python -m pytest backend/tests/test_research.py -v`
Expected: all existing tests pass (some may need minor adjusts for new return fields; fix any failures)

- [ ] **Step 4: Run all scheduler and websocket tests**

Run: `python -m pytest backend/tests/test_research_scheduler_api.py backend/tests/test_research_websocket.py backend/tests/test_research_e2e.py -v`
Expected: all pass

---

### Task 7: Frontend IterationChart component

**Files:**
- Create: `frontend/src/components/research/IterationChart.tsx`
- Modify: `frontend/src/pages/ResearchPage.tsx` — add chart below table
- Create: `frontend/src/components/research/IterationChart.test.tsx`

- [ ] **Step 1: Write the test file**

Write `frontend/src/components/research/IterationChart.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IterationChart } from './IterationChart'

const sampleResults = [
  { iteration: 1, composite_score: 0.8, backtest_sharpe: 0.6, backtest_win_rate: 0.55, verdict: 'WARN' },
  { iteration: 2, composite_score: 1.2, backtest_sharpe: 0.9, backtest_win_rate: 0.6, verdict: 'KEPT' },
  { iteration: 3, composite_score: 0.4, backtest_sharpe: 0.3, backtest_win_rate: 0.4, verdict: 'REVERTED' },
]

describe('IterationChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<IterationChart results={sampleResults} />)
    expect(container).toBeTruthy()
  })

  it('renders chart title', () => {
    render(<IterationChart results={sampleResults} />)
    expect(screen.getByText('Performance Trends')).toBeTruthy()
  })

  it('shows empty state when no results', () => {
    render(<IterationChart results={[]} />)
    expect(screen.getByText('No iteration data for chart')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Implement IterationChart component**

Write `frontend/src/components/research/IterationChart.tsx`:
```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface ResultItem {
  iteration: number
  composite_score: number
  backtest_sharpe: number
  backtest_win_rate: number
  verdict: string
}

interface IterationChartProps {
  results: ResultItem[]
}

export function IterationChart({ results }: IterationChartProps) {
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
        <p className="text-sm text-gray-500">No iteration data for chart</p>
      </div>
    )
  }

  const data = [...results]
    .sort((a, b) => a.iteration - b.iteration)
    .map((r) => ({
      iteration: r.iteration,
      Score: r.composite_score,
      Sharpe: r.backtest_sharpe,
      'Win Rate': r.backtest_win_rate,
    }))

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-300">Performance Trends</h2>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="iteration" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
          <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#F9FAFB' }}
          />
          <Legend />
          <Line type="monotone" dataKey="Score" stroke="#F9FAFB" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Sharpe" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Win Rate" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 3: Integrate into ResearchPage**

Edit `frontend/src/pages/ResearchPage.tsx`. Add import at top:
```tsx
import { IterationChart } from '@/components/research/IterationChart'
```

Add below the iteration history table (after the table closing `</tbody></table></div>` block, before the `)}` line):
```tsx
              <div className="mt-4">
                <IterationChart results={results} />
              </div>
```

The placement: after line 239 (`</tbody></table></div>`), before `)}` on line 240.

- [ ] **Step 4: Run frontend tests**

Run: `npx vitest run --reporter verbose` (from frontend directory)
Expected: all tests pass including the new IterationChart tests

---

### Task 8: Final verification

**Files:**
- Test: all test files

- [ ] **Step 1: Run all backend tests**

Run: `python -m pytest backend/tests/ -v --tb=short`
Expected: all tests pass (existing 69 + new 26 = ~95)

- [ ] **Step 2: Run all frontend tests**

Run: `npx vitest run --reporter verbose` (from frontend directory)
Expected: all tests pass (existing 13 + new 3 = ~16)
