import pytest
import tempfile
import os

from app.models import ResearchSession, ExperimentResult, RLMAlphaVector, ResearchSessionConfig  # noqa: F401

pytestmark = pytest.mark.asyncio


class TestResearchE2E:
    async def test_research_full_lifecycle(self, client):
        # a. Configure research preset and concurrency
        resp = await client.put("/api/research/config?preset=sharpe_max&max_concurrent=2")
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        # b. Read back config and verify values
        resp = await client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "sharpe_max"
        assert data["max_concurrent"] == 2
        assert "cron_enabled" in data
        assert "max_hypotheses_per_session" in data

        # c. Get aggregate stats and verify structure
        resp = await client.get("/api/research/stats")
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
        resp = await client.get("/api/research/climate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["regime"] == "calm"
        assert data["confidence"] == 0.0
        assert "metrics" in data

        # e. Get feature importance and verify features field
        _tabpfn_available = True
        try:
            import tabpfn  # noqa: F401
        except ImportError:
            _tabpfn_available = False
        if _tabpfn_available:
            resp = await client.get("/api/research/features")
            assert resp.status_code == 200
            data = resp.json()
            assert "features" in data

        # f. Run RLM scan on a temp directory with keyword-bearing content
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("oracle-lag and slippage-limit are key signals")
            resp = await client.post(
                "/api/research/rlm-scan",
                params={
                    "source_type": "forum",
                    "source_path": tmpdir,
                    "keywords": "oracle-lag,slippage",
                },
            )
            assert resp.status_code == 200, f"RLM scan failed: {resp.text}"
            data = resp.json()
            assert data["status"] == "completed"
            assert "alpha_vector_id" in data
            scan_id = data["alpha_vector_id"]

        # g. List alpha vectors and verify the scan result is present
        resp = await client.get("/api/research/alpha-vectors")
        assert resp.status_code == 200
        data = resp.json()
        assert "vectors" in data
        assert len(data["vectors"]) > 0
        assert any(v["id"] == scan_id for v in data["vectors"])

        # h. Verify config values persist across calls
        resp = await client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "sharpe_max"
        assert data["max_concurrent"] == 2

    async def test_research_config_persistence(self, client):
        # PUT config with all supported fields
        resp = await client.put(
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
        resp = await client.get("/api/research/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == "win_rate_max"
        assert data["max_concurrent"] == 4
        assert data["cron_enabled"] is True
        assert data["cron_interval_minutes"] == 60
        assert data["continuous_enabled"] is True
        assert data["max_hypotheses_per_session"] == 100
