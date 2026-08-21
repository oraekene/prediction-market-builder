from app.ai.domain_providers.base import DomainProvider, DomainData


class MacrosDomainProvider(DomainProvider):
    @property
    def name(self) -> str:
        return "macros"

    @property
    def description(self) -> str:
        return "Macroeconomic indicators: CPI, rates, indices (Phase 4 — placeholder)"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        return DomainData(domain="macros", items=[], error="not_implemented")
