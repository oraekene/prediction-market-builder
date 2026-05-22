from __future__ import annotations

import asyncio
import io
import logging
import textwrap
import time
import uuid
from datetime import datetime, timedelta, timezone

from RestrictedPython import safe_builtins
from RestrictedPython.Guards import safer_getattr, guarded_write_property, guarded_write_object, guarded_write_iter
from RestrictedPython.compile import compile_restricted_exec

logger = logging.getLogger(__name__)

SAFE_MODULES: dict[str, object] = {}

def _import_safe_modules():
    import math
    import statistics
    import json
    import re
    import collections
    import itertools
    import functools
    import typing
    import datetime as dt_mod
    import random

    import time as time_mod
    SAFE_MODULES.update({
        "math": math,
        "statistics": statistics,
        "json": json,
        "re": re,
        "collections": collections,
        "itertools": itertools,
        "functools": functools,
        "typing": typing,
        "datetime": dt_mod,
        "random": random,
        "time": time_mod,
    })

_import_safe_modules()


def _make_safe_import():
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in SAFE_MODULES:
            return SAFE_MODULES[name]
        raise ImportError(f"module '{name}' is not allowed in sandbox")
    return safe_import


def _common_builtins() -> dict[str, object]:
    result = dict(safe_builtins)
    result["__import__"] = _make_safe_import()
    extras = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
        "float", "format", "frozenset", "hash", "hex", "id", "int", "iter",
        "len", "list", "map", "max", "min", "next", "oct", "ord",
        "pow", "range", "repr", "reversed", "round", "set", "slice", "sorted",
        "str", "sum", "tuple", "zip",
    }
    builtins_real = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
    for name in extras:
        if name not in result and name in builtins_real:
            result[name] = builtins_real[name]
    return result


class _PrintHandlerFactory:
    def __init__(self, buf: io.StringIO | None = None):
        self.buf = buf

    def __call__(self, _getattr_fn=None):
        if self.buf is not None:
            return _PrintHandler(self.buf)
        return _PrintHandler(io.StringIO())


class _PrintHandler:
    def __init__(self, buf: io.StringIO):
        self.buf = buf

    def _call_print(self, *objects, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", None) or self.buf
        text = sep.join(str(o) for o in objects) + end
        file.write(text)


class REPLSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.execution_count = 0
        self.error_count = 0

        common_builtins = _common_builtins()
        self._globals: dict[str, object] = {
            "__builtins__": common_builtins,
            "_getattr_": safer_getattr,
            "_getitem_": lambda obj, key: obj[key],
            "_getiter_": lambda obj: iter(obj),
            "_print_": _PrintHandlerFactory(),
            "_write_": guarded_write_object,
        }

    @property
    def variable_count(self) -> int:
        ignored = {"__builtins__", "_getattr_", "_print_"}
        return sum(1 for k in self._globals if not k.startswith("_") and k not in ignored)

    @property
    def variable_types(self) -> dict[str, str]:
        ignored = {"__builtins__", "_getattr_", "_print_"}
        return {
            k: type(v).__name__
            for k, v in self._globals.items()
            if not k.startswith("_") and k not in ignored
        }

    def touch(self) -> None:
        self.last_activity = datetime.now(timezone.utc)

    def _make_globals_copy(self) -> dict[str, object]:
        return dict(self._globals)

    def execute(self, code: str) -> dict:
        self.execution_count += 1
        self.touch()
        stdout_capture = io.StringIO()

        local_vars: dict[str, object] = {}
        exec_globals = self._make_globals_copy()
        exec_globals["_print_"] = _PrintHandlerFactory(buf=stdout_capture)

        wrapped = _wrap_user_code(code)

        try:
            ast = compile_restricted_exec(wrapped)
            if ast.errors:
                raise SyntaxError("\n".join(ast.errors))
        except SyntaxError as e:
            self.error_count += 1
            return {
                "stdout": "",
                "result": None,
                "error": str(e),
                "execution_time_ms": 0,
            }

        start = time.perf_counter()
        try:
            exec(ast.code, exec_globals, local_vars)
            elapsed = int((time.perf_counter() - start) * 1000)
            result = local_vars.get("result")
            self._merge_back(exec_globals, local_vars)

            return {
                "stdout": stdout_capture.getvalue(),
                "result": repr(result) if result is not None else None,
                "error": None,
                "execution_time_ms": elapsed,
            }
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            self.error_count += 1
            self._merge_back(exec_globals, local_vars)
            return {
                "stdout": stdout_capture.getvalue(),
                "result": None,
                "error": f"{type(e).__name__}: {e}",
                "execution_time_ms": elapsed,
            }

    def _merge_back(self, exec_globals: dict, local_vars: dict) -> None:
        for k, v in local_vars.items():
            if not k.startswith("_"):
                self._globals[k] = v

    def state(self) -> dict:
        self.touch()
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "variable_count": self.variable_count,
            "variable_types": self.variable_types,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
        }


def _is_complete_statement(source: str) -> bool:
    try:
        compile(source, "<repl>", "exec")
        return True
    except SyntaxError:
        return False


def _is_expression(source: str) -> bool:
    try:
        compile(source, "<repl>", "eval")
        return True
    except SyntaxError:
        return False


def _wrap_user_code(code: str) -> str:
    code = textwrap.dedent(code).strip()
    lines = code.split("\n")
    last_expr = None
    body_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            body_lines.append(line)
            continue

        parts = [p.strip() for p in stripped.split(";")]
        if len(parts) > 1:
            stmts = []
            for i, part in enumerate(parts):
                if part and _is_expression(part):
                    if i == len(parts) - 1:
                        last_expr = part
                    else:
                        body_lines.append(part)
                else:
                    stmts.append(part)
            if stmts:
                body_lines.append("; ".join(stmts))
            continue

        if _is_expression(stripped):
            last_expr = stripped
        else:
            body_lines.append(line)

    if last_expr is not None:
        body_lines.append(f"result = ({last_expr})")

    return "\n".join(body_lines)


class REPLSessionManager:
    def __init__(self, max_sessions: int = 50, session_ttl_minutes: int = 30):
        self._sessions: dict[str, REPLSession] = {}
        self._max_sessions = max_sessions
        self._session_ttl = timedelta(minutes=session_ttl_minutes)

    def create_session(self) -> str:
        self._evict_stale()
        if len(self._sessions) >= self._max_sessions:
            raise RuntimeError(f"Max REPL sessions ({self._max_sessions}) reached")
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = REPLSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> REPLSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if datetime.now(timezone.utc) - session.last_activity > self._session_ttl:
            self.destroy_session(session_id)
            return None
        return session

    def destroy_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def _evict_stale(self) -> None:
        now = datetime.now(timezone.utc)
        stale = [
            sid for sid, s in self._sessions.items()
            if now - s.last_activity > self._session_ttl
        ]
        for sid in stale:
            self._sessions.pop(sid, None)
            logger.info("Evicted stale REPL session: %s", sid)

    def session_count(self) -> int:
        return len(self._sessions)


class REPLService:
    def __init__(self, max_sessions: int = 50, session_ttl_minutes: int = 30, timeout_seconds: int = 30):
        self._manager = REPLSessionManager(max_sessions, session_ttl_minutes)
        self._timeout = timeout_seconds

    def create_session(self) -> dict:
        session_id = self._manager.create_session()
        session = self._manager.get_session(session_id)
        return {"session_id": session_id, **(session.state() if session else {})}

    async def execute_code(self, session_id: str, code: str) -> dict:
        session = self._manager.get_session(session_id)
        if session is None:
            return {"error": f"Session '{session_id}' not found or expired", "session_id": session_id}

        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, session.execute, code),
                timeout=self._timeout,
            )
            result["session_id"] = session_id
            result["variable_types"] = session.variable_types
            return result
        except asyncio.TimeoutError:
            return {
                "session_id": session_id,
                "stdout": "",
                "result": None,
                "error": f"Execution timed out after {self._timeout}s",
                "execution_time_ms": self._timeout * 1000,
                "variable_types": session.variable_types,
            }

    def get_session_state(self, session_id: str) -> dict | None:
        session = self._manager.get_session(session_id)
        if session is None:
            return None
        return session.state()

    def destroy_session(self, session_id: str) -> bool:
        return self._manager.destroy_session(session_id)

    def session_count(self) -> int:
        return self._manager.session_count()
