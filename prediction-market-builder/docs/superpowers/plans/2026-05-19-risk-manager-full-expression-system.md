# Risk Manager Full Expression System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full risk strategy expression system with DB persistence, condition/action rules engine, and CRUD API.

**Architecture:** Extends the existing `RiskManager`/`RiskProfile` with a rule-based expression engine stored as `RiskTemplate` in the DB. Each template has an ordered list of rules, each with a condition (when to fire) and action (what to do). First matching rule wins; fallback to default RiskProfile evaluation.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite (via existing DB), Pydantic, pytest

---

### Task 1: RiskTemplate Model

**Files:**
- Create: `app/models/risk_template.py`
- Modify: `app/database.py` (import model so alembic detects it)
- Test: `tests/test_risk_templates.py`

- [ ] **Step 1: Write the failing model test**

```python
import pytest
from app.models.risk_template import RiskTemplate


@pytest.mark.asyncio
async def test_create_risk_template_model():
    rt = RiskTemplate(
        user_id="user_1",
        name="Conservative Kelly",
        description="Half-kelly with 15% drawdown limit",
        rules=[
            {
                "condition": {"type": "max_drawdown", "params": {"threshold": 0.15}},
                "action": {"type": "reject", "params": {}},
            },
            {
                "condition": {"type": "min_confidence", "params": {"min_confidence": 0.5}},
                "action": {"type": "approve", "params": {}},
            },
        ],
    )
    assert rt.user_id == "user_1"
    assert rt.name == "Conservative Kelly"
    assert len(rt.rules) == 2
    assert rt.id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_risk_templates.py::test_create_risk_template_model -v`
Expected: ImportError, RiskTemplate not defined

- [ ] **Step 3: Create the model**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RiskTemplate(Base):
    __tablename__ = "risk_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_risk_templates.py::test_create_risk_template_model -v`
Expected: PASS

- [ ] **Step 5: Commit** (skip unless user asks)

---

### Task 2: Risk Expression Engine

**Files:**
- Create: `app/services/risk_engine.py`
- Test: `tests/test_risk_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.services.risk_engine import evaluate_risk_template, evaluate_rule, CONDITION_EVALUATORS, ACTION_EXECUTORS


def test_max_drawdown_condition_triggers():
    condition = {"type": "max_drawdown", "params": {"threshold": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 8000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_max_drawdown_condition_does_not_trigger():
    condition = {"type": "max_drawdown", "params": {"threshold": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 9500, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is False


def test_min_confidence_condition_triggers():
    condition = {"type": "min_confidence", "params": {"min_confidence": 0.5}}
    signal = {"probability": 0.7, "confidence": 0.3, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_min_confidence_does_not_trigger():
    condition = {"type": "min_confidence", "params": {"min_confidence": 0.5}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is False


def test_max_position_size_triggers():
    condition = {"type": "max_position_size", "params": {"max_size": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio, suggested_size=0.15) is True


def test_always_condition():
    condition = {"type": "always", "params": {}}
    signal = {}
    portfolio = {}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_reject_action():
    result = {"approved": True, "suggested_size": 0.1, "violations": []}
    action = {"type": "reject", "params": {}}
    ACTION_EXECUTORS["reject"](result, action, signal={}, portfolio={})
    assert result["approved"] is False
    assert "rule_rejected" in result["violations"]


def test_approve_action():
    result = {"approved": False, "suggested_size": 0.0, "violations": ["rule_rejected"]}
    action = {"type": "approve", "params": {}}
    ACTION_EXECUTORS["approve"](result, action, signal={}, portfolio={})
    assert result["approved"] is True
    assert "rule_approved" in result["violations"]
    assert "rule_rejected" not in result["violations"]


def test_scale_position_action():
    result = {"approved": True, "suggested_size": 0.2, "violations": []}
    action = {"type": "scale_position", "params": {"factor": 0.5}}
    ACTION_EXECUTORS["scale_position"](result, action, signal={"probability": 0.5, "market_odds": 0.5}, portfolio={})
    assert result["suggested_size"] == 0.1


def test_fixed_fraction_action():
    result = {"approved": True, "suggested_size": 0.0, "violations": []}
    action = {"type": "fixed_fraction", "params": {"fraction": 0.02}}
    ACTION_EXECUTORS["fixed_fraction"](result, action, signal={}, portfolio={"current_capital": 10000})
    assert result["suggested_size"] == 0.02


def test_evaluate_risk_template_full_pipeline():
    from app.services.risk_engine import evaluate_risk_template
    from dataclasses import dataclass

    @dataclass
    class FakeTemplate:
        rules = [
            {"condition": {"type": "max_drawdown", "params": {"threshold": 0.15}}, "action": {"type": "reject", "params": {}}},
            {"condition": {"type": "always", "params": {}}, "action": {"type": "approve", "params": {}}},
        ]

    result = evaluate_risk_template(
        FakeTemplate(),
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 8000, "peak_capital": 10000},
    )
    assert result["approved"] is False
    assert "max_drawdown" in result["matched_rule"]


def test_evaluate_risk_template_falls_back_to_default():
    from app.services.risk_engine import evaluate_risk_template

    @dataclass
    class FakeTemplate:
        rules = []

    result = evaluate_risk_template(
        FakeTemplate(),
        signal={"probability": 0.5, "confidence": 0.3, "market_odds": 0.5},
        portfolio={"current_capital": 10000, "peak_capital": 10000},
    )
    assert result["approved"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_risk_engine.py -v`
Expected: ImportError or NameError for undefined functions

- [ ] **Step 3: Create risk_engine.py**

```python
from typing import Any
from dataclasses import dataclass


@dataclass
class RuleMatch:
    condition_type: str
    action_type: str


DEFAULT_PROFILE = {
    "max_position_size": 0.2,
    "max_drawdown": 0.15,
    "stop_loss": 0.1,
    "kelly_fraction": 0.25,
    "max_correlation": 0.7,
    "min_confidence": 0.6,
}


def evaluate_risk_template(template, signal: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
    result = {"approved": True, "suggested_size": 0.0, "violations": [], "matched_rule": None}

    for rule in template.rules:
        condition = rule.get("condition", {})
        action = rule.get("action", {})
        cond_type = condition.get("type", "always")
        action_type = action.get("type", "approve")

        if cond_type not in CONDITION_EVALUATORS:
            continue

        cond_result = CONDITION_EVALUATORS[cond_type](condition.get("params", {}), signal, portfolio, result["suggested_size"])
        if cond_result:
            if action_type in ACTION_EXECUTORS:
                ACTION_EXECUTORS[action_type](result, action.get("params", {}), signal, portfolio)
            result["matched_rule"] = cond_type
            break

    if result["matched_rule"] is None:
        fallback_evaluate(result, signal, portfolio)

    return result


def fallback_evaluate(result: dict, signal: dict, portfolio: dict) -> None:
    current_drawdown = _calc_drawdown(portfolio)
    confidence = signal.get("confidence", 0.5)
    if current_drawdown >= DEFAULT_PROFILE["max_drawdown"]:
        result["approved"] = False
        result["violations"].append("max_drawdown_reached")
    if confidence < DEFAULT_PROFILE["min_confidence"]:
        result["approved"] = False
        result["violations"].append("low_confidence")
    if result["approved"]:
        suggested = _kelly_size(signal, DEFAULT_PROFILE["kelly_fraction"])
        result["suggested_size"] = round(min(suggested, DEFAULT_PROFILE["max_position_size"]), 4)
    result["matched_rule"] = "default_profile"


def _calc_drawdown(portfolio: dict) -> float:
    peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
    current = portfolio.get("current_capital", 10000)
    if peak <= 0:
        return 0
    return (peak - current) / peak


def _kelly_size(signal: dict, kelly_fraction: float) -> float:
    probability = signal.get("probability", 0.5)
    odds = signal.get("market_odds", 0.5)
    if odds <= 0:
        return 0
    b = (1 - odds) / odds
    p = probability
    q = 1 - p
    if b <= 0:
        return 0
    kelly = (p * b - q) / b
    return max(0, kelly * kelly_fraction)


def evaluate_rule(condition: dict, signal: dict, portfolio: dict, suggested_size: float = 0.0) -> bool:
    cond_type = condition.get("type", "always")
    params = condition.get("params", {})
    if cond_type in CONDITION_EVALUATORS:
        return CONDITION_EVALUATORS[cond_type](params, signal, portfolio, suggested_size)
    return False


def _cond_max_drawdown(params: dict, signal: dict, portfolio: dict, _size: float) -> bool:
    return _calc_drawdown(portfolio) >= params.get("threshold", 0.15)


def _cond_min_confidence(params: dict, signal: dict, _portfolio: dict, _size: float) -> bool:
    return signal.get("confidence", 0) < params.get("min_confidence", 0.5)


def _cond_max_position_size(params: dict, _signal: dict, _portfolio: dict, suggested_size: float) -> bool:
    return suggested_size > params.get("max_size", 0.2)


def _cond_always(_params: dict, _signal: dict, _portfolio: dict, _size: float) -> bool:
    return True


CONDITION_EVALUATORS = {
    "max_drawdown": _cond_max_drawdown,
    "min_confidence": _cond_min_confidence,
    "max_position_size": _cond_max_position_size,
    "always": _cond_always,
}


def _act_reject(result: dict, _params: dict, _signal: dict, _portfolio: dict) -> None:
    result["approved"] = False
    result["suggested_size"] = 0.0
    result["violations"].append("rule_rejected")


def _act_approve(result: dict, _params: dict, _signal: dict, _portfolio: dict) -> None:
    result["approved"] = True
    if "rule_rejected" in result["violations"]:
        result["violations"].remove("rule_rejected")
    result["violations"].append("rule_approved")


def _act_scale_position(result: dict, params: dict, signal: dict, _portfolio: dict) -> None:
    factor = params.get("factor", 1.0)
    current = result.get("suggested_size", 0.0)
    if current == 0.0:
        current = _kelly_size(signal, DEFAULT_PROFILE["kelly_fraction"])
    result["suggested_size"] = round(current * factor, 4)


def _act_fixed_fraction(result: dict, params: dict, _signal: dict, _portfolio: dict) -> None:
    result["suggested_size"] = params.get("fraction", 0.01)


ACTION_EXECUTORS = {
    "reject": _act_reject,
    "approve": _act_approve,
    "scale_position": _act_scale_position,
    "fixed_fraction": _act_fixed_fraction,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_risk_engine.py -v`
Expected: 12-13 tests PASS

---

### Task 3: Risk Templates API Router

**Files:**
- Create: `app/routers/risk_templates.py`
- Modify: `app/main.py` (register router)
- Test: `tests/test_risk_templates_api.py`

- [ ] **Step 1: Write failing API tests**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_risk_template(client):
    resp = await client.post("/api/risk-templates", json={
        "name": "Aggressive Kelly",
        "description": "Full kelly, 25% drawdown",
        "rules": [
            {"condition": {"type": "max_drawdown", "params": {"threshold": 0.25}}, "action": {"type": "reject", "params": {}}},
            {"condition": {"type": "always", "params": {}}, "action": {"type": "approve", "params": {}}},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Aggressive Kelly"
    assert len(body["rules"]) == 2


@pytest.mark.asyncio
async def test_list_risk_templates(client):
    resp = await client.get("/api/risk-templates")
    assert resp.status_code == 200
    body = resp.json()
    assert "templates" in body


@pytest.mark.asyncio
async def test_get_risk_template(client):
    create_resp = await client.post("/api/risk-templates", json={"name": "Test", "rules": []})
    tid = create_resp.json()["id"]
    resp = await client.get(f"/api/risk-templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test"


@pytest.mark.asyncio
async def test_update_risk_template(client):
    create_resp = await client.post("/api/risk-templates", json={"name": "Old", "rules": []})
    tid = create_resp.json()["id"]
    resp = await client.put(f"/api/risk-templates/{tid}", json={"name": "Updated", "rules": []})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_risk_template(client):
    create_resp = await client.post("/api/risk-templates", json={"name": "ToDelete", "rules": []})
    tid = create_resp.json()["id"]
    resp = await client.delete(f"/api/risk-templates/{tid}")
    assert resp.status_code == 200
    get_resp = await client.get(f"/api/risk-templates/{tid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_apply_risk_template(client):
    create_resp = await client.post("/api/risk-templates", json={
        "name": "Test",
        "rules": [
            {"condition": {"type": "max_drawdown", "params": {"threshold": 0.1}}, "action": {"type": "reject", "params": {}}},
        ],
    })
    tid = create_resp.json()["id"]
    resp = await client.post(f"/api/risk-templates/{tid}/evaluate", json={
        "signal": {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        "portfolio": {"current_capital": 8000, "peak_capital": 10000},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "approved" in body
    assert body["approved"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_risk_templates_api.py -v`
Expected: 404 errors since router not registered

- [ ] **Step 3: Create the router file**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.risk_template import RiskTemplate
from app.services.risk_engine import evaluate_risk_template

router = APIRouter(prefix="/api/risk-templates", tags=["risk-templates"])


@router.post("")
async def create_risk_template(body: dict, session: AsyncSession = Depends(get_session)):
    template = RiskTemplate(
        name=body["name"],
        description=body.get("description", ""),
        rules=body.get("rules", []),
        user_id=body.get("user_id", "default"),
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return _template_response(template)


@router.get("")
async def list_risk_templates(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(RiskTemplate).order_by(RiskTemplate.created_at.desc()))
    templates = [t for t in rows.scalars().all()]
    return {"templates": [_template_response(t) for t in templates]}


@router.get("/{template_id}")
async def get_risk_template(template_id: str, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    return _template_response(template)


@router.put("/{template_id}")
async def update_risk_template(template_id: str, body: dict, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    if "name" in body:
        template.name = body["name"]
    if "description" in body:
        template.description = body.get("description", "")
    if "rules" in body:
        template.rules = body["rules"]
    await session.commit()
    await session.refresh(template)
    return _template_response(template)


@router.delete("/{template_id}")
async def delete_risk_template(template_id: str, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    await session.delete(template)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{template_id}/evaluate")
async def evaluate_risk_template_endpoint(template_id: str, body: dict, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    signal = body.get("signal", {})
    portfolio = body.get("portfolio", {})
    result = evaluate_risk_template(template, signal, portfolio)
    return result


def _template_response(t: RiskTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "rules": t.rules,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
```

- [ ] **Step 4: Register router in main.py**

```python
from app.routers import auth, markets, strategies, chat, portfolio, analytics, risk_templates
...
app.include_router(risk_templates.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_risk_templates_api.py -v`
Expected: All 6 tests PASS

---

### Task 4: Full Test Suite Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All existing tests still pass. Count: 51 + new tests.
