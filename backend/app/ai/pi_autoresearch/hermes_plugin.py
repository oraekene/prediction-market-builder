from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HermesResearchPlugin:
    def __init__(self, hermes_sidecar: Any = None) -> None:
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
            hypotheses: list[str] = []
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
            return {"critique": response, "suggestions": response}
        except Exception as exc:
            logger.warning("Hermes critique failed: %s", exc)
            return {"critique": "", "suggestions": ""}
