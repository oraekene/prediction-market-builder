"""Tests for Hermes sidecar integration."""

from unittest.mock import patch

import pytest


async def test_import_hermes_sidecar():
    from app.ai.hermes_sidecar import HermesSidecar
    assert HermesSidecar is not None


async def test_instantiate_without_config():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    assert sidecar.available is False


async def test_process_message_fallback():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    result = await sidecar.process_message("Hello", {"user_id": "test"})
    assert "response" in result
    assert "type" in result
    assert result["type"] == "hermes_unavailable"


async def test_conversation_context():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    await sidecar.process_message("First message", {"user_id": "test"})
    await sidecar.process_message("Second message", {"user_id": "test"})
    history = await sidecar.get_history("test")
    assert len(history) == 2
    assert history[0] == "First message"
    assert history[1] == "Second message"


async def test_separate_conversations():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    await sidecar.process_message("User A message", {"user_id": "user_a"})
    await sidecar.process_message("User B message", {"user_id": "user_b"})
    assert len(await sidecar.get_history("user_a")) == 1
    assert len(await sidecar.get_history("user_b")) == 1


async def test_clear_conversation():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    await sidecar.process_message("Message", {"user_id": "test"})
    await sidecar.clear_history("test")
    assert await sidecar.get_history("test") == []


async def test_fallback_response_contains_response_key():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    result = await sidecar.process_message("Test", {"user_id": "test"})
    assert "response" in result


async def test_message_too_long_does_not_crash():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": False})
    long_msg = "x" * 100000
    result = await sidecar.process_message(long_msg, {"user_id": "test"})
    assert "response" in result


async def test_hermes_response_path_with_mock():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": True})
    with patch("hermes_cli.oneshot._run_agent") as mock_run:
        mock_run.return_value = "mock response text"
        result = await sidecar.process_message("test message", {"user_id": "test"})
    assert result["type"] == "hermes_response"
    assert result["response"] == "mock response text"


async def test_hermes_response_import_error_becomes_unavailable():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": True})
    with patch("hermes_cli.oneshot._run_agent", side_effect=ImportError("not installed")):
        result = await sidecar.process_message("test", {"user_id": "test"})
    assert result["type"] == "hermes_unavailable"
    assert sidecar.available is False


async def test_hermes_response_handles_runtime_error():
    from app.ai.hermes_sidecar import HermesSidecar
    sidecar = HermesSidecar({"available": True})
    with patch("hermes_cli.oneshot._run_agent", side_effect=RuntimeError("API error")):
        result = await sidecar.process_message("test", {"user_id": "test"})
    assert result["type"] == "hermes_error"
    assert "API error" in result["response"]
