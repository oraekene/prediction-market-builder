from __future__ import annotations

import pytest

from app.ai.repl_service import REPLService, REPLSessionManager, REPLSession


@pytest.fixture
def repl_service():
    return REPLService(max_sessions=10, session_ttl_minutes=1, timeout_seconds=5)


@pytest.fixture
def session_id(repl_service):
    return repl_service.create_session()["session_id"]


class TestREPLSessionManager:
    def test_create_session(self):
        mgr = REPLSessionManager(max_sessions=5)
        sid = mgr.create_session()
        assert sid is not None
        assert mgr.get_session(sid) is not None

    def test_max_sessions(self):
        mgr = REPLSessionManager(max_sessions=2)
        mgr.create_session()
        mgr.create_session()
        with pytest.raises(RuntimeError, match="Max REPL sessions"):
            mgr.create_session()

    def test_destroy_session(self):
        mgr = REPLSessionManager()
        sid = mgr.create_session()
        assert mgr.destroy_session(sid) is True
        assert mgr.get_session(sid) is None

    def test_session_count(self):
        mgr = REPLSessionManager(max_sessions=10)
        assert mgr.session_count() == 0
        mgr.create_session()
        mgr.create_session()
        assert mgr.session_count() == 2


class TestREPLService:
    def test_create_session(self, repl_service):
        result = repl_service.create_session()
        assert "session_id" in result
        assert result["variable_count"] == 0

    def test_execute_simple_expression(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "2 + 2")
        assert result["error"] is None
        assert result["result"] == "4"

    def test_execute_print(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "print('hello world')")
        assert result["error"] is None
        assert "hello world" in result["stdout"]

    def test_persistent_variables(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "x = 42")
        result = _sync_execute(repl_service, session_id, "x * 2")
        assert result["result"] == "84"

    def test_string_operations(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "'hello ' + 'world'")
        assert result["result"] == "'hello world'"

    def test_list_operations(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "items = [1, 2, 3, 4, 5]")
        result = _sync_execute(repl_service, session_id, "sum(items)")
        assert result["result"] == "15"

    def test_dict_operations(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "d = {'a': 1, 'b': 2}")
        result = _sync_execute(repl_service, session_id, "d['a'] + d['b']")
        assert result["result"] == "3"

    def test_import_blocked(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "import os")
        assert result["error"] is not None
        assert "import" in result["error"].lower() or "not" in result["error"].lower()

    def test_open_blocked(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "open('/etc/passwd')")
        assert result["error"] is not None

    def test_exec_blocked(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "exec('x = 1')")
        assert result["error"] is not None

    def test_math_module(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "import math; math.sqrt(16)")
        assert result["result"] == "4.0"

    def test_statistics_module(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "import statistics; statistics.mean([1,2,3,4,5])")
        assert result["result"] == "3"

    def test_json_module(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "import json; json.dumps({'a': 1})")
        assert result["result"] == "'{\"a\": 1}'"

    def test_collections_module(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "from collections import Counter; Counter('aabbc')")
        assert "Counter" in (result["result"] or "")

    def test_get_session_state(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "x = 42")
        state = repl_service.get_session_state(session_id)
        assert state is not None
        assert state["session_id"] == session_id
        assert state["variable_count"] >= 1
        assert "x" in state["variable_types"]

    def test_get_session_state_expired(self, repl_service):
        state = repl_service.get_session_state("nonexistent")
        assert state is None

    def test_destroy_session(self, repl_service, session_id):
        assert repl_service.destroy_session(session_id) is True
        assert repl_service.destroy_session(session_id) is False

    def test_execute_invalid_session(self, repl_service):
        result = _sync_execute(repl_service, "bad-session", "x = 1")
        assert "error" in result
        assert "not found" in result["error"]

    def test_execute_timeout_gives_error(self):
        service = REPLService(max_sessions=5, session_ttl_minutes=1, timeout_seconds=1)
        sid = service.create_session()["session_id"]
        result = _sync_execute(service, sid, "import time; time.sleep(5)")
        assert result["error"] is not None
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()

    def test_for_loop(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "sum(i for i in range(10))")
        assert result["result"] == "45"

    def test_function_definition(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "def add(a, b): return a + b")
        result = _sync_execute(repl_service, session_id, "add(3, 4)")
        assert result["result"] == "7"

    def test_syntax_error(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "This is not valid Python @@")
        assert result["error"] is not None

    def test_division_by_zero(self, repl_service, session_id):
        result = _sync_execute(repl_service, session_id, "1 / 0")
        assert result["error"] is not None
        assert "ZeroDivisionError" in result["error"]

    def test_variable_types_tracking(self, repl_service, session_id):
        _sync_execute(repl_service, session_id, "x = 42")
        _sync_execute(repl_service, session_id, "y = 'hello'")
        _sync_execute(repl_service, session_id, "z = [1, 2, 3]")
        state = repl_service.get_session_state(session_id)
        assert state["variable_types"]["x"] == "int"
        assert state["variable_types"]["y"] == "str"
        assert state["variable_types"]["z"] == "list"


def _sync_execute(service: REPLService, session_id: str, code: str) -> dict:
    import asyncio
    return asyncio.run(service.execute_code(session_id, code))
