from __future__ import annotations

import logging
import subprocess
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., dict[str, Any]]
AvailabilityCheck = Callable[[], bool]
ExecutionMode = Literal["in_memory", "container"]


class ToolDefinition:
    def __init__(
        self,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: ToolHandler,
        check_fn: AvailabilityCheck | None = None,
        shared_check_key: str | None = None,
        container_image: str | None = None,
        container_command: list[str] | None = None,
        execution_mode: ExecutionMode = "in_memory",
    ):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.shared_check_key = shared_check_key
        self.container_image = container_image
        self.container_command = container_command
        self.execution_mode = execution_mode


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._toolsets: dict[str, set[str]] = {}

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: ToolHandler,
        check_fn: AvailabilityCheck | None = None,
        shared_check_key: str | None = None,
        container_image: str | None = None,
        container_command: list[str] | None = None,
        execution_mode: ExecutionMode = "in_memory",
    ) -> None:
        definition = ToolDefinition(
            name, toolset, schema, handler, check_fn, shared_check_key,
            container_image, container_command, execution_mode,
        )
        self._tools[name] = definition
        self._toolsets.setdefault(toolset, set()).add(name)
        logger.debug("Registered tool '%s' in toolset '%s' (mode=%s)", name, toolset, execution_mode)

    def unregister(self, name: str) -> None:
        tool = self._tools.pop(name, None)
        if tool and tool.name in self._toolsets.get(tool.toolset, set()):
            self._toolsets[tool.toolset].discard(tool.name)

    def dispatch(self, name: str, args_dict: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        if tool.check_fn and not tool.check_fn():
            return {"error": f"Tool '{name}' is not available"}
        try:
            if tool.execution_mode == "container":
                return self._dispatch_container(tool, args_dict)
            result = tool.handler(**(args_dict or {}))
            if not isinstance(result, dict):
                return {"result": result}
            return result
        except Exception as exc:
            logger.exception("Tool '%s' dispatch failed: %s", name, exc)
            return {"error": f"Tool dispatch failed: {exc}"}

    def _dispatch_container(self, tool: ToolDefinition, args_dict: dict[str, Any] | None = None) -> dict[str, Any]:
        import json
        cmd = ["docker", "run", "--rm"]
        if tool.container_image:
            cmd.append(tool.container_image)
        cmd.extend(tool.container_command or [])
        input_data = json.dumps(args_dict or {})
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=120,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if result.returncode != 0:
                return {"error": f"Container exited with code {result.returncode}: {stderr or stdout}"}
            try:
                return json.loads(stdout)
            except (json.JSONDecodeError, ValueError):
                return {"result": stdout}
        except subprocess.TimeoutExpired:
            return {"error": "Container execution timed out after 120s"}
        except FileNotFoundError:
            return {"error": "Docker is not available on this system"}

    def get_definitions(self, tool_names: set[str] | None = None) -> list[dict[str, Any]]:
        names = tool_names if tool_names is not None else set(self._tools.keys())
        result = []
        for name in names:
            tool = self._tools.get(name)
            if tool:
                entry = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.schema.get("description", ""),
                        "parameters": tool.schema.get("parameters", {}),
                    },
                }
                result.append(entry)
        return result

    def get_tools_by_toolset(self, toolset: str) -> list[ToolDefinition]:
        names = self._toolsets.get(toolset, set())
        return [self._tools[n] for n in names if n in self._tools]

    def list_tools(self, toolset_filter: str | None = None) -> list[dict[str, Any]]:
        if toolset_filter:
            tools = self.get_tools_by_toolset(toolset_filter)
        else:
            tools = list(self._tools.values())
        return [
            {
                "name": t.name,
                "toolset": t.toolset,
                "description": t.schema.get("description", ""),
                "available": t.check_fn() if t.check_fn else True,
                "execution_mode": t.execution_mode,
            }
            for t in tools
        ]

    def has_container_tools(self) -> bool:
        return any(t.execution_mode == "container" for t in self._tools.values())


registry = ToolRegistry()
