import pytest
from datetime import datetime, timezone, timedelta

from app.models.meta_strategy import MetaStrategy, MetaStrategyMode
from app.models.strategy import Strategy
from app.models.user import User


@pytest.fixture(autouse=True)
def _auth_override():
    from app.main import app
    from app.routers.auth import get_current_user
    stub_user = User(id='test-user', email='test@test.com', is_active=True)
    app.dependency_overrides[get_current_user] = lambda: stub_user
    yield


class TestMetaStrategyAPI:
    @pytest.mark.asyncio
    async def test_create_meta_strategy(self, client, session):
        resp = await client.post("/api/meta-strategies", json={
            "name": "Test Meta",
            "description": "Test description",
            "mode": "competition",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Meta"
        assert data["mode"] == "competition"
        assert data["status"] == "active"
        assert data["consumer"] is None
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_meta_strategy_with_config(self, client, session):
        resp = await client.post("/api/meta-strategies", json={
            "name": "Configured MS",
            "mode": "confluence",
            "consumer": "paper_trading",
            "scoring_config": {
                "metrics": {"sharpe": 0.5, "win_rate": 0.3, "profit_factor": 0.1, "max_drawdown": 0.1},
                "evaluation_window_days": 60,
            },
            "promotion_config": {"interval": "weekly", "probation_hours": 72},
            "confluence_config": {"threshold": 2, "source": "top_n", "from_top": 3, "manual_strategy_ids": []},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["consumer"] == "paper_trading"
        assert data["scoring_config"]["metrics"]["sharpe"] == 0.5
        assert data["promotion_config"]["interval"] == "weekly"
        assert data["confluence_config"]["threshold"] == 2

    @pytest.mark.asyncio
    async def test_list_meta_strategies(self, client, session):
        await client.post("/api/meta-strategies", json={"name": "MS1"})
        await client.post("/api/meta-strategies", json={"name": "MS2"})
        resp = await client.get("/api/meta-strategies")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_meta_strategy(self, client, session):
        create_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = create_resp.json()["id"]
        resp = await client.get(f"/api/meta-strategies/{ms_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test MS"

    @pytest.mark.asyncio
    async def test_get_meta_strategy_not_found(self, client, session):
        resp = await client.get("/api/meta-strategies/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_meta_strategy(self, client, session):
        create_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = create_resp.json()["id"]
        resp = await client.put(f"/api/meta-strategies/{ms_id}", json={
            "name": "Updated MS",
            "mode": "confluence",
            "consumer": "live",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated MS"
        assert resp.json()["mode"] == "confluence"
        assert resp.json()["consumer"] == "live"

    @pytest.mark.asyncio
    async def test_delete_meta_strategy(self, client, session):
        create_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/meta-strategies/{ms_id}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/api/meta-strategies/{ms_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_strategy_to_pool(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        strat_resp = await client.post("/api/strategies", json={"name": "Pool Strategy"})
        strat_id = strat_resp.json()["id"]
        resp = await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={strat_id}")
        assert resp.status_code == 200
        assert strat_id in resp.json()["strategy_ids"]

    @pytest.mark.asyncio
    async def test_remove_strategy_from_pool(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        strat_resp = await client.post("/api/strategies", json={"name": "Pool Strategy"})
        strat_id = strat_resp.json()["id"]
        await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={strat_id}")
        resp = await client.delete(f"/api/meta-strategies/{ms_id}/strategies/{strat_id}")
        assert resp.status_code == 200
        assert strat_id not in resp.json()["strategy_ids"]

    @pytest.mark.asyncio
    async def test_rankings_empty_pool(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        resp = await client.get(f"/api/meta-strategies/{ms_id}/rankings")
        assert resp.status_code == 200
        assert resp.json()["rankings"] == []

    @pytest.mark.asyncio
    async def test_evaluate_promotion(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        strat_resp = await client.post("/api/strategies", json={"name": "Winner Strategy"})
        strat_id = strat_resp.json()["id"]
        await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={strat_id}")
        resp = await client.post(f"/api/meta-strategies/{ms_id}/evaluate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_winner_id"] == strat_id
        assert data["last_promotion_at"] is not None
        assert data["promoted"] is True

    @pytest.mark.asyncio
    async def test_force_promote(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        s1 = await client.post("/api/strategies", json={"name": "S1"})
        s2 = await client.post("/api/strategies", json={"name": "S2"})
        s1_id, s2_id = s1.json()["id"], s2.json()["id"]
        await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={s1_id}")
        await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={s2_id}")
        resp = await client.post(f"/api/meta-strategies/{ms_id}/force-promote?strategy_id={s2_id}")
        assert resp.status_code == 200
        assert resp.json()["current_winner_id"] == s2_id

    @pytest.mark.asyncio
    async def test_force_promote_not_in_pool(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Test MS"})
        ms_id = ms_resp.json()["id"]
        resp = await client.post(f"/api/meta-strategies/{ms_id}/force-promote?strategy_id=nonexistent")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_performance_endpoint(self, client, session):
        ms_resp = await client.post("/api/meta-strategies", json={"name": "Perf MS"})
        ms_id = ms_resp.json()["id"]
        strat_resp = await client.post("/api/strategies", json={"name": "S1"})
        strat_id = strat_resp.json()["id"]
        await client.post(f"/api/meta-strategies/{ms_id}/strategies?strategy_id={strat_id}")
        resp = await client.get(f"/api/meta-strategies/{ms_id}/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Perf MS"
        assert len(data["strategy_performances"]) == 1
        assert data["strategy_performances"][0]["id"] == strat_id
