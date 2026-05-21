from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentTracker:
    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)
        self._experiments_dir = self.repo_path / "experiments"

    async def commit_experiment(self, experiment_result: dict[str, Any]) -> str | None:
        try:
            session_id = experiment_result["session_id"]
            iteration = experiment_result["iteration"]
            hypothesis = experiment_result.get("hypothesis", "")

            session_dir = self._experiments_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            file_path = session_dir / f"iter_{iteration}.json"
            file_path.write_text(
                json.dumps(experiment_result, indent=2, default=str),
                encoding="utf-8",
            )

            rel_path = f"experiments/{session_id}/iter_{iteration}.json"
            subprocess.run(
                ["git", "add", rel_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                ["git", "commit", "-m", f"experiment: {session_id} iter {iteration} - {hypothesis[:60]}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            match = re.search(r"\[([^\]]+)\]", result.stdout)
            if match:
                commit_hash = match.group(1).split()[-1]
                return commit_hash
            return None
        except Exception:
            logger.warning("Failed to commit experiment", exc_info=True)
            return None

    async def rollback_experiment(self, commit_hash: str) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", commit_hash, "--", "experiments/"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"rollback experiment to {commit_hash[:8]}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            logger.warning("Failed to rollback experiment", exc_info=True)
            return False

    async def get_experiment_history(self, session_id: str) -> list[dict]:
        session_dir = self._experiments_dir / session_id
        if not session_dir.is_dir():
            return []

        history: list[dict] = []
        for fpath in sorted(session_dir.iterdir()):
            if not fpath.name.startswith("iter_") or not fpath.suffix == ".json":
                continue
            try:
                iteration = int(fpath.stem.split("_")[1])
            except (IndexError, ValueError):
                continue

            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                continue
            history.append({
                "iteration": iteration,
                "file": str(fpath.relative_to(self.repo_path)),
                "verdict": data.get("verdict"),
                "hypothesis": data.get("hypothesis"),
                "composite_score": data.get("composite_score"),
            })

        return history
