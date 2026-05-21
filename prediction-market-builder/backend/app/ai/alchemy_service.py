from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.ai.domain_providers import DomainRegistry, DomainData, DomainItem
# Lazy import for EmbeddingService to avoid requiring sentence-transformers at import time

logger = logging.getLogger(__name__)


class AlchemyRequest(BaseModel):
    query: str
    market_id: str | None = None
    force_refresh: bool = False


class AlchemyConnection(BaseModel):
    source_domain: str
    source_entity: str
    target_domain: str
    target_entity: str
    correlation_type: str
    similarity_score: float
    strength: float
    novelty_score: float
    explanation: str
    evidence: list[str]


class AlchemyReport(BaseModel):
    id: str
    query: str
    timestamp: datetime
    domains_queried: list[str]
    connections: list[AlchemyConnection]
    summary: str
    novelty_score: float


class ConnectionEngine:
    def __init__(
        self,
        embedding_service=None,
        hermes=None,
        chromadb=None,
        similarity_threshold: float = 0.65,
    ):
        if embedding_service is not None:
            self._embed = embedding_service
        else:
            try:
                from app.ai.embeddings import EmbeddingService
                self._embed = EmbeddingService()
            except ImportError:
                logger.warning("sentence-transformers not available; embedding-based connection detection disabled")
                self._embed = None
        self._hermes = hermes
        self._chromadb = chromadb
        self._threshold = similarity_threshold

    async def find_connections(
        self,
        domain_data: dict[str, DomainData],
        query: str,
    ) -> list[AlchemyConnection]:
        all_items: list[tuple[str, DomainItem]] = []
        for domain, data in domain_data.items():
            if data.error and data.error != "not_implemented":
                continue
            for item in data.items:
                all_items.append((domain, item))

        if len(all_items) < 2:
            return []

        if self._embed is None:
            return []

        texts = [item.text for _, item in all_items]
        raw_embeddings = self._embed.encode(texts)
        embeddings = self._ensure_2d(raw_embeddings, len(texts))

        n = len(all_items)
        connections: list[AlchemyConnection] = []
        for i in range(n):
            for j in range(i + 1, n):
                dom_i, item_i = all_items[i]
                dom_j, item_j = all_items[j]
                if dom_i == dom_j:
                    continue
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                if sim < self._threshold:
                    continue
                corr_type = self._infer_correlation_type(item_i, item_j)
                explanation = await self._generate_explanation(query, dom_i, item_i, dom_j, item_j, sim)
                novelty = await self._check_novelty(dom_i, dom_j, item_i.text, item_j.text)
                connections.append(AlchemyConnection(
                    source_domain=dom_i,
                    source_entity=item_i.text[:100],
                    target_domain=dom_j,
                    target_entity=item_j.text[:100],
                    correlation_type=corr_type,
                    similarity_score=round(sim, 4),
                    strength=round(min(1.0, sim * (1.2 if explanation else 1.0)), 4),
                    novelty_score=novelty,
                    explanation=explanation or f"Connection between {dom_i} and {dom_j} (similarity={sim:.3f})",
                    evidence=[item_i.text, item_j.text],
                ))

        connections.sort(key=lambda c: c.strength, reverse=True)
        return connections

    def _ensure_2d(self, embeddings: Any, expected_count: int) -> list[list[float]]:
        if not embeddings:
            return [[0.0] * 384 for _ in range(expected_count)]
        if isinstance(embeddings, list):
            if embeddings and not isinstance(embeddings[0], list):
                return [embeddings]
            return embeddings
        return [[0.0] * 384 for _ in range(expected_count)]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _infer_correlation_type(self, item_a: DomainItem, item_b: DomainItem) -> str:
        meta_a = item_a.metadata or {}
        meta_b = item_b.metadata or {}
        val_a = meta_a.get("odds") or meta_a.get("price") or meta_a.get("sentiment")
        val_b = meta_b.get("odds") or meta_b.get("price") or meta_b.get("sentiment")
        if val_a is not None and val_b is not None:
            if abs(float(val_a) - float(val_b)) < 0.1:
                return "confirms"
            if abs(float(val_a) - 0.5) > abs(float(val_b) - 0.5):
                return "leading_indicator"
            return "contradicts"
        return "confirms"

    async def _generate_explanation(
        self,
        query: str,
        dom_a: str,
        item_a: DomainItem,
        dom_b: str,
        item_b: DomainItem,
        sim: float,
    ) -> str | None:
        if not self._hermes or not self._hermes.available:
            return None
        prompt = (
            f"Query: {query}\n"
            f"Domain A ({dom_a}): {item_a.text}\n"
            f"Domain B ({dom_b}): {item_b.text}\n"
            f"Similarity: {sim:.3f}\n\n"
            f"Explain the connection between these two data points in the context of "
            f"prediction markets. What does this cross-domain signal mean for a trader?"
        )
        try:
            result = await self._hermes.process_message(prompt, {"user_id": "alchemy"})
            return result.get("response", "")
        except Exception as e:
            logger.debug("Explanation generation failed: %s", e)
            return None

    async def _check_novelty(self, dom_a: str, dom_b: str, text_a: str, text_b: str) -> float:
        if not self._chromadb:
            return 1.0
        try:
            results = self._chromadb.recall_similar(
                "alchemy_memory",
                f"{dom_a} {dom_b} {text_a[:50]} {text_b[:50]}",
                n_results=5,
            )
            if not results:
                return 1.0
            for r in results:
                meta = r.get("metadata", {})
                if meta.get("source_domain") == dom_a and meta.get("target_domain") == dom_b:
                    seen_count = sum(
                        1 for rr in results
                        if rr.get("metadata", {}).get("source_domain") == dom_a
                        and rr.get("metadata", {}).get("target_domain") == dom_b
                    )
                    return round(max(0.1, 1.0 - seen_count * 0.2), 4)
            return 0.8
        except Exception as e:
            logger.debug("Novelty check failed: %s", e)
            return 1.0


class AlchemyService:
    def __init__(
        self,
        domain_registry: DomainRegistry | None = None,
        connection_engine: ConnectionEngine | None = None,
        chromadb=None,
        hermes=None,
    ):
        self._registry = domain_registry or DomainRegistry()
        self._chromadb = chromadb
        self._hermes = hermes
        self._engine = connection_engine or ConnectionEngine(hermes=hermes, chromadb=chromadb)
        self._reports: dict[str, AlchemyReport] = {}

    def _ensure_collections(self) -> None:
        if self._chromadb:
            try:
                self._chromadb.client.get_collection("alchemy_memory")
            except Exception:
                self._chromadb.client.create_collection("alchemy_memory")
            try:
                self._chromadb.client.get_collection("alchemy_cache")
            except Exception:
                self._chromadb.client.create_collection("alchemy_cache")

    async def analyze(self, request: AlchemyRequest) -> AlchemyReport:
        start = time.time()

        if not request.force_refresh:
            cached = self._check_cache(request.query)
            if cached:
                return cached

        selected = self._registry.select(request.query)

        domain_data: dict[str, DomainData] = {}
        domains_queried: list[str] = []
        for provider in selected:
            try:
                data = await provider.query(request.query)
                domain_data[provider.name] = data
                if data.error and data.error != "not_implemented":
                    logger.warning("Domain %s returned error: %s", provider.name, data.error)
                    continue
                domains_queried.append(provider.name)
            except Exception as e:
                logger.warning("Domain %s query failed: %s", provider.name, e)

        connections = await self._engine.find_connections(domain_data, request.query)

        summary = await self._generate_summary(request.query, connections)
        novelty = round(max((c.novelty_score for c in connections), default=0.0), 4)

        report = AlchemyReport(
            id=uuid.uuid4().hex,
            query=request.query,
            timestamp=datetime.now(timezone.utc),
            domains_queried=domains_queried,
            connections=connections,
            summary=summary or (
                f"Analyzed {len(domains_queried)} domains ({', '.join(domains_queried)}). "
                f"Found {len(connections)} cross-domain connection{'s' if len(connections) != 1 else ''}."
            ),
            novelty_score=novelty,
        )

        self._store_report(report)
        self._reports[report.id] = report

        elapsed = int((time.time() - start) * 1000)
        logger.info(
            "Alchemy analyze complete: %s domains, %d connections, %dms",
            len(domains_queried), len(connections), elapsed,
        )
        return report

    def _check_cache(self, query: str) -> AlchemyReport | None:
        if not self._chromadb:
            return None
        try:
            results = self._chromadb.recall_similar("alchemy_cache", query, n_results=1)
            if results:
                cached_id = results[0].get("metadata", {}).get("report_id")
                if cached_id and cached_id in self._reports:
                    return self._reports[cached_id]
        except Exception:
            pass
        return None

    async def check_existing(self, query: str) -> dict[str, Any]:
        if not self._chromadb:
            return {"known_connections": [], "found": False, "query": query}
        try:
            results = self._chromadb.recall_similar("alchemy_memory", query, n_results=5)
            return {
                "found": len(results) > 0,
                "known_connections": [
                    {"text": r.get("text", ""), "metadata": r.get("metadata", {}), "id": r.get("id", "")}
                    for r in results
                ],
                "query": query,
            }
        except Exception as e:
            logger.warning("check_existing failed: %s", e)
            return {"error": str(e), "found": False, "query": query}

    def _store_report(self, report: AlchemyReport) -> None:
        if not self._chromadb:
            return
        try:
            report_text = (
                f"Query: {report.query}\n"
                f"Summary: {report.summary}\n"
                f"Domains: {', '.join(report.domains_queried)}"
            )
            self._chromadb.store_memory(
                "alchemy_memory",
                report.id,
                report_text,
                {
                    "type": "alchemy_report",
                    "query": report.query,
                    "connection_count": len(report.connections),
                    "novelty_score": report.novelty_score,
                    "timestamp": report.timestamp.isoformat(),
                },
            )
            self._chromadb.store_memory(
                "alchemy_cache",
                report.id,
                report.query,
                {"report_id": report.id, "timestamp": report.timestamp.isoformat()},
            )
            for conn in report.connections:
                self._chromadb.store_memory(
                    "alchemy_memory",
                    f"{report.id}_{uuid.uuid4().hex[:8]}",
                    (
                        f"{conn.source_domain}: {conn.source_entity[:100]} | "
                        f"{conn.target_domain}: {conn.target_entity[:100]} | "
                        f"{conn.explanation[:200]}"
                    ),
                    {
                        "type": "alchemy_connection",
                        "source_domain": conn.source_domain,
                        "target_domain": conn.target_domain,
                        "correlation_type": conn.correlation_type,
                        "strength": conn.strength,
                        "query": report.query,
                        "report_id": report.id,
                    },
                )
        except Exception as e:
            logger.warning("Failed to store alchemy report: %s", e)

    async def _generate_summary(self, query: str, connections: list[AlchemyConnection]) -> str | None:
        if not connections:
            return None
        if not self._hermes or not self._hermes.available:
            return None
        conn_lines = "\n".join(
            f"- {c.source_domain} ↔ {c.target_domain}: {c.explanation[:150]}"
            for c in connections[:5]
        )
        prompt = (
            f"Query: {query}\n"
            f"Cross-domain connections found:\n{conn_lines}\n\n"
            f"Write a 2-3 sentence executive summary of what these connections mean "
            f"for a prediction market trader. Focus on the most actionable signal."
        )
        try:
            result = await self._hermes.process_message(prompt, {"user_id": "alchemy_summary"})
            return result.get("response", "")
        except Exception as e:
            logger.debug("Summary generation failed: %s", e)
            return None

    def get_history(self) -> list[AlchemyReport]:
        return list(self._reports.values())

    def get_report(self, report_id: str) -> AlchemyReport | None:
        return self._reports.get(report_id)
