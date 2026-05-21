from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Individual:
    objectives: list[float]
    crowding_distance: float = 0.0
    rank: int = -1
    hypothesis: dict = field(default_factory=dict)


def fast_non_dominated_sort(population: list[Individual]) -> list[list[Individual]]:
    domination_count = [0] * len(population)
    dominated_set: list[list[int]] = [[] for _ in range(len(population))]
    fronts: list[list[int]] = [[]]

    for i, p in enumerate(population):
        for j, q in enumerate(population):
            if i == j:
                continue
            if _dominates(p, q):
                dominated_set[i].append(j)
            elif _dominates(q, p):
                domination_count[i] += 1
        if domination_count[i] == 0:
            fronts[0].append(i)
            population[i].rank = 0

    front_idx = 0
    while fronts[front_idx]:
        next_front: list[int] = []
        for i in fronts[front_idx]:
            for j in dominated_set[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    population[j].rank = front_idx + 1
                    next_front.append(j)
        front_idx += 1
        fronts.append(next_front)

    fronts.pop()

    result: list[list[Individual]] = []
    for front_indices in fronts:
        result.append([population[i] for i in front_indices])
    return result


def _dominates(a: Individual, b: Individual) -> bool:
    """Returns True if a dominates b (assumes maximization — higher is better for all objectives)."""
    at_least_one_better = False
    for av, bv in zip(a.objectives, b.objectives):
        if av < bv:
            return False
        if av > bv:
            at_least_one_better = True
    return at_least_one_better


def crowding_distance(front: list[Individual]) -> None:
    if len(front) <= 2:
        for ind in front:
            ind.crowding_distance = float("inf")
        return

    n_objectives = len(front[0].objectives)
    for ind in front:
        ind.crowding_distance = 0.0

    for m in range(n_objectives):
        front.sort(key=lambda ind, m=m: ind.objectives[m])
        min_val = front[0].objectives[m]
        max_val = front[-1].objectives[m]
        obj_range = max_val - min_val

        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")

        if obj_range == 0:
            continue

        for i in range(1, len(front) - 1):
            front[i].crowding_distance += (
                front[i + 1].objectives[m] - front[i - 1].objectives[m]
            ) / obj_range


def tournament_selection(
    population: list[Individual], k: int = 2
) -> Individual:
    selected = random.sample(population, k)
    winner = selected[0]
    for contender in selected[1:]:
        if contender.rank < winner.rank:
            winner = contender
        elif contender.rank == winner.rank and contender.crowding_distance > winner.crowding_distance:
            winner = contender
    return winner


def nsga2_optimize(
    hypotheses: list[dict], objectives_matrix: list[list[float]]
) -> list[Individual]:
    if not hypotheses or not objectives_matrix:
        return []

    population = [
        Individual(
            objectives=objectives_matrix[i],
            hypothesis=hypotheses[i],
        )
        for i in range(len(hypotheses))
    ]

    fronts = fast_non_dominated_sort(population)
    for front in fronts:
        crowding_distance(front)

    for ind in population:
        ind.hypothesis["pareto_rank"] = ind.rank
        ind.hypothesis["crowding_distance"] = ind.crowding_distance

    return population
