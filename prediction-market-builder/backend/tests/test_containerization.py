from __future__ import annotations

import asyncio
import json
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.tool_registry import ToolRegistry, ToolDefinition


class TestToolRegistryContainer:
    def test_register_container_tool(self):
        reg = ToolRegistry()
        reg.register(
            name="container_skill",
            toolset="custom_skills",
            schema={"description": "A container skill", "parameters": {}},
            handler=lambda **kw: {"result": "ok"},
            container_image="my-skill:latest",
            execution_mode="container",
        )
        tool = reg._tools["container_skill"]
        assert tool.execution_mode == "container"
        assert tool.container_image == "my-skill:latest"
        assert tool.handler is not None

    def test_list_tools_shows_execution_mode(self):
        reg = ToolRegistry()
        reg.register(
            name="mem_skill", toolset="skills",
            schema={"description": "mem", "parameters": {}},
            handler=lambda **kw: {},
            execution_mode="in_memory",
        )
        reg.register(
            name="ctr_skill", toolset="skills",
            schema={"description": "ctr", "parameters": {}},
            handler=lambda **kw: {},
            container_image="img:latest",
            execution_mode="container",
        )
        listed = reg.list_tools()
        modes = {t["name"]: t["execution_mode"] for t in listed}
        assert modes["mem_skill"] == "in_memory"
        assert modes["ctr_skill"] == "container"

    def test_has_container_tools(self):
        reg = ToolRegistry()
        assert not reg.has_container_tools()
        reg.register(
            name="ctr", toolset="t",
            schema={}, handler=lambda **kw: {},
            container_image="i", execution_mode="container",
        )
        assert reg.has_container_tools()

    @patch("app.ai.tool_registry.subprocess.run")
    def test_dispatch_container_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"result": "hello"}', stderr="",
        )
        reg = ToolRegistry()
        reg.register(
            name="ctr_skill", toolset="t",
            schema={"description": "test", "parameters": {}},
            handler=lambda **kw: {},
            container_image="test:latest",
            execution_mode="container",
        )
        result = reg.dispatch("ctr_skill", {"key": "val"})
        assert result == {"result": "hello"}
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args is not None
        assert "docker" in call_args[0][0][0]

    @patch("app.ai.tool_registry.subprocess.run")
    def test_dispatch_container_error(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="something broke",
        )
        reg = ToolRegistry()
        reg.register(
            name="bad_ctr", toolset="t",
            schema={}, handler=lambda **kw: {},
            container_image="bad:latest",
            execution_mode="container",
        )
        result = reg.dispatch("bad_ctr")
        assert "error" in result
        assert "something broke" in result["error"]

    @patch("app.ai.tool_registry.subprocess.run")
    def test_dispatch_container_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=120)
        reg = ToolRegistry()
        reg.register(
            name="slow_ctr", toolset="t",
            schema={}, handler=lambda **kw: {},
            container_image="slow:latest",
            execution_mode="container",
        )
        result = reg.dispatch("slow_ctr")
        assert "timed out" in result["error"]

    @patch("app.ai.tool_registry.subprocess.run")
    def test_dispatch_container_docker_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        reg = ToolRegistry()
        reg.register(
            name="no_docker", toolset="t",
            schema={}, handler=lambda **kw: {},
            container_image="x:latest",
            execution_mode="container",
        )
        result = reg.dispatch("no_docker")
        assert "Docker is not available" in result["error"]

    def test_dispatch_in_memory_still_works(self):
        reg = ToolRegistry()
        reg.register(
            name="regular", toolset="t",
            schema={"description": "reg", "parameters": {}},
            handler=lambda **kw: {"ok": True},
        )
        result = reg.dispatch("regular", {"x": 1})
        assert result == {"ok": True}

    def test_definitions_include_container_tools(self):
        reg = ToolRegistry()
        reg.register(
            name="ctr", toolset="t",
            schema={"description": "a container tool", "parameters": {}},
            handler=lambda **kw: {},
            container_image="img:latest",
            execution_mode="container",
        )
        defs = reg.get_definitions()
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "ctr"


class TestToolDefinition:
    def test_default_execution_mode(self):
        td = ToolDefinition(
            name="test", toolset="t", schema={},
            handler=lambda **kw: {},
        )
        assert td.execution_mode == "in_memory"
        assert td.container_image is None

    def test_container_execution_mode(self):
        td = ToolDefinition(
            name="ctr", toolset="t", schema={},
            handler=lambda **kw: {},
            container_image="img:v1",
            execution_mode="container",
        )
        assert td.execution_mode == "container"
        assert td.container_image == "img:v1"


class TestSkillCreatorContainer:
    @patch("app.ai.skill_creator.shutil.which")
    def test_docker_availability_check(self, mock_which):
        from app.ai.skill_creator import SkillCreator

        mock_which.return_value = "/usr/bin/docker"
        sc = SkillCreator()
        assert sc.docker_available is True

        mock_which.return_value = None
        sc2 = SkillCreator()
        assert sc2.docker_available is False

    def test_extract_handler_body(self):
        from app.ai.skill_creator import SkillCreator
        sc = SkillCreator()
        code = """\
def handler(node, inputs, ctx):
    data = node.get("data", {})
    value = data.get("threshold", 0.5)
    triggered = value > 0.3
    return {"triggered": triggered}"""
        body = sc._extract_handler_body(code)
        assert "data = node.get" in body
        assert "value = data.get" in body
        assert "triggered = value > 0.3" in body
        assert "return" not in body

    @patch("app.ai.skill_creator.shutil.which")
    @patch("app.ai.skill_creator.subprocess.run")
    def test_build_container_pipeline(self, mock_run, mock_which):
        from app.ai.skill_creator import SkillCreator

        mock_which.return_value = "/usr/bin/docker"
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"result": "ok"}', stderr="",
        )

        sc = SkillCreator(tool_registry=ToolRegistry())
        compiled = {
            "id": "skill_test123",
            "name": "test_skill",
            "description": "test",
            "code": "def handler(node, inputs, ctx):\n    return {\"result\": \"ok\"}",
            "type": "custom_skill",
        }
        tag = sc._build_container(compiled["code"], compiled)
        assert tag == "skill-skill_test123:latest"
        assert mock_run.call_count >= 2

    @patch("app.ai.skill_creator.shutil.which")
    @patch("app.ai.skill_creator.subprocess.run")
    def test_build_container_failure(self, mock_run, mock_which):
        from app.ai.skill_creator import SkillCreator

        mock_which.return_value = "/usr/bin/docker"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="build error",
        )

        sc = SkillCreator()
        compiled = {
            "id": "skill_fail",
            "name": "fail",
            "description": "fail",
            "code": "def handler(node, inputs, ctx):\n    return {}",
            "type": "custom_skill",
        }
        tag = sc._build_container(compiled["code"], compiled)
        assert tag is None

    @patch("app.ai.skill_creator.SkillCreator._generate_code", new_callable=AsyncMock)
    @patch("app.ai.skill_creator.shutil.which")
    @patch("app.ai.skill_creator.subprocess.run")
    @pytest.mark.asyncio
    async def test_create_skill_with_container(self, mock_run, mock_which, mock_gen):
        from app.ai.skill_creator import SkillCreator

        mock_gen.return_value = (
            "def handler(node, inputs, ctx):\n"
            "    data = node.get('data', {})\n"
            "    threshold = data.get('threshold', 0.3)\n"
            "    odds = ctx.market.get('current_odds', 0.5)\n"
            "    triggered = odds < threshold\n"
            "    return {'triggered': triggered, 'odds': odds}"
        )
        mock_which.return_value = "/usr/bin/docker"
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"result": "ok"}', stderr="",
        )

        reg = ToolRegistry()
        sc = SkillCreator(tool_registry=reg)
        result = await asyncio.wait_for(
            sc.create_skill_from_description(
                description="threshold alert",
                user_id="test_user",
                build_container=True,
            ),
            timeout=10,
        )
        assert result["skill"] is not None
        assert result["container_tag"] is not None
        assert "skill_" in result["container_tag"]

        listed = reg.list_tools(toolset_filter="custom_skills")
        if listed:
            assert listed[0]["execution_mode"] == "container"

    @patch("app.ai.skill_creator.SkillCreator._generate_code", new_callable=AsyncMock)
    @patch("app.ai.skill_creator.shutil.which")
    @pytest.mark.asyncio
    async def test_create_skill_with_container_no_docker(self, mock_which, mock_gen):
        from app.ai.skill_creator import SkillCreator

        mock_gen.return_value = (
            "def handler(node, inputs, ctx):\n"
            "    return {'result': 'ok'}"
        )
        mock_which.return_value = None

        sc = SkillCreator()
        result = await asyncio.wait_for(
            sc.create_skill_from_description(
                description="simple test skill",
                user_id="test_user",
                build_container=True,
            ),
            timeout=10,
        )
        assert result["skill"] is not None
        assert result["container_tag"] is None
