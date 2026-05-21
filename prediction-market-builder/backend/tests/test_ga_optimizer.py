from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.ga_optimizer import NSGAIIOptimizer, HypothesisGene, Individual
from app.ai.mc_sensitivity import MonteCarloSensitivity, MCSensitivityResult


@pytest.fixture
def optimizer():
    return NSGAIIOptimizer(population_size=20, generations=3, mutation_rate=0.2)


@pytest.fixture
def sample_gene():
    return HypothesisGene(
        entry_threshold=0.6,
        exit_threshold=0.4,
        position_size=0.2,
        stop_loss=0.08,
        take_profit=0.35,
        lookback_window=24,
        min_confidence=0.7,
        max_holding_period=48,
        regime_filter=0,
        signal_source=1,
    )


class TestHypothesisGene:
    def test_default_creation(self):
        g = HypothesisGene()
        assert 0.0 <= g.entry_threshold <= 1.0
        assert 1 <= g.lookback_window <= 100
        assert 0 <= g.regime_filter <= 4
        assert 0 <= g.signal_source <= 3

    def test_ge_le_constraints(self):
        with pytest.raises(Exception):
            HypothesisGene(entry_threshold=1.5)
        with pytest.raises(Exception):
            HypothesisGene(lookback_window=0)
        with pytest.raises(Exception):
            HypothesisGene(regime_filter=5)
        with pytest.raises(Exception):
            HypothesisGene(signal_source=-1)

    def test_valid_gene_accepted(self):
        g = HypothesisGene(
            entry_threshold=0.5, exit_threshold=0.5,
            position_size=0.25, stop_loss=0.1, take_profit=0.3,
            lookback_window=24, min_confidence=0.6,
            max_holding_period=48, regime_filter=2, signal_source=1,
        )
        assert g.entry_threshold == 0.5


class TestNSGAIIOptimizer:
    def test_initialize_population_size(self, optimizer):
        pop = optimizer.initialize_population()
        assert len(pop) == optimizer.population_size

    def test_initialize_with_seeds(self, optimizer, sample_gene):
        pop = optimizer.initialize_population(seed_genes=[sample_gene])
        assert len(pop) == optimizer.population_size
        assert pop[0].gene.entry_threshold == 0.6

    def test_initialize_population_all_have_genes(self, optimizer):
        pop = optimizer.initialize_population()
        for ind in pop:
            assert isinstance(ind.gene, HypothesisGene)

    def test_non_dominated_sort_two_objectives(self, optimizer):
        pop = [
            Individual(gene=sample_gene, objectives=[1.0, 0.8]),
            Individual(gene=sample_gene, objectives=[0.5, 0.9]),
            Individual(gene=sample_gene, objectives=[0.3, 0.3]),
        ]
        fronts = optimizer._non_dominated_sort(pop)
        assert len(fronts) >= 1
        assert len(fronts[0]) >= 1

    def test_non_dominated_sort_ranks(self, optimizer):
        pop = [
            Individual(gene=sample_gene, objectives=[1.0, 0.9]),
            Individual(gene=sample_gene, objectives=[0.8, 0.7]),
            Individual(gene=sample_gene, objectives=[0.3, 0.2]),
        ]
        fronts = optimizer._non_dominated_sort(pop)
        assert fronts[0][0].rank == 0

    def test_crowding_distance_infinite_for_edges(self, optimizer):
        front = [
            Individual(gene=sample_gene, objectives=[0.0, 0.0]),
            Individual(gene=sample_gene, objectives=[0.5, 0.5]),
            Individual(gene=sample_gene, objectives=[1.0, 1.0]),
        ]
        optimizer._crowding_distance(front)
        assert front[0].crowding_distance == float("inf")
        assert front[-1].crowding_distance == float("inf")

    def test_tournament_selection_returns_valid(self, optimizer):
        pop = [
            Individual(gene=sample_gene, objectives=[1.0, 1.0], rank=0),
            Individual(gene=sample_gene, objectives=[0.0, 0.0], rank=1),
        ]
        selected = optimizer._tournament_selection(pop)
        assert selected in pop

    def test_sbx_crossover_preserves_gene_type(self, optimizer, sample_gene):
        g1 = HypothesisGene(entry_threshold=0.2, exit_threshold=0.8, position_size=0.4, stop_loss=0.15, take_profit=0.45, lookback_window=12, min_confidence=0.3, max_holding_period=24, regime_filter=1, signal_source=2)
        c1, c2 = optimizer._sbx_crossover(g1, sample_gene)
        assert isinstance(c1, HypothesisGene)
        assert isinstance(c2, HypothesisGene)

    def test_polynomial_mutation_changes_gene(self, optimizer, sample_gene):
        mutated = optimizer._polynomial_mutation(sample_gene)
        assert isinstance(mutated, HypothesisGene)

    def test_evolution_returns_same_size(self, optimizer):
        pop = optimizer.initialize_population()
        for ind in pop:
            ind.objectives = [0.5, 0.5, 0.5]
        next_pop = optimizer.evolve(pop)
        assert len(next_pop) == len(pop)

    def test_extract_pareto_front(self, optimizer, sample_gene):
        pop = [
            Individual(gene=sample_gene, objectives=[1.0, 0.9, 0.8]),
            Individual(gene=sample_gene, objectives=[0.3, 0.4, 0.5]),
        ]
        front = optimizer.extract_pareto_front(pop)
        assert len(front) >= 1
        assert "gene" in front[0]
        assert "objectives" in front[0]
        assert "sharpe" in front[0]["objectives"]

    def test_to_hypothesis_dict_contains_fields(self, optimizer, sample_gene):
        d = optimizer.to_hypothesis_dict(sample_gene)
        assert "description" in d
        assert "threshold" in d
        assert d["entry_threshold"] == 0.6

    def test_from_hypothesis_dict_roundtrip(self, optimizer, sample_gene):
        d = optimizer.to_hypothesis_dict(sample_gene)
        g = optimizer.from_hypothesis_dict(d)
        assert g.entry_threshold == sample_gene.entry_threshold
        assert g.lookback_window == sample_gene.lookback_window


class TestDominance:
    def test_dominates_true(self):
        a = Individual(gene=HypothesisGene(), objectives=[1.0, 0.9, 0.8])
        b = Individual(gene=HypothesisGene(), objectives=[0.5, 0.6, 0.7])
        assert a.dominates(b)
        assert not b.dominates(a)

    def test_dominates_false_equal(self):
        a = Individual(gene=HypothesisGene(), objectives=[0.5, 0.5])
        b = Individual(gene=HypothesisGene(), objectives=[0.5, 0.5])
        assert not a.dominates(b)
        assert not b.dominates(a)

    def test_dominates_false_worse(self):
        a = Individual(gene=HypothesisGene(), objectives=[0.5, 0.5])
        b = Individual(gene=HypothesisGene(), objectives=[0.6, 0.6])
        assert not a.dominates(b)


class TestMonteCarloSensitivity:
    @pytest.mark.asyncio
    async def test_analyze_returns_result(self, sample_gene):
        mc = MonteCarloSensitivity(n_samples=50)
        result = await mc.analyze(sample_gene)
        assert isinstance(result, MCSensitivityResult)
        assert isinstance(result.expected_sharpe, float)
        assert isinstance(result.prob_positive, float)
        assert isinstance(result.recommendation, str)

    @pytest.mark.asyncio
    async def test_analyze_recommendation_not_empty(self, sample_gene):
        mc = MonteCarloSensitivity(n_samples=30)
        result = await mc.analyze(sample_gene)
        assert result.recommendation in ("proceed", "reject", "caution", "unknown")

    @pytest.mark.asyncio
    async def test_sensitive_params_returned(self, sample_gene):
        mc = MonteCarloSensitivity(n_samples=30)
        result = await mc.analyze(sample_gene)
        assert isinstance(result.sensitive_params, list)
        assert len(result.sensitive_params) > 0

    @pytest.mark.asyncio
    async def test_perturb_produces_valid_gene(self, sample_gene):
        mc = MonteCarloSensitivity()
        perturbed = mc._perturb(sample_gene)
        assert isinstance(perturbed, HypothesisGene)
        assert 0.0 <= perturbed.entry_threshold <= 1.0
        assert 1 <= perturbed.lookback_window <= 100
        assert 0 <= perturbed.regime_filter <= 4


class TestAutoresearchGAIntegration:
    @pytest.mark.asyncio
    async def test_enable_genetic_uses_evolve_population(self):
        from app.ai.pi_autoresearch.genetic_programming import evolve_population
        from app.ai.autoresearch import AutoresearchService

        hypothesis = {
            "description": "GP evolved hypothesis",
            "operator": "gt",
            "threshold": 0.55,
            "regime_affinity": ["trending"],
        }
        with patch("app.ai.autoresearch.evolve_population", return_value=[hypothesis]):
            service = AutoresearchService(tabpfn_service=None)
            result = await service._generate_hypotheses(
                climate={"regime": "trending"},
                feature_importance={"odds": 0.8, "volume": 0.2},
                past_results=[
                    {"verdict": "KEPT", "backtest_config": {"operator": "gt"}},
                    {"verdict": "KEPT", "backtest_config": {"operator": "lt"}},
                ],
                enable_genetic=True,
            )
        assert len(result) >= 1
        assert result[0]["description"] == "GP evolved hypothesis"

    @pytest.mark.asyncio
    async def test_enable_genetic_false_uses_templates(self):
        from app.ai.autoresearch import AutoresearchService

        service = AutoresearchService(tabpfn_service=None)
        with patch("app.ai.autoresearch.evolve_population") as mock_evolve:
            result = await service._generate_hypotheses(
                climate={"regime": "trending"},
                feature_importance={"odds": 0.8},
                enable_genetic=False,
            )
        mock_evolve.assert_not_called()
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_run_iteration_returns_new_fields(self):
        from app.ai.autoresearch import AutoresearchService

        hypothesis = {
            "description": "test momentum",
            "operator": "gt",
            "threshold": 0.6,
            "regime_affinity": ["trending"],
        }
        service = AutoresearchService(tabpfn_service=None)
        with patch.object(service, "_generate_hypotheses", return_value=[hypothesis]):
            with patch.object(service.tabpfn, "predict_probability", return_value=0.6):
                with patch("app.ai.autoresearch.monte_carlo_backtest") as mock_mc:
                    mock_mc.return_value.to_dict.return_value = {"mean_sharpe": 0.8}
                    mock_mc.return_value.mean_sharpe = 0.8
                    mock_mc.return_value.mean_win_rate = 0.55
                    mock_mc.return_value.var_95 = -0.02
                    mock_mc.return_value.cvar_95 = -0.05
                    mock_mc.return_value.mean_total_pnl = 100.0
                    with patch.object(service.tabpfn, "validate_signal", return_value={"probability": 0.6, "confidence": 0.3}):
                        result = await service.run_iteration(
                            strategy_id="test",
                            market_history=[{"current_odds": 0.5}],
                            climate={"regime": "trending"},
                        )
        assert "mc_result" in result
        assert "mc_var_95" in result
        assert "mc_cvar_95" in result
        assert "pareto_rank" in result
        assert "hermes_critique" in result
        assert result["mc_var_95"] is not None
