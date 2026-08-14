import pytest
import tempfile
import os

from app.models import ResearchSession, ExperimentResult, ResearchSessionConfig  # noqa: F401

pytestmark = pytest.mark.asyncio


class TestResearchE2E:
    async def test_research_full_lifecycle(self, authenticated_client):
        # a. Configure research preset and concurrency
        resp = await authenticated_client.put("/api/research/config?preset=sharpe_max&max_concurrent=2")
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        # b. Read back config and verify values
        resp = await authenticated_client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "sharpe_max"
        assert data["max_concurrent"] == 2
        assert "cron_enabled" in data
        assert "max_hypotheses_per_session" in data

        # c. Get aggregate stats and verify structure
        resp = await authenticated_client.get("/api/research/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 0
        assert data["total_kept"] == 0
        assert data["total_reverted"] == 0
        assert "avg_sharpe" in data
        assert "avg_win_rate" in data
        assert "best_sharpe" in data
        assert "keep_rate" in data

        # d. Get market climate and verify regime
        resp = await authenticated_client.get("/api/research/climate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["regime"] == "calm"
        assert data["confidence"] == 0.0
        assert "metrics" in data

        # e. Verify config values persist across calls
        resp = await authenticated_client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "sharpe_max"
        assert data["max_concurrent"] == 2

    async def test_research_config_persistence(self, authenticated_client):
        # PUT config with all supported fields
        resp = await authenticated_client.put(
            "/api/research/config",
            params={
                "preset": "win_rate_max",
                "max_concurrent": 4,
                "cron_enabled": "true",
                "cron_interval": 60,
                "continuous_enabled": "true",
                "max_hypotheses": 100,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        # GET config and verify every field matches
        resp = await authenticated_client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "win_rate_max"
        assert data["max_concurrent"] == 4
        assert data["cron_enabled"] is True
        assert data["cron_interval_minutes"] == 60
        assert data["continuous_enabled"] is True
        assert data["max_hypotheses_per_session"] == 100
