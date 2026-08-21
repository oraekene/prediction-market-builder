from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HypothesisGene(BaseModel):
    entry_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    exit_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    position_size: float = Field(default=0.25, ge=0.0, le=1.0)
    stop_loss: float = Field(default=0.1, ge=0.0, le=1.0)
    take_profit: float = Field(default=0.3, ge=0.0, le=1.0)
    lookback_window: int = Field(default=24, ge=1, le=100)
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    max_holding_period: int = Field(default=48, ge=1, le=72)
    regime_filter: int = Field(default=0, ge=0, le=4)
    signal_source: int = Field(default=0, ge=0, le=3)


@dataclass
class Individual:
    gene: HypothesisGene
    objectives: list[float] = field(default_factory=list)
    rank: int = -1
    crowding_distance: float = 0.0

    def dominates(self, other: Individual) -> bool:
        better_in_any = False
        for a, b in zip(self.objectives, other.objectives):
            if a < b:
                return False
            if a > b:
                better_in_any = True
        return better_in_any


class NSGAIIOptimizer:
    def __init__(
        self,
        population_size: int = 50,
        generations: int = 20,
        crossover_eta: float = 15.0,
        mutation_eta: float = 20.0,
        mutation_rate: float = 0.1,
        elite_ratio: float = 0.2,
    ):
        self.population_size = population_size
        self.generations = generations
        self.crossover_eta = crossover_eta
        self.mutation_eta = mutation_eta
        self.mutation_rate = mutation_rate
        self.elite_ratio = elite_ratio

    def initialize_population(self, seed_genes: list[HypothesisGene] | None = None) -> list[Individual]:
        pop: list[Individual] = []
        if seed_genes:
            for g in seed_genes:
                pop.append(Individual(gene=g))
        while len(pop) < self.population_size:
            pop.append(Individual(gene=self._random_gene()))
        return pop[: self.population_size]

    def evolve(
        self,
        population: list[Individual],
    ) -> list[Individual]:
        n = len(population)
        fronts = self._non_dominated_sort(population)
        for front in fronts:
            self._crowding_distance(front)

        offspring = []
        while len(offspring) < n:
            p1 = self._tournament_selection(population)
            p2 = self._tournament_selection(population)
            if random.random() < 0.9:
                c1, c2 = self._sbx_crossover(p1.gene, p2.gene)
                offspring.append(Individual(gene=self._polynomial_mutation(c1)))
                offspring.append(Individual(gene=self._polynomial_mutation(c2)))
            else:
                offspring.append(Individual(gene=self._polynomial_mutation(p1.gene)))
                offspring.append(Individual(gene=self._polynomial_mutation(p2.gene)))

        combined = population + offspring[:n]
        combined_fronts = self._non_dominated_sort(combined)
        for front in combined_fronts:
            self._crowding_distance(front)

        next_pop: list[Individual] = []
        for front in combined_fronts:
            if len(next_pop) + len(front) <= n:
                next_pop.extend(front)
            else:
                front.sort(key=lambda ind: -ind.crowding_distance)
                remaining = n - len(next_pop)
                next_pop.extend(front[:remaining])
                break

        return next_pop

    def _random_gene(self) -> HypothesisGene:
        return HypothesisGene(
            entry_threshold=random.uniform(0.3, 0.8),
            exit_threshold=random.uniform(0.3, 0.8),
            position_size=random.uniform(0.05, 0.5),
            stop_loss=random.uniform(0.02, 0.2),
            take_profit=random.uniform(0.1, 0.5),
            lookback_window=random.randint(4, 96),
            min_confidence=random.uniform(0.4, 0.9),
            max_holding_period=random.randint(4, 72),
            regime_filter=random.randint(0, 4),
            signal_source=random.randint(0, 3),
        )

    def _non_dominated_sort(self, population: list[Individual]) -> list[list[Individual]]:
        n = len(population)
        domination_count = [0] * n
        dominated_sets: list[list[int]] = [[] for _ in range(n)]
        fronts: list[list[Individual]] = []

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if population[i].dominates(population[j]):
                    dominated_sets[i].append(j)
                elif population[j].dominates(population[i]):
                    domination_count[i] += 1
            if domination_count[i] == 0:
                population[i].rank = 0

        current_front = [i for i in range(n) if domination_count[i] == 0]
        front_idx = 0

        while current_front:
            front_individuals = [population[i] for i in current_front]
            for ind in front_individuals:
                ind.rank = front_idx
            fronts.append(front_individuals)

            next_front: list[int] = []
            for i in current_front:
                for j in dominated_sets[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            current_front = next_front
            front_idx += 1

        return fronts

    def _crowding_distance(self, front: list[Individual]) -> None:
        evaluated = [ind for ind in front if ind.objectives]
        unevaluated = [ind for ind in front if not ind.objectives]
        for ind in unevaluated:
            ind.crowding_distance = 0.0

        n = len(evaluated)
        if n <= 2:
            for ind in evaluated:
                ind.crowding_distance = float("inf")
            return

        for ind in evaluated:
            ind.crowding_distance = 0.0

        n_objectives = len(evaluated[0].objectives)
        for obj_idx in range(n_objectives):
            evaluated.sort(key=lambda ind, oi=obj_idx: ind.objectives[oi])
            obj_min = evaluated[0].objectives[obj_idx]
            obj_max = evaluated[-1].objectives[obj_idx]
            obj_range = obj_max - obj_min
            if obj_range == 0:
                continue
            evaluated[0].crowding_distance = float("inf")
            evaluated[-1].crowding_distance = float("inf")
            for i in range(1, n - 1):
                diff = evaluated[i + 1].objectives[obj_idx] - evaluated[i - 1].objectives[obj_idx]
                evaluated[i].crowding_distance += diff / obj_range

    def _tournament_selection(self, population: list[Individual]) -> Individual:
        a = random.choice(population)
        b = random.choice(population)
        if a.rank < b.rank:
            return a
        if b.rank < a.rank:
            return b
        return a if a.crowding_distance > b.crowding_distance else b

    def _sbx_crossover(
        self,
        parent1: HypothesisGene,
        parent2: HypothesisGene,
    ) -> tuple[HypothesisGene, HypothesisGene]:
        child1 = parent1.model_copy(deep=True)
        child2 = parent2.model_copy(deep=True)

        for field_name in HypothesisGene.model_fields:
            val1 = getattr(parent1, field_name)
            val2 = getattr(parent2, field_name)
            if random.random() > 0.5:
                continue
            if isinstance(val1, (int, float)):
                beta = self._calculate_beta(self.crossover_eta)
                new_val1 = 0.5 * ((1 + beta) * val1 + (1 - beta) * val2)
                new_val2 = 0.5 * ((1 - beta) * val1 + (1 + beta) * val2)
                self._clamp_gene_field(child1, field_name, new_val1)
                self._clamp_gene_field(child2, field_name, new_val2)

        return child1, child2

    def _calculate_beta(self, eta: float) -> float:
        u = random.random()
        if u <= 0.5:
            return (2 * u) ** (1.0 / (eta + 1))
        return (1.0 / (2 * (1 - u))) ** (1.0 / (eta + 1))

    def _polynomial_mutation(self, gene: HypothesisGene) -> HypothesisGene:
        mutated = gene.model_copy(deep=True)
        for field_name in HypothesisGene.model_fields:
            if random.random() > self.mutation_rate:
                continue
            val = getattr(mutated, field_name)
            if isinstance(val, (int, float)):
                r = random.random()
                if r < 0.5:
                    delta = (2 * r) ** (1.0 / (self.mutation_eta + 1)) - 1
                else:
                    delta = 1 - (2 * (1 - r)) ** (1.0 / (self.mutation_eta + 1))
                new_val = val + delta * val if val != 0 else delta * 0.1
                self._clamp_gene_field(mutated, field_name, new_val)
        return mutated

    def _clamp_gene_field(self, gene: HypothesisGene, field_name: str, value: float) -> None:
        field_info = HypothesisGene.model_fields[field_name]
        ge = next((m.ge for m in field_info.metadata if hasattr(m, "ge")), None)
        le = next((m.le for m in field_info.metadata if hasattr(m, "le")), None)
        if isinstance(getattr(gene, field_name), int):
            clamped = int(round(value))
            if ge is not None:
                clamped = max(clamped, int(ge))
            if le is not None:
                clamped = min(clamped, int(le))
            setattr(gene, field_name, clamped)
        else:
            if ge is not None:
                value = max(value, float(ge))
            if le is not None:
                value = min(value, float(le))
            setattr(gene, field_name, value)

    def to_hypothesis_dict(self, gene: HypothesisGene) -> dict[str, Any]:
        return {
            "description": (
                f"GA: entry={gene.entry_threshold:.2f} exit={gene.exit_threshold:.2f} "
                f"size={gene.position_size:.2f} sl={gene.stop_loss:.2f} tp={gene.take_profit:.2f} "
                f"lookback={gene.lookback_window}h conf={gene.min_confidence:.2f} "
                f"hold={gene.max_holding_period}h regime={gene.regime_filter} src={gene.signal_source}"
            ),
            "operator": "gt",
            "threshold": gene.entry_threshold,
            "entry_threshold": gene.entry_threshold,
            "exit_threshold": gene.exit_threshold,
            "position_size": gene.position_size,
            "stop_loss": gene.stop_loss,
            "take_profit": gene.take_profit,
            "lookback_window": gene.lookback_window,
            "min_confidence": gene.min_confidence,
            "max_holding_period": gene.max_holding_period,
            "regime_filter": gene.regime_filter,
            "signal_source": gene.signal_source,
            "regime_affinity": ["trending", "ranging", "volatile", "calm"],
        }

    def from_hypothesis_dict(self, hypothesis: dict[str, Any]) -> HypothesisGene:
        return HypothesisGene(
            entry_threshold=hypothesis.get("entry_threshold", hypothesis.get("threshold", 0.5)),
            exit_threshold=hypothesis.get("exit_threshold", 0.5),
            position_size=hypothesis.get("position_size", 0.25),
            stop_loss=hypothesis.get("stop_loss", 0.1),
            take_profit=hypothesis.get("take_profit", 0.3),
            lookback_window=hypothesis.get("lookback_window", 24),
            min_confidence=hypothesis.get("min_confidence", 0.6),
            max_holding_period=hypothesis.get("max_holding_period", 48),
            regime_filter=hypothesis.get("regime_filter", 0),
            signal_source=hypothesis.get("signal_source", 0),
        )

    def extract_pareto_front(self, population: list[Individual]) -> list[dict[str, Any]]:
        fronts = self._non_dominated_sort(population)
        if not fronts:
            return []
        return [
            {
                "gene": ind.gene.model_dump(),
                "objectives": {
                    "sharpe": ind.objectives[0] if len(ind.objectives) > 0 else 0.0,
                    "win_rate": ind.objectives[1] if len(ind.objectives) > 1 else 0.0,
                    "max_drawdown": ind.objectives[2] if len(ind.objectives) > 2 else 0.0,
                },
                "rank": ind.rank,
                "crowding_distance": ind.crowding_distance,
            }
            for ind in fronts[0]
        ]
