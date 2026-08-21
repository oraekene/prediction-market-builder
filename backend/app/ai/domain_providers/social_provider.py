from app.ai.domain_providers.base import DomainProvider, DomainData


class SocialDomainProvider(DomainProvider):
    @property
    def name(self) -> str:
        return "social"

    @property
    def description(self) -> str:
        return "Social media sentiment from Twitter/X (Phase 4 — placeholder)"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        return DomainData(domain="social", items=[], error="not_implemented")
