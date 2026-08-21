from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.alchemy_service import (
    AlchemyService,
    AlchemyRequest,
    AlchemyReport,
    AlchemyConnection,
    ConnectionEngine,
)
from app.ai.domain_providers import DomainRegistry, DomainProvider, DomainData, DomainItem
from app.ai.domain_providers.market_provider import MarketDomainProvider
from app.ai.domain_providers.news_provider import NewsDomainProvider
from app.ai.domain_providers.memory_provider import MemoryDomainProvider


@pytest.fixture
def mock_chromadb():
    db = MagicMock()
    db.store_memory = MagicMock()
    db.recall_similar = MagicMock(return_value=[])
    db.client.get_collection = MagicMock()
    db.client.create_collection = MagicMock()
    return db


@pytest.fixture
def mock_hermes():
    h = AsyncMock()
    h.available = False
    return h


@pytest.fixture
def mock_embed():
    e = MagicMock()
    e.encode = MagicMock(return_value=[[0.1] * 384, [0.9] * 384, [0.15] * 384])
    return e


@pytest.fixture
def sample_market_provider():
    p = MagicMock(spec=DomainProvider)
    p.name = "markets"
    p.description = "Test markets"
    p.query = AsyncMock(return_value=DomainData(
        domain="markets",
        items=[
            DomainItem(
                text="Will BTC exceed $100k by Dec 2026? odds=0.72 volume=2500000 liquidity=800000",
                metadata={"odds": 0.72, "volume": 2500000, "category": "Crypto"},
                source="pm-001",
                timestamp=datetime.now(timezone.utc),
            ),
            DomainItem(
                text="Will the Fed cut rates in Q3 2026? odds=0.45 volume=1800000 liquidity=600000",
                metadata={"odds": 0.45, "volume": 1800000, "category": "Economy"},
                source="pm-002",
                timestamp=datetime.now(timezone.utc),
            ),
        ],
        query_time_ms=5,
    ))
    return p


@pytest.fixture
def sample_news_provider():
    p = MagicMock(spec=DomainProvider)
    p.name = "news"
    p.description = "Test news"
    p.query = AsyncMock(return_value=DomainData(
        domain="news",
        items=[
            DomainItem(
                text="SEC Delays ETH ETF Decision Regulatory uncertainty continues",
                metadata={"source": "CryptoNews"},
                source="https://example.com/news/1",
                timestamp=datetime.now(timezone.utc),
            ),
        ],
        query_time_ms=10,
    ))
    return p


class TestDomainRegistry:
    def test_register_and_select(self):
        reg = DomainRegistry()
        p = MagicMock(spec=DomainProvider)
        p.name = "markets"
        reg.register(p)
        selected = reg.select("test query")
        assert len(selected) == 1
        assert selected[0].name == "markets"

    def test_select_prioritizes_relevant_domains(self):
        reg = DomainRegistry()
        for name in ["markets", "news", "memory"]:
            p = MagicMock(spec=DomainProvider)
            p.name = name
            reg.register(p)
        selected = reg.select("what are the odds of btc")
        assert selected[0].name == "markets"

    def test_get_provider_returns_none_for_unknown(self):
        reg = DomainRegistry()
        assert reg.get_provider("nonexistent") is None


class TestMarketDomainProvider:
    @pytest.mark.asyncio
    async def test_query_returns_items(self):
        mock_agg = AsyncMock()
        mock_agg.fetch_all = AsyncMock(return_value=[
            {"title": "Will BTC exceed $100k?", "current_odds": 0.72, "volume": 2500000,
             "liquidity": 800000, "participants": 1200, "category": "Crypto",
             "platform": "polymarket", "platform_market_id": "pm-001"},
        ])
        provider = MarketDomainProvider(market_aggregator=mock_agg)
        data = await provider.query("BTC")
        assert data.domain == "markets"
        assert len(data.items) == 1
        assert "BTC" in data.items[0].text

    @pytest.mark.asyncio
    async def test_query_empty_without_match(self):
        mock_agg = AsyncMock()
        mock_agg.fetch_all = AsyncMock(return_value=[
            {"title": "Will ETH hit $10k?", "current_odds": 0.3, "volume": 1000,
             "liquidity": 500, "participants": 100, "category": "Crypto",
             "platform": "polymarket", "platform_market_id": "pm-002"},
        ])
        provider = MarketDomainProvider(market_aggregator=mock_agg)
        data = await provider.query("SOL")
        assert len(data.items) == 0


class TestNewsDomainProvider:
    @pytest.mark.asyncio
    async def test_query_returns_mock_headlines(self):
        provider = NewsDomainProvider()
        data = await provider.query("ETH")
        assert data.domain == "news"
        assert len(data.items) > 0
        assert "eth" in data.items[0].text.lower() or "ETH" in data.items[0].text

    @pytest.mark.asyncio
    async def test_mock_headlines_no_match_shows_fallback(self):
        provider = NewsDomainProvider()
        data = await provider.query("zzzznotarealkeyword")
        assert len(data.items) == 1
        assert "zzzznotarealkeyword" in data.items[0].text


class TestMemoryDomainProvider:
    @pytest.mark.asyncio
    async def test_query_without_chromadb_returns_empty(self):
        provider = MemoryDomainProvider(chromadb=None)
        data = await provider.query("test")
        assert data.domain == "memory"
        assert len(data.items) == 0


class TestConnectionEngine:
    @pytest.mark.asyncio
    async def test_find_connections_returns_cross_domain_pairs(self, mock_embed):
        engine = ConnectionEngine(embedding_service=mock_embed)
        domain_data = {
            "markets": DomainData(domain="markets", items=[
                DomainItem(text="BTC to $100k odds=0.72", metadata={"odds": 0.72}),
            ]),
            "news": DomainData(domain="news", items=[
                DomainItem(text="Institutional Bitcoin buying surges", metadata={}),
            ]),
        }
        conns = await engine.find_connections(domain_data, "BTC")
        assert len(conns) >= 1
        assert conns[0].source_domain != conns[0].target_domain

    @pytest.mark.asyncio
    async def test_find_connections_requires_multiple_domains(self, mock_embed):
        engine = ConnectionEngine(embedding_service=mock_embed)
        domain_data = {
            "markets": DomainData(domain="markets", items=[
                DomainItem(text="Test market", metadata={}),
            ]),
        }
        conns = await engine.find_connections(domain_data, "test")
        assert len(conns) == 0

    @pytest.mark.asyncio
    async def test_cosine_similarity_basic(self):
        engine = ConnectionEngine()
        sim = engine._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert abs(sim - 1.0) < 0.001
        sim2 = engine._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim2 - 0.0) < 0.001

    def test_infer_correlation_type(self):
        engine = ConnectionEngine()
        item_a = DomainItem(text="a", metadata={"odds": 0.8})
        item_b = DomainItem(text="b", metadata={"odds": 0.3})
        assert engine._infer_correlation_type(item_a, item_b) == "leading_indicator"
        item_c = DomainItem(text="c", metadata={"odds": 0.79})
        assert engine._infer_correlation_type(item_a, item_c) == "confirms"

    @pytest.mark.asyncio
    async def test_novelty_returns_1_when_no_chromadb(self):
        engine = ConnectionEngine()
        score = await engine._check_novelty("a", "b", "text_a", "text_b")
        assert score == 1.0


class TestAlchemyService:
    @pytest.mark.asyncio
    async def test_analyze_returns_report(self):
        registry = DomainRegistry()
        p = MagicMock(spec=DomainProvider)
        p.name = "markets"
        p.query = AsyncMock(return_value=DomainData(domain="markets", items=[
            DomainItem(text="Test market odds=0.5", metadata={"odds": 0.5}),
        ]))
        registry.register(p)

        mock_embed = MagicMock()
        mock_embed.encode = MagicMock(return_value=[[0.5] * 384])
        engine = ConnectionEngine(embedding_service=mock_embed)

        service = AlchemyService(domain_registry=registry, connection_engine=engine)
        report = await service.analyze(AlchemyRequest(query="test query"))

        assert isinstance(report, AlchemyReport)
        assert report.query == "test query"
        assert "markets" in report.domains_queried

    @pytest.mark.asyncio
    async def test_analyze_with_multiple_domains_finds_connections(self):
        registry = DomainRegistry()
        p1 = MagicMock(spec=DomainProvider)
        p1.name = "markets"
        p1.query = AsyncMock(return_value=DomainData(domain="markets", items=[
            DomainItem(text="BTC to $100k odds=0.72", metadata={"odds": 0.72}),
        ]))
        p2 = MagicMock(spec=DomainProvider)
        p2.name = "news"
        p2.query = AsyncMock(return_value=DomainData(domain="news", items=[
            DomainItem(text="Institutional Bitcoin buying surges", metadata={}),
        ]))
        registry.register(p1)
        registry.register(p2)

        mock_embed = MagicMock()
        mock_embed.encode = MagicMock(return_value=[
            [0.1] * 384,
            [0.9] * 384,
        ])
        engine = ConnectionEngine(embedding_service=mock_embed)

        service = AlchemyService(domain_registry=registry, connection_engine=engine)
        report = await service.analyze(AlchemyRequest(query="BTC"))
        assert len(report.connections) >= 1

    @pytest.mark.asyncio
    async def test_check_existing_returns_not_found(self, mock_chromadb):
        service = AlchemyService(chromadb=mock_chromadb)
        result = await service.check_existing("test")
        assert result["found"] is False
        assert result["query"] == "test"

    @pytest.mark.asyncio
    async def test_check_existing_without_chromadb(self):
        service = AlchemyService()
        result = await service.check_existing("test")
        assert result["found"] is False

    def test_get_history_empty(self):
        service = AlchemyService()
        assert service.get_history() == []

    def test_get_report_not_found(self):
        service = AlchemyService()
        assert service.get_report("nonexistent") is None

    @pytest.mark.asyncio
    async def test_analyze_gracefully_handles_provider_error(self):
        registry = DomainRegistry()
        p = MagicMock(spec=DomainProvider)
        p.name = "markets"
        p.query = AsyncMock(side_effect=RuntimeError("connection failed"))
        registry.register(p)

        service = AlchemyService(domain_registry=registry)
        report = await service.analyze(AlchemyRequest(query="test"))
        assert isinstance(report, AlchemyReport)

    def test_domain_registry_excludes_stubs_by_default(self):
        from app.ai.domain_providers import (
            OnChainDomainProvider, MacrosDomainProvider,
            SocialDomainProvider, LegalDomainProvider,
        )
        reg = DomainRegistry()
        reg.register(OnChainDomainProvider())
        reg.register(MacrosDomainProvider())
        reg.register(SocialDomainProvider())
        reg.register(LegalDomainProvider())
        selected = reg.select("any query")
        stub_names = {p.name for p in selected}
        assert "onchain" not in stub_names
        assert "macros" not in stub_names
        assert "social" not in stub_names
        assert "legal" not in stub_names
