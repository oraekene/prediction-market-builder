"""Hermes-Agent sidecar integration with tool calling.

Wraps Nous Research's Hermes-Agent (oneshot API) as an importable module
with tool-calling capability via ToolRegistry. Supports multi-turn
tool-calling loops: LLM → tool call → execute → feed result → LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


class HermesSidecar:
    """Hermes-Agent wrapper with tool-calling support.

    Manages per-user conversation history and graceful degradation when
    Hermes is not configured. Supports tool-calling via ToolRegistry:
    tool definitions are injected into the prompt, and structured tool
    calls in the LLM response are parsed, executed, and fed back.
    """

    def __init__(self, config: dict | None = None, tool_registry=None):
        self._config = config or {}
        self._conversations: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()
        self._available: bool | None = None
        self._tool_registry = tool_registry
        self._max_tool_rounds = 5

    def set_tool_registry(self, registry) -> None:
        self._tool_registry = registry

    async def get_tool_definitions(self) -> str:
        """Format tool registry as a JSON tool-use prompt block."""
        if not self._tool_registry:
            return ""
        try:
            tools = self._tool_registry.list_tools() if hasattr(self._tool_registry, "list_tools") else []
            if not tools:
                return ""
            lines = [
                "You have access to the following tools. "
                "When you want to call a tool, respond with a JSON block exactly like:",
                '  {"tool": "tool_name", "args": {"arg1": "val1"}}',
                "",
                "Available tools:",
            ]
            for t in tools:
                name = t.get("name", "?")
                desc = t.get("description", "")
                params = t.get("parameters", {})
                param_desc = json.dumps(params) if params else "{}"
                lines.append(f"  - {name}: {desc}  params: {param_desc}")
            lines.append("")
            lines.append(
                "After the tool returns a result, continue the conversation. "
                "You may call multiple tools sequentially."
            )
            return "\n".join(lines)
        except Exception:
            logger.exception("Failed to build tool definitions")
            return ""

    def _parse_tool_calls(self, text: str) -> list[dict]:
        """Extract tool call JSON blocks from LLM response text."""
        calls = []
        pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{.*?\})\s*\}'
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                args = json.loads(match.group(2))
                calls.append({"tool": match.group(1), "args": args})
            except (json.JSONDecodeError, KeyError):
                continue
        return calls

    def _strip_tool_calls_from_text(self, text: str) -> str:
        return re.sub(r'\s*\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\}', "", text, flags=re.DOTALL)

    async def _execute_tool_call(self, call: dict) -> str:
        """Execute a single tool call and return a result summary."""
        if not self._tool_registry:
            return '{"error": "no tool registry configured"}'
        try:
            result = await self._tool_registry.execute(
                tool_name=call["tool"],
                **call["args"],
            )
            snippet = str(result)[:1500]
            return json.dumps({"tool": call["tool"], "result": snippet})
        except Exception as exc:
            logger.warning("Tool call failed: %s | %s", call["tool"], exc)
            return json.dumps({"tool": call["tool"], "error": str(exc)[:500]})

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

    async def _build_prompt(self, user_id: str, include_tools: bool = True) -> str:
        async with self._lock:
            history = list(self._conversations.get(user_id, []))
        tool_block = ""
        if include_tools:
            tool_block = await self.get_tool_definitions()
            if tool_block:
                tool_block = "\n[TOOLS]\n" + tool_block + "\n[/TOOLS]\n"
        if len(history) <= 1:
            return tool_block + (history[0] if history else "")
        lines = [tool_block] if tool_block else []
        for i, msg in enumerate(history):
            lines.append(f"[Message {i + 1}]: {msg}")
        lines.append(f"[Latest]: {history[-1]}")
        return "\n".join(lines)

    async def _hermes_response(self, user_id: str) -> dict:
        try:
            from hermes_cli.oneshot import _run_agent

            raw_responses: list[str] = []
            tool_calls_made: list[dict] = []

            for turn in range(self._max_tool_rounds):
                prompt = await self._build_prompt(user_id, include_tools=(turn == 0))
                response = await asyncio.to_thread(_run_agent, prompt=prompt)
                if not response:
                    break

                tool_calls = self._parse_tool_calls(response)
                clean_text = self._strip_tool_calls_from_text(response)
                raw_responses.append(clean_text)

                if not tool_calls:
                    all_tool_results = []
                    break

                tool_results = []
                for call in tool_calls:
                    result = await self._execute_tool_call(call)
                    tool_results.append(result)
                    tool_calls_made.append({"tool": call["tool"], "args": call["args"]})

                tool_block = "\n".join(
                    f"[TOOL RESULT: {json.loads(r).get('tool', '?')}]: {json.loads(r).get('result', json.loads(r).get('error', ''))}"  # noqa: E501
                    for r in tool_results
                )
                async with self._lock:
                    self._conversations[user_id].append(f"[Tool Results]:\n{tool_block}")
            else:
                all_tool_results = tool_calls_made

            final_text = "\n".join(raw_responses)
            return {
                "type": "hermes_response",
                "response": final_text or "",
                "tool_calls": tool_calls_made,
                "num_tool_turns": len(raw_responses),
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
