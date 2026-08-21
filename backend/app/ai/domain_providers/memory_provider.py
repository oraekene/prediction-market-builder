import logging
import time

from app.ai.domain_providers.base import DomainProvider, DomainData, DomainItem

logger = logging.getLogger(__name__)


class MemoryDomainProvider(DomainProvider):
    def __init__(self, chromadb=None):
        self._chromadb = chromadb

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Past alchemy patterns and known cross-domain connections from long-term memory"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        start = time.time()
        try:
            if self._chromadb is None:
                from app.data.chromadb_manager import ChromaDBManager
                self._chromadb = ChromaDBManager()
            results = self._chromadb.recall_similar("alchemy_memory", query, n_results=10)
            items = []
            for r in results:
                meta = r.get("metadata", {})
                items.append(DomainItem(
                    text=r.get("text", ""),
                    metadata=meta,
                    source=f"alchemy_memory/{r.get('id', '')}",
                ))
            elapsed = int((time.time() - start) * 1000)
            return DomainData(domain="memory", items=items, query_time_ms=elapsed)
        except Exception as e:
            logger.warning("Memory provider query failed: %s", e)
            elapsed = int((time.time() - start) * 1000)
            return DomainData(domain="memory", items=[], error=str(e), query_time_ms=elapsed)
