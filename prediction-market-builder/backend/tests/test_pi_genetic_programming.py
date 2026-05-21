from __future__ import annotations

from math import isclose

import pytest

from app.ai.pi_autoresearch.genetic_programming import (
    HypothesisIndividual,
    crossover,
    evolve_population,
    mutation,
    tournament_select,
)


class TestHypothesisIndividual:
    def test_defaults(self):
        ind = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.7,
        )
        assert ind.template == "Momentum breakout on {feature}"
        assert ind.feature == "rsi_14"
        assert ind.operator == "gt"
        assert isclose(ind.threshold, 0.7)
        assert ind.regime_affinity == []
        assert isclose(ind.composite_score, 0.0)
        assert ind.description == "Momentum breakout on rsi_14"

    def test_to_dict(self):
        ind = HypothesisIndividual(
            template="Mean reversion on {feature}",
            feature="bb_width",
            operator="lt",
            threshold=0.3,
            regime_affinity=["ranging"],
            composite_score=0.8,
        )
        d = ind.to_dict()
        assert d["template"] == "Mean reversion on {feature}"
        assert d["feature"] == "bb_width"
        assert d["operator"] == "lt"
        assert isclose(d["threshold"], 0.3)
        assert d["regime_affinity"] == ["ranging"]
        assert isclose(d["composite_score"], 0.8)


class TestMutation:
    def test_perturbs_threshold(self):
        original = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.5,
        )
        changed = False
        for _ in range(50):
            mutated = mutation(original, mutation_rate=1.0, top_features=["rsi_14"])
            if not isclose(mutated.threshold, 0.5, abs_tol=1e-6):
                changed = True
                break
        assert changed, "threshold never changed after 50 mutations"

    def test_preserves_structure_with_zero_rate(self):
        original = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.5,
            regime_affinity=["trending"],
            composite_score=0.9,
        )
        result = mutation(original, mutation_rate=0.0, top_features=["rsi_14"])
        assert result.template == original.template
        assert result.feature == original.feature
        assert result.operator == original.operator
        assert isclose(result.threshold, original.threshold)
        assert result.regime_affinity == original.regime_affinity
        assert isclose(result.composite_score, original.composite_score)

    def test_returns_new_individual(self):
        original = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.5,
        )
        result = mutation(original, mutation_rate=1.0, top_features=["rsi_14"])
        assert result is not original


class TestCrossover:
    def test_swaps_at_full_rate(self):
        parent_a = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.7,
            regime_affinity=["trending"],
        )
        parent_b = HypothesisIndividual(
            template="Mean reversion on {feature}",
            feature="bb_width",
            operator="lt",
            threshold=0.3,
            regime_affinity=["ranging"],
        )
        child_a, child_b = crossover(parent_a, parent_b, crossover_rate=1.0)
        # child_a: template/feature/regime from parent_a, operator/threshold from parent_b
        assert child_a.template == parent_a.template
        assert child_a.feature == parent_a.feature
        assert child_a.regime_affinity == parent_a.regime_affinity
        assert child_a.operator == parent_b.operator
        assert isclose(child_a.threshold, parent_b.threshold)
        # child_b: template/feature/regime from parent_b, operator/threshold from parent_a
        assert child_b.template == parent_b.template
        assert child_b.feature == parent_b.feature
        assert child_b.regime_affinity == parent_b.regime_affinity
        assert child_b.operator == parent_a.operator
        assert isclose(child_b.threshold, parent_a.threshold)

    def test_returns_clones_at_zero_rate(self):
        parent_a = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.7,
        )
        parent_b = HypothesisIndividual(
            template="Mean reversion on {feature}",
            feature="bb_width",
            operator="lt",
            threshold=0.3,
        )
        child_a, child_b = crossover(parent_a, parent_b, crossover_rate=0.0)
        assert child_a.template == parent_a.template
        assert child_a.feature == parent_a.feature
        assert child_a.operator == parent_a.operator
        assert isclose(child_a.threshold, parent_a.threshold)
        assert child_b.template == parent_b.template
        assert child_b.feature == parent_b.feature
        assert child_b.operator == parent_b.operator
        assert isclose(child_b.threshold, parent_b.threshold)


class TestTournamentSelect:
    def test_returns_best_candidate(self):
        best = HypothesisIndividual(
            template="Momentum breakout on {feature}",
            feature="rsi_14",
            operator="gt",
            threshold=0.7,
            composite_score=0.9,
        )
        mid = HypothesisIndividual(
            template="Mean reversion on {feature}",
            feature="bb_width",
            operator="lt",
            threshold=0.3,
            composite_score=0.5,
        )
        worst = HypothesisIndividual(
            template="Volatility contraction entry on {feature}",
            feature="atr",
            operator="gt",
            threshold=0.2,
            composite_score=0.1,
        )
        population = [worst, mid, best]
        wins = 0
        for _ in range(100):
            selected = tournament_select(population, k=3)
            if selected is best:
                wins += 1
            else:
                assert selected.composite_score < best.composite_score
        assert wins >= 20, f"best won only {wins}/100 times"


class TestEvolvePopulation:
    def test_empty_past_generates_hypotheses(self):
        top_features = ["rsi_14", "bb_width", "atr", "volume", "macd"]
        result = evolve_population([], top_features, pop_size=10, elite_size=2)
        assert len(result) >= 5
        for item in result:
            assert "template" in item
            assert "feature" in item
            assert "operator" in item
            assert "threshold" in item
            assert "regime_affinity" in item
            assert "composite_score" in item

    def test_with_past_kept_elite(self):
        past_results = [
            {
                "verdict": "KEPT",
                "template": "Momentum breakout on {feature}",
                "feature": "rsi_14",
                "operator": "gt",
                "threshold": 0.7,
                "regime_affinity": ["trending"],
                "composite_score": 0.9,
            },
            {
                "verdict": "KEPT",
                "template": "Mean reversion on {feature}",
                "feature": "bb_width",
                "operator": "lt",
                "threshold": 0.3,
                "regime_affinity": ["ranging"],
                "composite_score": 0.8,
            },
            {
                "verdict": "DISCARDED",
                "template": "Volatility contraction entry on {feature}",
                "feature": "atr",
                "operator": "gt",
                "threshold": 0.5,
                "regime_affinity": ["calm"],
                "composite_score": 0.2,
            },
        ]
        top_features = ["rsi_14", "bb_width", "atr", "volume", "macd"]
        result = evolve_population(past_results, top_features, pop_size=10, elite_size=2)
        assert len(result) >= 5
        kept_features = {r["feature"] for r in past_results if r["verdict"] == "KEPT"}
        result_features = {r["feature"] for r in result[:2]}
        assert kept_features & result_features, "KEPT past results should be among elite"
