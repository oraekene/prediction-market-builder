from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GitError(Exception):
    pass


class GitManager:
    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self._skills_dir = self.repo_path / "skills"

    def init_repo(self) -> bool:
        self.repo_path.mkdir(parents=True, exist_ok=True)
        if (self.repo_path / ".git").exists():
            return True
        try:
            subprocess.run(["git", "init"], cwd=self.repo_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Hermes-Agent"], cwd=self.repo_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "hermes@prediction-builder.local"], cwd=self.repo_path, check=True, capture_output=True, text=True)
            skills_ignore = self.repo_path / ".gitignore"
            if not skills_ignore.exists():
                skills_ignore.write_text("__pycache__/\n*.pyc\n")
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_path, check=True, capture_output=True, text=True)
            logger.info("Initialized Git repo at %s", self.repo_path)
            return True
        except subprocess.CalledProcessError as exc:
            logger.warning("Git init failed: %s", exc.stderr)
            return False

    def save_skill_code(self, skill_name: str, code: str, description: str) -> dict[str, Any]:
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = self._skills_dir / f"{skill_name}.py"
        skill_file.write_text(code)

        skill_doc = self._skills_dir / f"{skill_name}.md"
        doc_content = (
            f"# {skill_name}\n\n"
            f"**Created:** {datetime.now(timezone.utc).isoformat()}\n\n"
            f"{description}\n"
        )
        skill_doc.write_text(doc_content)

        return {
            "path": str(skill_file),
            "doc_path": str(skill_doc),
            "skill_name": skill_name,
        }

    def commit_skill(self, skill_name: str, description: str) -> str | None:
        try:
            subprocess.run(
                ["git", "add", "skills/"],
                cwd=self.repo_path, check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                ["git", "commit", "-m", f"skill: {skill_name} - {description[:80]}"],
                cwd=self.repo_path, check=True, capture_output=True, text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            logger.warning("Git commit failed for skill '%s': %s", skill_name, exc.stderr)
            return None

    def get_skill_history(self, skill_name: str) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--follow", "--", f"skills/{skill_name}.py"],
                cwd=self.repo_path, check=True, capture_output=True, text=True,
            )
            entries = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(" ", 1)
                entries.append({"commit": parts[0], "message": parts[1] if len(parts) > 1 else ""})
            return entries
        except subprocess.CalledProcessError:
            return []

    def rollback_skill(self, skill_name: str, commit_hash: str) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", commit_hash, "--", f"skills/{skill_name}.py"],
                cwd=self.repo_path, check=True, capture_output=True, text=True,
            )
            self.commit_skill(skill_name, f"Rollback to {commit_hash}")
            return True
        except subprocess.CalledProcessError as exc:
            logger.warning("Git rollback failed for skill '%s': %s", skill_name, exc.stderr)
            return False

    def list_committed_skills(self) -> list[str]:
        if not self._skills_dir.exists():
            return []
        return [f.stem for f in self._skills_dir.glob("*.py")]

    def read_skill_code(self, skill_name: str) -> str | None:
        skill_file = self._skills_dir / f"{skill_name}.py"
        if skill_file.exists():
            return skill_file.read_text()
        return None
