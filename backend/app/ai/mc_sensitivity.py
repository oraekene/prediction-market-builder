from __future__ import annotations

import logging
import math
import random
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ga_optimizer import HypothesisGene

logger = logging.getLogger(__name__)


class MCSensitivityResult(BaseModel):
    expected_sharpe: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    prob_positive: float = 0.0
    sensitive_params: list[str] = Field(default_factory=list)
    recommendation: str = "unknown"


class MonteCarloSensitivity:
    def __init__(self, n_samples: int = 200):
        self.n_samples = n_samples

    async def analyze(
        self,
        hypothesis: HypothesisGene,
        n_samples: int | None = None,
    ) -> MCSensitivityResult:
        n = n_samples or self.n_samples
        sharpes: list[float] = []
        param_contributions: dict[str, list[float]] = {
            "entry_threshold": [],
            "exit_threshold": [],
            "position_size": [],
            "stop_loss": [],
            "take_profit": [],
            "min_confidence": [],
        }

        for _ in range(n):
            variant = self._perturb(hypothesis)
            sharpe = self._quick_simulate(variant)
            sharpes.append(sharpe)
            for param in param_contributions:
                perturbed_val = getattr(variant, param)
                base_val = getattr(hypothesis, param)
                param_contributions[param].append(abs(sharpe) * abs(perturbed_val - base_val + 1e-6))

        sharpes.sort()
        n_s = len(sharpes)
        expected = sum(sharpes) / n_s if n_s > 0 else 0.0
        ci_low = sharpes[int(n_s * 0.05)] if n_s > 1 else 0.0
        ci_high = sharpes[int(n_s * 0.95)] if n_s > 1 else 0.0
        prob_pos = sum(1 for s in sharpes if s > 0) / n_s if n_s > 0 else 0.0

        param_variance = {
            param: sum(vals) / len(vals) if vals else 0.0
            for param, vals in param_contributions.items()
        }
        sorted_params = sorted(param_variance, key=param_variance.__getitem__, reverse=True)
        sensitive = sorted_params[:3]

        if ci_low > 0.2:
            rec = "proceed"
        elif ci_high < 0:
            rec = "reject"
        else:
            rec = "caution"

        return MCSensitivityResult(
            expected_sharpe=round(expected, 4),
            ci_lower=round(ci_low, 4),
            ci_upper=round(ci_high, 4),
            prob_positive=round(prob_pos, 4),
            sensitive_params=sensitive,
            recommendation=rec,
        )

    def _perturb(self, gene: HypothesisGene) -> HypothesisGene:
        return HypothesisGene(
            entry_threshold=self._jitter(gene.entry_threshold, 0.0, 1.0),
            exit_threshold=self._jitter(gene.exit_threshold, 0.0, 1.0),
            position_size=self._jitter(gene.position_size, 0.0, 1.0),
            stop_loss=self._jitter(gene.stop_loss, 0.0, 1.0),
            take_profit=self._jitter(gene.take_profit, 0.0, 1.0),
            lookback_window=self._jitter_int(gene.lookback_window, 1, 100),
            min_confidence=self._jitter(gene.min_confidence, 0.0, 1.0),
            max_holding_period=self._jitter_int(gene.max_holding_period, 1, 72),
            regime_filter=gene.regime_filter,
            signal_source=gene.signal_source,
        )

    def _jitter(self, val: float, lo: float, hi: float, sigma: float = 0.05) -> float:
        noise = random.gauss(0, sigma)
        return max(lo, min(hi, val + noise))

    def _jitter_int(self, val: int, lo: int, hi: int) -> int:
        noise = int(random.gauss(0, max(1, (hi - lo) * 0.05)))
        return max(lo, min(hi, val + noise))

    def _quick_simulate(self, gene: HypothesisGene) -> float:
        base_sharpe = 0.5
        entry_contrib = (gene.entry_threshold - 0.5) * 0.5
        exit_contrib = (0.5 - gene.exit_threshold) * 0.3
        size_contrib = (0.25 - gene.position_size) * 0.2
        sl_contrib = (0.1 - gene.stop_loss) * 0.4
        tp_contrib = (gene.take_profit - 0.3) * 0.3
        conf_contrib = (gene.min_confidence - 0.5) * 0.5
        noise = random.gauss(0, 0.1)

        sharpe = base_sharpe + entry_contrib + exit_contrib + size_contrib + sl_contrib + tp_contrib + conf_contrib + noise
        return sharpe
