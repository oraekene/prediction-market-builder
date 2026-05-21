"""Tests for strategy template CRUD and apply operations."""


class TestTemplateCRUD:
    async def test_create_template(self, client):
        resp = await client.post("/api/strategies/templates", json={
            "name": "Trend Following",
            "description": "Buy when odds trend above 0.6",
            "config": {"mode": "chat", "nodes": [], "edges": []},
            "tags": ["trend", "momentum"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Trend Following"
        assert "id" in data

    async def test_list_templates(self, client):
        await client.post("/api/strategies/templates", json={
            "name": "Template A", "config": {},
        })
        await client.post("/api/strategies/templates", json={
            "name": "Template B", "config": {},
        })
        resp = await client.get("/api/strategies/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    async def test_get_template(self, client):
        created = await client.post("/api/strategies/templates", json={
            "name": "Mean Reversion", "config": {"threshold": 0.3},
        })
        tid = created.json()["id"]
        resp = await client.get(f"/api/strategies/templates/{tid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mean Reversion"

    async def test_update_template(self, client):
        created = await client.post("/api/strategies/templates", json={
            "name": "Old Name", "config": {},
        })
        tid = created.json()["id"]
        resp = await client.put(f"/api/strategies/templates/{tid}", json={
            "name": "New Name", "config": {},
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_delete_template(self, client):
        created = await client.post("/api/strategies/templates", json={
            "name": "To Delete", "config": {},
        })
        tid = created.json()["id"]
        resp = await client.delete(f"/api/strategies/templates/{tid}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/api/strategies/templates/{tid}")
        assert get_resp.status_code == 404

    async def test_get_nonexistent_template(self, client):
        resp = await client.get("/api/strategies/templates/nonexistent-id")
        assert resp.status_code == 404

    async def test_apply_template_creates_strategy(self, client):
        created = await client.post("/api/strategies/templates", json={
            "name": "Scalping", "config": {
                "nodes": [{"id": "1", "type": "threshold"}],
                "edges": [{"from": "1", "to": "2"}],
                "risk_profile": {"max_risk": 0.02},
            },
        })
        tid = created.json()["id"]
        resp = await client.post(f"/api/strategies/templates/{tid}/apply")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Scalping"
        assert data["nodes"] == [{"id": "1", "type": "threshold"}]
        assert data["risk_profile"] == {"max_risk": 0.02}
