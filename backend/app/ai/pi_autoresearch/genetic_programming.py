from __future__ import annotations

import copy
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
            "template": self.template,
            "feature": self.feature,
            "operator": self.operator,
            "threshold": self.threshold,
            "regime_affinity": self.regime_affinity.copy(),
            "composite_score": self.composite_score,
        }


def mutation(
    ind: HypothesisIndividual,
    mutation_rate: float = 0.3,
    top_features: list[str] | None = None,
) -> HypothesisIndividual:
    result = copy.deepcopy(ind)
    if random.random() > mutation_rate:
        return result
    result.threshold = round(
        max(0.0, min(1.0, result.threshold + random.uniform(-0.05, 0.05))), 3
    )
    if random.random() < 0.3:
        result.operator = "lt" if result.operator == "gt" else "gt"
    if top_features and random.random() < 0.2:
        result.feature = random.choice(top_features)
    if random.random() < 0.1:
        available = [t for t in HYPOTHESIS_TEMPLATES if t != result.template]
        if available:
            result.template = random.choice(available)
    return result


def crossover(
    parent_a: HypothesisIndividual,
    parent_b: HypothesisIndividual,
    crossover_rate: float = 0.7,
) -> tuple[HypothesisIndividual, HypothesisIndividual]:
    if random.random() > crossover_rate:
        return copy.deepcopy(parent_a), copy.deepcopy(parent_b)
    child_a = HypothesisIndividual(
        template=parent_a.template,
        feature=parent_a.feature,
        operator=parent_b.operator,
        threshold=parent_b.threshold,
        regime_affinity=parent_a.regime_affinity.copy(),
        composite_score=0.0,
    )
    child_b = HypothesisIndividual(
        template=parent_b.template,
        feature=parent_b.feature,
        operator=parent_a.operator,
        threshold=parent_a.threshold,
        regime_affinity=parent_b.regime_affinity.copy(),
        composite_score=0.0,
    )
    return child_a, child_b


def tournament_select(
    population: list[HypothesisIndividual], k: int = 3
) -> HypothesisIndividual:
    candidates = random.sample(population, min(k, len(population)))
    return max(candidates, key=lambda ind: ind.composite_score)


def evolve_population(
    past_results: list[dict[str, Any]],
    top_features: list[str],
    pop_size: int = 10,
    elite_size: int = 2,
) -> list[dict[str, Any]]:
    def _to_individual(r: dict[str, Any]) -> HypothesisIndividual:
        backtest_config = r.get("backtest_config") or {}
        return HypothesisIndividual(
            template=r.get("template") or random.choice(HYPOTHESIS_TEMPLATES),
            feature=r.get("feature") or (top_features[0] if top_features else "odds"),
            operator=r.get("operator") or backtest_config.get("operator", "gt"),
            threshold=r.get("threshold", backtest_config.get("threshold", 0.5)),
            regime_affinity=r.get("regime_affinity", []),
            composite_score=r.get("composite_score", 0.0),
        )

    kept = [
        r for r in past_results if r.get("verdict") == "KEPT"
    ]
    elite = [_to_individual(r) for r in kept[:elite_size]]
    all_past_individuals = [
        _to_individual(r)
        for r in past_results
        if r.get("verdict") != "KEPT"
    ]
    result: list[HypothesisIndividual] = list(elite)
    while len(result) < pop_size:
        if len(all_past_individuals) >= 2:
            parent_a = tournament_select(all_past_individuals)
            parent_b = tournament_select(all_past_individuals)
            child_a, child_b = crossover(parent_a, parent_b)
            child_a = mutation(child_a, top_features=top_features)
            child_b = mutation(child_b, top_features=top_features)
            result.append(child_a)
            if len(result) < pop_size:
                result.append(child_b)
        else:
            template = random.choice(HYPOTHESIS_TEMPLATES)
            feature = random.choice(top_features)
            operator = random.choice(OPERATORS)
            threshold = round(random.random(), 3)
            result.append(
                HypothesisIndividual(
                    template=template,
                    feature=feature,
                    operator=operator,
                    threshold=threshold,
                )
            )
    return [ind.to_dict() for ind in result]
