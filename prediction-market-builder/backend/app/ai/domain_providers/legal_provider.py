from app.ai.domain_providers.base import DomainProvider, DomainData


class LegalDomainProvider(DomainProvider):
    @property
    def name(self) -> str:
        return "legal"

    @property
    def description(self) -> str:
        return "Regulatory filings and legal documents (Phase 4 — placeholder)"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        return DomainData(domain="legal", items=[], error="not_implemented")
