from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

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
        "response": "The hypothesis is reasonable but the threshold is too aggressive."
    }
    plugin = HermesResearchPlugin(hermes_sidecar=mock_sidecar)
    result = await plugin.critique_result({"composite_score": 1.2, "verdict": "WARN"})
    assert "critique" in result
    assert "suggestions" in result


@pytest.mark.asyncio
async def test_available_property():
    plugin = HermesResearchPlugin()
    assert plugin.available is False
    mock_sidecar = AsyncMock()
    mock_sidecar.available = True
    plugin2 = HermesResearchPlugin(hermes_sidecar=mock_sidecar)
    assert plugin2.available is True
