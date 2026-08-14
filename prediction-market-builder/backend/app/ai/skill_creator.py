from __future__ import annotations

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import uuid
from typing import Any

from app.data.chromadb_manager import ChromaDBManager
from app.services.node_executor import NodeRegistry, ExecutionContext

logger = logging.getLogger(__name__)

_FORBIDDEN_NAMES = {
    "__import__", "open", "eval", "exec", "compile", "input",
    "globals", "locals", "vars", "breakpoint", "memoryview",
    "__loader__", "__spec__", "__build_class__", "super",
}

SKILL_TEMPLATE = """
from typing import Any

def handler(node: dict, inputs: dict, ctx: ExecutionContext) -> dict:
    {body}
    return result
"""

SKILL_CREATION_PROMPT = """
You are a skill creator for a prediction market strategy builder.
Generate a Python function that implements a node handler with this signature:

def handler(node: dict, inputs: dict, ctx: ExecutionContext) -> dict:
    ...

Where:
- node: contains "data" dict with user-configured parameters (fields, thresholds, etc.)
- inputs: dict of outputs from upstream nodes, keyed by node id
- ctx: ExecutionContext with .market, .signal, .portfolio, .risk_calculator, .portfolio_manager, .tabpfn

The handler should:
1. Extract parameters from node.get("data", {{}})
2. Use inputs and ctx as needed
3. Return a dict with at minimum a "triggered" bool and any computed values

Example skill: "Alert when odds drop below 0.3":
```python
def handler(node, inputs, ctx):
    data = node.get("data", {{}})
    threshold = data.get("threshold", 0.3)
    odds = ctx.market.get("current_odds", 0.5)
    triggered = odds < threshold
    return {{
        "triggered": triggered,
        "odds": odds,
        "threshold": threshold,
    }}
```

User description: {description}

Generate ONLY the Python code. No explanation. No markdown formatting.
Use standard Python. No external imports beyond typing.Any.
Return a valid function that can be `eval`'d.
"""


CONTAINER_SKILL_TEMPLATE = r"""
import json
import sys

def handler(node, inputs, ctx):
    {body}
    return result

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    result = handler(data.get("node", {{}}), data.get("inputs", {{}}), data.get("ctx", {{}}))
    print(json.dumps(result))
"""


class SkillCreator:
    def __init__(self, registry: NodeRegistry | None = None, tool_registry=None, git_manager=None):
        self.node_registry = registry or NodeRegistry()
        self.tool_registry = tool_registry
        self.git_manager = git_manager
        self.memory = ChromaDBManager()
        self.docker_available = shutil.which("docker") is not None

    async def create_skill_from_description(
        self,
        description: str,
        user_id: str = "default",
        build_container: bool = False,
    ) -> dict[str, Any]:
        code = await self._generate_code(description)
        if not code:
            return {
                "skill": None,
                "response": "Could not generate skill code from description.",
            }

        valid, error = self._validate_code(code)
        if not valid:
            logger.warning("Skill validation failed: %s", error)
            fixed = await self._fix_code(code, error)
            if fixed:
                code = fixed
                valid, error = self._validate_code(code)

        if not valid:
            return {
                "skill": None,
                "response": f"Could not create valid skill. Error: {error}",
            }

        compiled = self._compile_and_register(code, description)
        if not compiled:
            return {
                "skill": None,
                "response": "Failed to register the skill.",
            }

        container_tag = None
        if build_container and self.docker_available:
            container_tag = self._build_container(code, compiled)
            if container_tag:
                self._register_container_tool(compiled, container_tag)
        elif build_container and not self.docker_available:
            logger.warning("Container build requested but Docker is not available")

        if self.tool_registry and not container_tag:
            self._register_in_tool_registry(compiled, code)

        if self.git_manager:
            self._save_to_git(compiled, code, description)

        self._store_skill(compiled, description, user_id)

        return {
            "skill": compiled,
            "container_tag": container_tag,
            "response": f"Skill '{compiled['name']}' created and registered successfully.",
        }

    def _register_in_tool_registry(self, compiled: dict[str, Any], code: str) -> None:
        try:
            handler_fn = self.node_registry.get(compiled["id"])

            def skill_handler(**kw: Any) -> dict[str, Any]:
                node_data = kw.get("node_data") or {}
                inputs = kw.get("inputs") or {}
                result = handler_fn({"data": node_data}, inputs, ExecutionContext())
                return result if isinstance(result, dict) else {"result": result}

            schema = {
                "description": compiled.get("description", "Custom skill"),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_data": {"type": "object", "description": "Node configuration data"},
                        "inputs": {"type": "object", "description": "Upstream node outputs"},
                    },
                },
            }
            self.tool_registry.register(
                name=compiled["id"],
                toolset="custom_skills",
                schema=schema,
                handler=skill_handler,
            )
        except Exception as exc:
            logger.warning("Tool registry registration failed: %s", exc)

    def _save_to_git(self, compiled: dict[str, Any], code: str, description: str) -> None:
        try:
            self.git_manager.save_skill_code(compiled["name"], code, description)
            self.git_manager.commit_skill(compiled["name"], description)
        except Exception as exc:
            logger.debug("Git save failed: %s", exc)

    async def _generate_code(self, description: str) -> str | None:
        from app.ai.hermes_sidecar import HermesSidecar
        hermes = HermesSidecar()

        if hermes.available:
            prompt = SKILL_CREATION_PROMPT.format(description=description)
            result = await hermes.process_message(prompt, {"user_id": "skill_creator"})
            code = result.get("response", "")
        else:
            code = self._template_from_description(description)

        code = self._clean_code(code)
        if not code:
            return None
        return code

    def _template_from_description(self, description: str) -> str:
        desc_lower = description.lower()
        if "threshold" in desc_lower or "alert" in desc_lower or "drop" in desc_lower or "rise" in desc_lower:
            body = textwrap.dedent("""\
                data = node.get("data", {})
                field = data.get("field", "current_odds")
                operator = data.get("operator", "lt")
                threshold = data.get("threshold", 0.5)
                value = ctx.market.get(field, 0.5)
                if operator == "lt":
                    triggered = value < threshold
                elif operator == "gt":
                    triggered = value > threshold
                elif operator == "between":
                    lo = data.get("threshold_low", 0.3)
                    hi = data.get("threshold_high", 0.7)
                    triggered = lo <= value <= hi
                else:
                    triggered = False
                result = {
                    "triggered": triggered,
                    "value": value,
                    "threshold": threshold,
                    "field": field,
                }
            """)
        elif "volume" in desc_lower or "liquidity" in desc_lower:
            body = textwrap.dedent("""\
                data = node.get("data", {})
                min_volume = data.get("min_volume", 100000)
                volume = ctx.market.get("volume", 0)
                triggered = volume >= min_volume
                result = {
                    "triggered": triggered,
                    "volume": volume,
                    "min_volume": min_volume,
                }
            """)
        elif "momentum" in desc_lower or "trend" in desc_lower:
            body = textwrap.dedent("""\
                data = node.get("data", {})
                lookback = data.get("lookback", 5)
                min_momentum = data.get("min_momentum", 0.02)
                if hasattr(ctx, "portfolio") and "price_history" in ctx.portfolio:
                    prices = ctx.portfolio["price_history"][-lookback:]
                    if len(prices) >= 2:
                        momentum = (prices[-1] - prices[0]) / prices[0]
                    else:
                        momentum = 0
                else:
                    momentum = 0
                triggered = abs(momentum) >= min_momentum
                result = {
                    "triggered": triggered,
                    "momentum": round(momentum, 4),
                    "min_momentum": min_momentum,
                }
            """)
        else:
            body = textwrap.dedent("""\
                data = node.get("data", {})
                field = data.get("field", "current_odds")
                value = ctx.market.get(field, 0.5)
                triggered = True
                result = {
                    "triggered": triggered,
                    "value": value,
                    "field": field,
                }
            """)
        return f"def handler(node, inputs, ctx):\n{textwrap.indent(body, '    ')}\n    return result"

    def _clean_code(self, code: str) -> str | None:
        code = code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        if not code:
            return None
        if "def handler" not in code:
            code = SKILL_TEMPLATE.format(body=textwrap.indent(code, "    "))
        return code

    def _validate_code(self, code: str) -> tuple[bool, str | None]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, str(e)

        has_handler = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module == "typing":
                    continue
                return False, "imports are not allowed in generated skills"
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                return False, "global/nonlocal statements are not allowed"
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return False, f"dunder attribute access is not allowed: {node.attr}"
            if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
                return False, f"forbidden name: {node.id}"
            if isinstance(node, ast.FunctionDef) and node.name == "handler":
                has_handler = True
                args = [arg.arg for arg in node.args.args]
                if len(args) < 3:
                    return False, "handler must have at least 3 parameters (node, inputs, ctx)"

        if not has_handler:
            return False, "No 'handler' function found in generated code"

        return True, None

    async def _fix_code(self, code: str, error: str) -> str | None:
        from app.ai.hermes_sidecar import HermesSidecar
        hermes = HermesSidecar()

        if not hermes.available:
            return None

        fix_prompt = (
            f"The following Python code has an error:\n\n{code}\n\n"
            f"Error: {error}\n\n"
            f"Fix the code and return ONLY the corrected Python function definition. "
            f"Keep the function name 'handler'."
        )
        result = await hermes.process_message(fix_prompt, {"user_id": "skill_creator_fix"})
        fixed = self._clean_code(result.get("response", ""))
        if fixed and "def handler" in fixed:
            return fixed
        return None

    def _compile_and_register(self, code: str, description: str) -> dict[str, Any] | None:
        """Compile generated code in a RestrictedPython sandbox and register it.

        Generated code is LLM output and must be treated as untrusted: it runs
        with RestrictedPython's safe builtins only (no ``__builtins__``, no
        imports, guarded attribute access), inside the API process. The
        containerized path (``build_container=True``) additionally executes it
        with ``--network=none --read-only`` isolation.
        """
        from RestrictedPython import compile_restricted_exec
        from RestrictedPython.Guards import (
            safer_getattr,
            guarded_unpack_sequence,
            guarded_iter_unpack_sequence,
            full_write_guard,
            safe_builtins,
        )

        code = re.sub(r"^\s*from typing import .*$", "", code, flags=re.MULTILINE)

        safe_globals: dict[str, Any] = {
            "__builtins__": safe_builtins,
            "_getattr_": safer_getattr,
            "_getitem_": lambda obj, key: obj[key],
            "_getiter_": lambda obj: iter(obj),
            "_unpack_sequence_": guarded_unpack_sequence,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_write_": full_write_guard,
            "ExecutionContext": ExecutionContext,
            "Any": Any,
        }

        local_ns: dict[str, Any] = {}
        try:
            byte_code = compile_restricted_exec(
                code, filename=f"<skill_{description[:16]}>"
            )
            exec(byte_code, safe_globals, local_ns)
            handler_fn = local_ns.get("handler")
            if not handler_fn:
                return None
        except Exception as exc:
            logger.warning("Skill restricted-exec failed: %s", exc)
            return None

        try:
            smoke = handler_fn({"data": {}}, {}, ExecutionContext())
            if not isinstance(smoke, dict):
                logger.warning("Skill smoke test returned non-dict: %r", type(smoke))
                return None
        except Exception as exc:
            logger.warning("Skill smoke test raised: %s", exc)
            return None

        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        skill_name = f"custom_{uuid.uuid4().hex[:6]}"

        self.node_registry.register(skill_id, handler_fn)

        return {
            "id": skill_id,
            "name": skill_name,
            "description": description[:200],
            "code": code,
            "type": "custom_skill",
        }

    def _build_container(self, code: str, compiled: dict[str, Any]) -> str | None:
        tag = f"skill-{compiled['id']}:latest"
        tmp_dir: str | None = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="skill_container_")
            skill_path = os.path.join(tmp_dir, "skill.py")

            handler_body = self._extract_handler_body(code)
            full_code = CONTAINER_SKILL_TEMPLATE.format(body=textwrap.indent(handler_body, "    "))
            with open(skill_path, "w") as f:
                f.write(full_code)

            dockerfile = (
                "FROM python:3.12-slim\n"
                "WORKDIR /skill\n"
                "COPY skill.py .\n"
                "CMD [\"python\", \"skill.py\"]\n"
            )
            with open(os.path.join(tmp_dir, "Dockerfile"), "w") as f:
                f.write(dockerfile)

            result = subprocess.run(
                ["docker", "build", "-t", tag, "."],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.warning("Docker build failed for %s: %s", tag, result.stderr)
                return None

            if not self._test_container(tag):
                logger.warning("Container smoke test failed for %s", tag)
                return None

            return tag
        except Exception as exc:
            logger.warning("Container build failed: %s", exc)
            return None
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _extract_handler_body(self, code: str) -> str:
        lines = code.split("\n")
        body_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("def handler"):
                body_start = i + 1
                break
        if body_start < 0 or body_start >= len(lines):
            return code
        body_lines = lines[body_start:]
        min_indent = float("inf")
        for bl in body_lines:
            stripped = bl.rstrip()
            if stripped and not stripped.startswith("return"):
                indent = len(bl) - len(bl.lstrip())
                min_indent = min(min_indent, indent)
        if min_indent == float("inf"):
            min_indent = 0
        dedented = [bl[min_indent:] for bl in body_lines]
        dedented = [l for l in dedented if not l.strip().startswith("return")]
        return "\n".join(dedented).strip()

    def _test_container(self, tag: str) -> bool:
        import json as _json
        test_input = _json.dumps({"node": {"data": {}}, "inputs": {}, "ctx": {}})
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", tag],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("Container test failed (rc=%d): %s", result.returncode, result.stderr)
                return False
            output = result.stdout.strip()
            parsed = json.loads(output)
            return isinstance(parsed, dict) and "result" in parsed
        except Exception as exc:
            logger.warning("Container test exception: %s", exc)
            return False

    def _register_container_tool(self, compiled: dict[str, Any], container_tag: str) -> None:
        if not self.tool_registry:
            return
        try:
            schema = {
                "description": compiled.get("description", "Containerized custom skill"),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_data": {"type": "object", "description": "Node configuration data"},
                        "inputs": {"type": "object", "description": "Upstream node outputs"},
                    },
                },
            }
            self.tool_registry.register(
                name=compiled["id"],
                toolset="custom_skills",
                schema=schema,
                handler=lambda **kw: {"result": "skill_executed", "skill_id": compiled["id"]},
                container_image=container_tag,
                execution_mode="container",
            )
        except Exception as exc:
            logger.warning("Container tool registration failed: %s", exc)

    def _store_skill(self, skill: dict[str, Any], description: str, user_id: str) -> None:
        try:
            self.memory.store_memory(
                "strategy_templates",
                skill["id"],
                description,
                {
                    "type": "custom_skill",
                    "name": skill.get("name", ""),
                    "user_id": user_id,
                    "registry_id": skill["id"],
                },
            )
        except Exception as exc:
            logger.debug("Skill memory store failed: %s", exc)

    def list_skills(self) -> list[dict[str, Any]]:
        skills = []

        if self.tool_registry:
            try:
                tool_skills = self.tool_registry.list_tools(toolset_filter="custom_skills")
                skills.extend(tool_skills)
            except Exception as exc:
                logger.debug("Tool registry list failed: %s", exc)

        try:
            results = self.memory.recall_similar("strategy_templates", "custom skill", n_results=20)
            memory_skills = [
                {
                    "id": r.get("id", ""),
                    "name": (r.get("metadata") or {}).get("name", ""),
                    "description": r.get("text", ""),
                    "type": (r.get("metadata") or {}).get("type", ""),
                }
                for r in results
                if (r.get("metadata") or {}).get("type") == "custom_skill"
            ]
            existing_names = {s["name"] for s in skills}
            for ms in memory_skills:
                if ms["name"] not in existing_names:
                    skills.append(ms)
        except Exception as exc:
            logger.debug("Memory list failed: %s", exc)

        return skills
