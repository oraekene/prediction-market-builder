from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class SearchDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class SearchCategory(str, Enum):
    GENERAL = "general"
    NEWS = "news"
    SCIENCE = "science"
    SOCIAL = "social"


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    depth: SearchDepth = SearchDepth.STANDARD
    categories: list[SearchCategory] = [SearchCategory.GENERAL]
    extract_content: bool = False


class SearchResultItem(BaseModel):
    url: str
    title: str
    snippet: str
    engine: str
    score: float
    category: str
    content: str | None = None
    extracted_at: datetime | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total_found: int
    engines_used: list[str]
    took_ms: int
    cached: bool
