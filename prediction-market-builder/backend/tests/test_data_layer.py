import pytest

try:
    import chromadb  # noqa: F401
    _chromadb_available = True
except ImportError:
    _chromadb_available = False

try:
    import lancedb  # noqa: F401
    _lancedb_available = True
except ImportError:
    _lancedb_available = False


@pytest.mark.skipif(not _chromadb_available, reason="requires chromadb")
def test_chromadb_store_and_recall():
    from app.data.chromadb_manager import ChromaDBManager
    mgr = ChromaDBManager()
    mgr.store_memory(
        "agent_memory", "mem-1",
        "This strategy performed well in high volatility",
        {"type": "success"},
    )
    results = mgr.recall_similar("agent_memory", "volatility strategy", n_results=1)
    assert len(results) >= 1
    assert "mem-1" in [r["id"] for r in results]
    mgr.delete_memory("agent_memory", "mem-1")


class TestDuckDB:
    def test_insert_and_query(self, tmp_path):
        from app.data.duckdb_manager import DuckDBManager
        from app.config import settings
        original = settings.duckdb_path
        settings.duckdb_path = str(tmp_path / "analytics.duckdb")
        DuckDBManager._instance = None
        try:
            mgr = DuckDBManager()
            mgr.insert_market({
                "id": "test-1", "platform": "polymarket", "title": "Test Market",
                "category": "politics", "current_odds": 0.65, "volume": 100000,
                "liquidity": 50000, "participants": 100, "close_time": None,
                "status": "open", "last_updated": None,
            })
            results = mgr.query_markets("category = 'politics'")
            assert len(results) >= 1
            assert results[0]["title"] == "Test Market"
        finally:
            settings.duckdb_path = original
            DuckDBManager._instance = None

    def test_top_categories(self, tmp_path):
        from app.data.duckdb_manager import DuckDBManager
        from app.config import settings
        original = settings.duckdb_path
        settings.duckdb_path = str(tmp_path / "analytics.duckdb")
        DuckDBManager._instance = None
        try:
            mgr = DuckDBManager()
            categories = mgr.get_top_categories()
            assert isinstance(categories, list)
        finally:
            settings.duckdb_path = original
            DuckDBManager._instance = None


@pytest.mark.skipif(not _lancedb_available, reason="requires lancedb")
class TestLanceDB:
    def test_upsert_and_search(self, tmp_path):
        from app.data.lancedb_manager import LanceDBManager
        from app.config import settings
        original = settings.lancedb_path
        settings.lancedb_path = str(tmp_path / "lancedb")
        LanceDBManager._instance = None
        try:
            mgr = LanceDBManager()
            mgr.upsert_market_vector(
                id="vec-1", market_id="market-1", platform="polymarket",
                embedding=[0.1] * 384, text="Test market",
                metadata={"category": "politics"},
            )
            results = mgr.search_markets([0.1] * 384, top_k=10)
            assert any(r["market_id"] == "market-1" for r in results)
        finally:
            settings.lancedb_path = original
            LanceDBManager._instance = None

    def test_delete_vector(self, tmp_path):
        from app.data.lancedb_manager import LanceDBManager
        from app.config import settings
        original = settings.lancedb_path
        settings.lancedb_path = str(tmp_path / "lancedb_del")
        LanceDBManager._instance = None
        try:
            mgr = LanceDBManager()
            mgr.upsert_market_vector(
                id="vec-del", market_id="market-del", platform="kalshi",
                embedding=[0.2] * 384, text="Delete test",
            )
            mgr.delete_market_vector("vec-del")
            results = mgr.search_markets([0.2] * 384, top_k=10)
            assert all(r["market_id"] != "market-del" for r in results)
        finally:
            settings.lancedb_path = original
            LanceDBManager._instance = None

    def test_search_with_filter(self, tmp_path):
        from app.data.lancedb_manager import LanceDBManager
        from app.config import settings
        original = settings.lancedb_path
        settings.lancedb_path = str(tmp_path / "lancedb_filter")
        LanceDBManager._instance = None
        try:
            mgr = LanceDBManager()
            mgr.upsert_market_vector(id="v1", market_id="m1", platform="polymarket",
                                     embedding=[0.1] * 384, text="A")
            mgr.upsert_market_vector(id="v2", market_id="m2", platform="polymarket",
                                     embedding=[0.1] * 384, text="B")
            results = mgr.search_markets([0.1] * 384, filter_ids=["m1"], top_k=10)
            assert len(results) == 1
            assert results[0]["market_id"] == "m1"
        finally:
            settings.lancedb_path = original
            LanceDBManager._instance = None
