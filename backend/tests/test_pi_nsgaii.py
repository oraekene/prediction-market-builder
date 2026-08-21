from __future__ import annotations

import pytest

from app.ai.pi_autoresearch.nsgaii import (
    Individual,
    crowding_distance,
    fast_non_dominated_sort,
    nsga2_optimize,
    tournament_selection,
)


class TestIndividual:
    def test_individual_defaults(self):
        ind = Individual(objectives=[1.0, 2.0])
        assert ind.objectives == [1.0, 2.0]
        assert ind.crowding_distance == 0.0
        assert ind.rank == -1
        assert ind.hypothesis == {}


class TestFastNonDominatedSort:
    def test_two_fronts(self):
        a = Individual(objectives=[2.0, 1.0])
        b = Individual(objectives=[1.5, 0.8])
        c = Individual(objectives=[1.0, 0.5])
        fronts = fast_non_dominated_sort([a, b, c])
        assert len(fronts) == 3
        assert len(fronts[0]) == 1
        assert fronts[0][0] is a
        assert fronts[1][0] is b
        assert fronts[2][0] is c

    def test_incomparable(self):
        a = Individual(objectives=[1.0, 2.0])
        b = Individual(objectives=[0.3, 1.0])
        c = Individual(objectives=[0.9, 2.2])
        fronts = fast_non_dominated_sort([a, b, c])
        assert len(fronts) >= 2
        assert len(fronts[0]) == 2
        assert len(fronts[1]) == 1
        for ind in fronts[0]:
            assert ind.rank == 0
        assert fronts[1][0].rank == 1


class TestCrowdingDistance:
    def test_boundary(self):
        front = [
            Individual(objectives=[0.0, 0.0]),
            Individual(objectives=[0.5, 0.5]),
            Individual(objectives=[1.0, 1.0]),
        ]
        crowding_distance(front)
        assert front[0].crowding_distance == float("inf")
        assert front[-1].crowding_distance == float("inf")
        assert front[1].crowding_distance >= 0.0


class TestTournamentSelection:
    def test_rank(self):
        best = Individual(objectives=[2.0, 2.0], rank=0)
        mid = Individual(objectives=[1.5, 1.5], rank=1)
        decent = Individual(objectives=[1.0, 1.0], rank=2)
        worst = Individual(objectives=[0.0, 0.0], rank=3)
        population = [worst, decent, mid, best]
        best_wins = 0
        for _ in range(100):
            selected = tournament_selection(population, k=2)
            if selected.rank == 0:
                best_wins += 1
                assert selected == best
            else:
                assert selected.rank > 0
        assert best_wins >= 20

    def test_crowding_distance_tiebreaker(self):
        same_rank = 0
        high_dist = Individual(objectives=[0.0, 0.0], rank=same_rank, crowding_distance=float("inf"))
        low_dist = Individual(objectives=[1.0, 1.0], rank=same_rank, crowding_distance=0.5)
        selected = tournament_selection([high_dist, low_dist], k=2)
        assert selected == high_dist

    def test_tournament_selection_crowding_distance(self):
        same_rank = 0
        candidates = [
            Individual(objectives=[0.0, 0.0], rank=same_rank, crowding_distance=0.1),
            Individual(objectives=[0.2, 0.2], rank=same_rank, crowding_distance=2.0),
            Individual(objectives=[0.5, 0.5], rank=same_rank, crowding_distance=0.5),
            Individual(objectives=[1.0, 1.0], rank=same_rank, crowding_distance=10.0),
        ]
        highest = candidates[3]
        high_dist_wins = 0
        for _ in range(100):
            selected = tournament_selection(candidates, k=2)
            if selected.crowding_distance == highest.crowding_distance:
                high_dist_wins += 1
                assert selected == highest
            else:
                assert selected.crowding_distance < highest.crowding_distance
        assert high_dist_wins >= 20


class TestNSGA2Optimize:
    def test_basic(self):
        hypotheses = [
            {"name": "A", "alpha": 1.0},
            {"name": "B", "alpha": 0.5},
            {"name": "C", "alpha": 0.1},
        ]
        objectives_matrix = [
            [1.0, 0.8, 0.6, 0.4],
            [0.7, 0.6, 0.5, 0.3],
            [0.2, 0.3, 0.4, 0.1],
        ]
        result = nsga2_optimize(hypotheses, objectives_matrix)
        assert len(result) == 3
        for ind in result:
            assert "pareto_rank" in ind.hypothesis
            assert "crowding_distance" in ind.hypothesis
            assert isinstance(ind.objectives, list)

    def test_empty(self):
        result = nsga2_optimize([], [])
        assert result == []

    def test_single(self):
        hypotheses = [{"name": "only"}]
        objectives_matrix = [[0.5, 0.5]]
        result = nsga2_optimize(hypotheses, objectives_matrix)
        assert len(result) == 1
        assert result[0].rank == 0
        assert result[0].crowding_distance == float("inf")
        assert result[0].hypothesis["pareto_rank"] == 0
        assert result[0].hypothesis["crowding_distance"] == float("inf")
