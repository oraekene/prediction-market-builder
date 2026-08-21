from __future__ import annotations

import subprocess

import pytest

from app.ai.pi_autoresearch.experiment_tracker import ExperimentTracker


@pytest.mark.asyncio
async def test_commit_and_get_history():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
        result = {
            "session_id": "s-1", "iteration": 1, "verdict": "KEPT",
            "hypothesis": "test hypothesis", "composite_score": 1.5,
        }
        hash_val = await tracker.commit_experiment(result)
        assert hash_val is not None
        history = await tracker.get_experiment_history("s-1")
        assert len(history) == 1
        assert history[0]["iteration"] == 1
        assert history[0]["verdict"] == "KEPT"


@pytest.mark.asyncio
async def test_commit_no_git_repo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        result = {"session_id": "s-1", "iteration": 1}
        hash_val = await tracker.commit_experiment(result)
        assert hash_val is None


@pytest.mark.asyncio
async def test_get_history_empty():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        history = await tracker.get_experiment_history("nonexistent")
        assert history == []


@pytest.mark.asyncio
async def test_rollback_experiment():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
        hash1 = await tracker.commit_experiment({
            "session_id": "s-1", "iteration": 1, "verdict": "KEPT",
            "hypothesis": "original", "composite_score": 0.0,
        })
        assert hash1 is not None
        hash2 = await tracker.commit_experiment({
            "session_id": "s-1", "iteration": 2, "verdict": "KEPT",
            "hypothesis": "modified", "composite_score": 0.0,
        })
        assert hash2 is not None
        success = await tracker.rollback_experiment(hash1)
        assert success is True


@pytest.mark.asyncio
async def test_commit_returns_none_for_none_result():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(repo_path=tmpdir)
        result = await tracker.commit_experiment({"session_id": "s-1"})
        assert result is None
