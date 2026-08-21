from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel


class DomainItem(BaseModel):
    text: str
    metadata: dict = {}
    source: str = ""
    timestamp: datetime | None = None


class DomainData(BaseModel):
    domain: str
    items: list[DomainItem] = []
    query_time_ms: int = 0
    error: str | None = None


class DomainProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def query(self, query: str, context: dict | None = None) -> DomainData: ...
