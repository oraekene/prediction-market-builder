"""Hermes-Agent sidecar integration.

Wraps Nous Research's Hermes-Agent (oneshot API) as an importable module
for the prediction market strategy builder. Falls back gracefully when
Hermes is not configured (no API keys, no config.yaml).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class HermesSidecar:
    """Lightweight wrapper around Hermes-Agent's internal _run_agent API.

    Manages per-user conversation history and graceful degradation when
    Hermes is not configured. Uses Hermes-Agent's internal _run_agent
    (which returns a response string) rather than run_oneshot (which
    prints to stdout and returns an exit code).
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._conversations: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()
        self._available: bool | None = None

    def check_available(self) -> bool:
        try:
            has_key = bool(os.getenv("HERMES_INFERENCE_MODEL") or
                           os.getenv("OPENAI_API_KEY") or
                           os.getenv("ANTHROPIC_API_KEY"))
            config_path = os.path.expanduser("~/.hermes/config.yaml")
            has_config = os.path.isfile(config_path)
            overridden = self._config.get("available", None)
            if overridden is not None:
                return bool(overridden)
            return has_key or has_config
        except Exception:
            return False

    @property
    def available(self) -> bool:
        if self._available is None:
            self._available = self.check_available()
        return self._available

    async def process_message(self, message: str, context: dict | None = None) -> dict:
        user_id = (context or {}).get("user_id", "default")
        async with self._lock:
            if user_id not in self._conversations:
                self._conversations[user_id] = []
            self._conversations[user_id].append(message)

        if not self.available:
            return await self._fallback_response(message, user_id)

        return await self._hermes_response(user_id)

    async def _fallback_response(self, message: str, user_id: str) -> dict:
        async with self._lock:
            history = list(self._conversations.get(user_id, []))
        return {
            "type": "hermes_unavailable",
            "response": (
                "Hermes-Agent is not configured. "
                "Set HERMES_INFERENCE_MODEL and a provider API key, "
                "or run `hermes setup` to configure it."
            ),
            "message_received": message,
            "history_length": len(history),
        }

    async def _build_prompt(self, user_id: str) -> str:
        async with self._lock:
            history = list(self._conversations.get(user_id, []))
        if len(history) <= 1:
            return history[0] if history else ""
        lines = []
        for i, msg in enumerate(history):
            lines.append(f"[Message {i + 1}]: {msg}")
        lines.append(f"[Latest]: {history[-1]}")
        return "\n".join(lines)

    async def _hermes_response(self, user_id: str) -> dict:
        try:
            from hermes_cli.oneshot import _run_agent

            prompt = await self._build_prompt(user_id)
            response = await asyncio.to_thread(_run_agent, prompt=prompt)
            return {
                "type": "hermes_response",
                "response": response or "",
            }
        except ImportError as exc:
            logger.warning("Hermes-Agent not fully installed: %s", exc)
            self._available = False
            return {
                "type": "hermes_unavailable",
                "response": "Hermes-Agent package is not fully installed. Run `pip install hermes-agent`.",
            }
        except Exception as exc:
            logger.warning("Hermes oneshot failed: %s", exc)
            return {
                "type": "hermes_error",
                "response": f"Hermes-Agent error: {exc}",
            }

    async def get_history(self, user_id: str) -> list[str]:
        async with self._lock:
            return list(self._conversations.get(user_id, []))

    async def clear_history(self, user_id: str) -> None:
        async with self._lock:
            self._conversations.pop(user_id, None)
