from app.ai.domain_providers.base import DomainProvider, DomainData


class OnChainDomainProvider(DomainProvider):
    @property
    def name(self) -> str:
        return "onchain"

    @property
    def description(self) -> str:
        return "On-chain data: gas, TVL, whale movements (Phase 4 — placeholder)"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        return DomainData(domain="onchain", items=[], error="not_implemented")
