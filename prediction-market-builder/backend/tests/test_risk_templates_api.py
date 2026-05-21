import pytest


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
