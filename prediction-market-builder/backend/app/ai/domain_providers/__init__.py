from app.ai.domain_providers.base import DomainProvider, DomainData, DomainItem
from app.ai.domain_providers.market_provider import MarketDomainProvider
from app.ai.domain_providers.news_provider import NewsDomainProvider
from app.ai.domain_providers.memory_provider import MemoryDomainProvider
from app.ai.domain_providers.onchain_provider import OnChainDomainProvider
from app.ai.domain_providers.macros_provider import MacrosDomainProvider
from app.ai.domain_providers.social_provider import SocialDomainProvider
from app.ai.domain_providers.legal_provider import LegalDomainProvider


class DomainRegistry:
    def __init__(self):
        self._providers: dict[str, DomainProvider] = {}

    def register(self, provider: DomainProvider) -> None:
        self._providers[provider.name] = provider

    def select(self, query: str) -> list[DomainProvider]:
        active = [p for name, p in self._providers.items()
                  if name not in ("onchain", "macros", "social", "legal")]
        query_lower = query.lower()
        priority_names = []
        if any(kw in query_lower for kw in ["market", "odds", "predict", "polymarket", "kalshi"]):
            priority_names.append("markets")
        if any(kw in query_lower for kw in ["news", "headline", "announce", "report"]):
            priority_names.append("news")
        if any(kw in query_lower for kw in ["memory", "past", "history", "previous"]):
            priority_names.append("memory")
        priority = [p for p in active if p.name in priority_names]
        others = [p for p in active if p.name not in priority_names]
        return priority + others

    def get_provider(self, name: str) -> DomainProvider | None:
        return self._providers.get(name)


__all__ = [
    "DomainProvider", "DomainData", "DomainItem",
    "DomainRegistry",
    "MarketDomainProvider", "NewsDomainProvider", "MemoryDomainProvider",
    "OnChainDomainProvider", "MacrosDomainProvider",
    "SocialDomainProvider", "LegalDomainProvider",
]
