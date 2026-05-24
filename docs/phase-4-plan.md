# Phase 4: Production — Granular Implementation Plan

> **Execution order:** 4.3 → 4.2 → 4.1 → 4.4
>
> **Architecture decisions:**
> - Task 4.1: Production-harden existing Python `SimulatedExecutionEngine`. Rust/ethers-rs engine deferred to v2.
> - This plan is read-only reference. Do NOT implement until explicitly instructed.

---

## Task 4.3: Agentic Search Pipeline (Priority 1)

**Goal:** Enable Hermes-Agent to search the web, extract content from pages, and research topics autonomously.

**Current state:** `backend/app/agentic_search/` is empty on disk. SearXNG service defined in `docker-compose.yml` but unconfigured. Scrapling dependency exists in `pyproject.toml`. Camoufox/Playwright not installed.

---

### 4.3.1: SearXNG Configuration & Client

**source**: https://github.com/searxng/searxng

**Files:**
- Modify: `infrastructure/docker-compose.yml` — add SearXNG config volume + env vars
- Create: `infrastructure/searxng/settings.yml` — SearXNG configuration
- Create: `infrastructure/searxng/limiter.toml` — rate limiter config
- Create: `backend/app/agentic_search/searxng_client.py` — async Python client
- Create: `backend/tests/test_searxng_client.py` — unit tests

**Steps:**

- [ ] **Step 1: Add SearXNG config volume to docker-compose.yml**
  - Mount `./infrastructure/searxng/settings.yml` to `/etc/searxng/settings.yml`
  - Mount `./infrastructure/searxng/limiter.toml` to `/etc/searxng/limiter.toml`
  - Set `SEARXNG_BASE_URL: http://localhost:8888`
  - Add `depends_on` condition (not required for basic functionality)
  - Add `restart: unless-stopped`

- [ ] **Step 2: Create SearXNG settings.yml**
  - `search_format: json` — JSON API responses
  - Enable engines: `google`, `duckduckgo`, `bing`, `wikipedia`, `news`, `wikidata`, `stackoverflow`
  - Disable engines: `youtube`, `google images`, `google videos`, `google shopping`
  - Set `autocomplete: ""` — disable autocomplete for privacy
  - Set `infinite_scroll: false`
  - Set `default_locale: en`
  - Cookie privacy: `cookie_max_age: 0` (no persistent cookies)
  - Rate limiting: refer to `limiter.toml`

- [ ] **Step 3: Create SearXNG limiter.toml**
  - `botdetection.ip_limit: 5` — max 5 requests per IP per second
  - `botdetection.ip_limit_short: 10` — burst allowance
  - `botdetection.ip_link_token_limit: 1000` — per link token

- [ ] **Step 4: Write SearXNGClient class** in `searxng_client.py`
  ```python
  class SearXNGClient:
      def __init__(self, base_url: str = "http://localhost:8888", timeout: int = 15):
          # Initialize httpx.AsyncClient with base URL, timeout, limits

      async def search(self, query: str, category: str = "general",
                       pageno: int = 1, language: str = "en") -> list[dict]:
          # GET /search with params q=query, format=json, category, pageno, language
          # Parse JSON response
          # Normalize to: {url, title, snippet, engine, score, category, positions}
          # Handle errors: connection refused, timeout, empty results, non-JSON response
          # Return sorted by score descending

      async def search_multi(self, queries: list[str], category: str = "general") -> list[dict]:
          # Run multiple searches concurrently with asyncio.gather
          # Merge results, deduplicate by URL, re-sort by score

      async def count_results(self, query: str, category: str = "general") -> int:
          # Return number_of_results from search response without loading full results
  ```
  - Fields: `_client` (httpx.AsyncClient, lazy init), `base_url`, `_available` (bool, set after first successful call)
  - Config: timeout, max_retries (3), retry_delay (1s exponential)

- [ ] **Step 5: Write tests** in `test_searxng_client.py`
  - Mock httpx responses to test:
    - Successful search returns normalized results
    - Empty results returns empty list
    - Connection error raises `SearXNGUnavailableError`
    - Timeout raises `SearXNGTimeoutError`
    - Invalid JSON response raises `SearXNGParseError`
    - `search_multi` deduplicates URLs correctly
    - `count_results` returns integer

---

### 4.3.2: Scrapling Fast Parse Gatekeeper

**source**: https://github.com/D4Vinci/Scrapling

**Files:**
- Create: `backend/app/agentic_search/scrapling_parser.py` — content extraction
- Create: `backend/tests/test_scrapling_parser.py` — tests
- Create: `backend/tests/fixtures/article.html` — sample HTML fixture
- Create: `backend/tests/fixtures/forum.html` — sample HTML fixture
- Create: `backend/tests/fixtures/listing.html` — sample HTML fixture

**Steps:**

- [ ] **Step 1: Write ScraplingParser class** in `scrapling_parser.py`
  ```python
  class ScraplingParser:
      def __init__(self, max_content_length: int = 100_000, fallback_to_lxml: bool = True):
          # store config

      async def parse_url(self, url: str) -> dict | None:
          # Fetch URL via httpx
          # Call parse_html with content + url
          # Return ParsedContent or None on failure

      async def parse_html(self, html: str, url: str) -> dict:
          # Use Scrapling AdaptiveParser to parse HTML
          # If unavailable and fallback_to_lxml, use lxml + readability-lxml
          # Extract:
          #   - title: <title> or <h1> or og:title
          #   - content: main article text via Scrapling's smart extraction
          #   - snippet: first 200 chars of content
          #   - author: meta[author], JSON-LD, or byline class
          #   - date: meta[date], time tags, JSON-LD, or published_time
          #   - links: all <a href> with rel="nofollow" filtering
          #   - language: <html lang> or detected from content
          # Strip: <script>, <style>, <nav>, <footer>, <header>, <noscript>
          # Truncate: max_content_length

      async def extract_article(self, url: str) -> dict | None:
          # Higher-level: parse + extract structured article data
          # Return {headline, author, date, body_text, word_count, estimated_read_time}

      async def available(self) -> bool:
          # Check if Scrapling is importable
  ```
  - Error handling: 404 returns `None`, 403 logs and returns partial, connection errors retry once

- [ ] **Step 2: Create test fixtures** — 3 sample HTML files
  - `article.html`: news article with `<article>`, `<time>`, author `<meta>`, structured content
  - `forum.html`: Reddit-style thread with posts, voting, nested comments
  - `listing.html`: Product listing with multiple items, cards, pagination

- [ ] **Step 3: Write tests** in `test_scrapling_parser.py`
  - Parse fixture HTML and verify extracted fields
  - Test with empty HTML returns None
  - Test with minimal HTML returns partial content
  - Test `extract_article` returns structured data
  - Test `available()` returns bool

---

### 4.3.3: Camoufox + Playwright

**source**: https://github.com/daijro/camoufox

**Files:**
- Create: `backend/app/agentic_search/camoufox_playwright.py` — browser automation
- Create: `backend/tests/test_camoufox_playwright.py` — tests

**Steps:**

- [ ] **Step 1: Install dependencies**
  - Add `playwright>=1.48.0` and `camoufox>=0.2.0` to `pyproject.toml`
  - Add note to README: `playwright install chromium` required

- [ ] **Step 2: Write CamoufoxCrawler class** in `camoufox_playwright.py`
  ```python
  class CamoufoxCrawler:
      def __init__(self, headless: bool = True, viewport: dict = None,
                   timeout: int = 30000, max_scrolls: int = 0):
          # Store config, _browser = None (lazy init)
          # Default viewport: {"width": 1280, "height": 720}

      async def ensure_browser(self):
          # Lazy-launch Playwright with Camoufox stealth
          # Camoufox config: humanize_mouse=True, screen={"width": 1280, "height": 720}
          # Block resources: images, fonts, media for speed
          # Set realistic user-agent, locale, timezone

      async def extract_page(self, url: str) -> dict:
          # await ensure_browser()
          # Create new context + page
          # page.goto(url, wait_until="networkidle", timeout=timeout)
          # Extract via Accessibility Tree (page.accessibility.snapshot)
          #   - label, role, value, description, children
          # Fallback: page.content() -> ScraplingParser.parse_html()
          # Extract: title (page.title()), url (page.url), status code
          # Optional: page.screenshot() as base64 (for debugging)
          # Return: {url, title, content, accessibility_tree, status_code, took_ms}
          # Cleanup: close page

      async def extract_page_safe(self, url: str) -> dict:
          # Wrapper with timeout and error handling
          # Catches: TimeoutError, BrowserError, ConnectionError
          # Returns error dict with partial content on failure

      async def search_and_extract(self, url: str) -> dict:
          # Specifically for search result pages
          # Extract structured results, not raw HTML
          # Handle JS-rendered search pages

      async def close(self):
          # Clean shutdown of browser

      async def available(self) -> bool:
          # Check if playwright + camoufox importable
  ```
  - Edge cases: CAPTCHA (detect and return partial), SPA (wait for specific selector), auth (return 403), redirect chains (follow to configurable max), PDFs (return metadata only), binary files (return error)
  - Resource limits: max 2 concurrent browser contexts, memory threshold check before launch

- [ ] **Step 3: Write tests** in `test_camoufox_playwright.py`
  - Test `available()` returns bool
  - Test `extract_page` with mock page (use monkeypatch/pytest-playwright)
  - Test `extract_page_safe` with unreachable URL returns error dict
  - Test browser reuse across calls
  - Test `close` cleans up resources

---

### 4.3.4: Search Orchestrator

**Files:**
- Create: `backend/app/agentic_search/__init__.py` — package init, exports
- Create: `backend/app/agentic_search/schemas.py` — Pydantic schemas
- Create: `backend/app/agentic_search/search_orchestrator.py` — orchestration
- Create: `backend/tests/test_search_orchestrator.py` — tests

**Steps:**

- [ ] **Step 1: Create Pydantic schemas** in `schemas.py`
  ```python
  from enum import Enum
  from pydantic import BaseModel, HttpUrl
  from datetime import datetime
  from typing import Literal

  class SearchDepth(str, Enum):
      QUICK = "quick"      # SearXNG only, snippets no extraction
      STANDARD = "standard" # SearXNG + Scrapling top results
      DEEP = "deep"         # SearXNG + Scrapling + Camoufox + follow-ups

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
  ```

- [ ] **Step 2: Write SearchOrchestrator class** in `search_orchestrator.py`
  ```python
  class SearchOrchestrator:
      def __init__(self, searxng_client: SearXNGClient = None,
                   scrapling_parser: ScraplingParser = None,
                   camoufox_crawler: CamoufoxCrawler = None,
                   cache_ttl: int = 300, cache_max_size: int = 500):
          # Initialize components (lazy: create on first use)
          # LRU cache: (query, depth, categories) -> SearchResponse

      async def search(self, request: SearchRequest) -> SearchResponse:
          # Check cache (keyed on query+depth+category hash)
          # Route to appropriate strategy:
          #   QUICK:    SearXNG only
          #   STANDARD: SearXNG -> Scrapling parse each result
          #   DEEP:     SearXNG -> Scrapling -> Camoufox for JS failures -> re-query
          # Track: start_time, engines_used
          # Store in cache before returning

      async def _search_quick(self, request: SearchRequest) -> tuple[list, list]:
          # SearXNG.search() with category
          # Return (results, engines_used)

      async def _search_standard(self, request: SearchRequest) -> tuple[list, list]:
          # SearXNG -> take top min(max_results * 2, available)
          # Scrapling parse each concurrently via asyncio.gather
          # Attach content to results
          # Return enriched results

      async def _search_deep(self, request: SearchRequest) -> tuple[list, list]:
          # SearXNG for original + generate 2 follow-up queries
          # All SearXNG calls concurrent
          # Scrapling parse all results
          # Camoufox fallback for failed parses
          # Deduplicate across queries
          # Return aggregated

      async def self_check(self) -> dict:
          # Verify each component is available
          # Return {searxng: bool, scrapling: bool, camoufox: bool}
  ```
  - Rate limiting: per-engine counter, max 30req/min SearXNG, 10req/min Camoufox
  - Fallback chain: SearXNG down -> log + raise; Scrapling fail -> content=None; Camoufox fail -> content="[unavailable]"
  - Cache invalidation: TTL-based, LRU eviction, manual clear endpoint

- [ ] **Step 3: Write __init__.py exports**
  ```python
  from .searxng_client import SearXNGClient, SearXNGUnavailableError
  from .scrapling_parser import ScraplingParser
  from .camoufox_playwright import CamoufoxCrawler
  from .search_orchestrator import SearchOrchestrator
  from .schemas import SearchRequest, SearchResponse, SearchResultItem, SearchDepth, SearchCategory
  ```

- [ ] **Step 4: Write tests** in `test_search_orchestrator.py`
  - Mock all 3 components, test orchestration logic
  - Test QUICK depth only calls SearXNG
  - Test STANDARD calls SearXNG + Scrapling
  - Test DEEP calls all three + generates follow-ups
  - Test empty results handling
  - Test cache hit returns old result
  - Test cache miss calls components
  - Test self_check returns status dict
  - Test component failure doesn't crash orchestrator

---

### 4.3.5: Hermes-Agent Integration

**Files:**
- Modify: `backend/app/main.py` — register search tools in ToolRegistry
- Create: `backend/app/agentic_search/search_router.py` — optional FastAPI router
- Modify: `backend/tests/test_integration.py` — search tool integration test

**Steps:**

- [ ] **Step 1: Register 3 search tools in main.py** (in lifespan or startup)
  ```python
  def _register_search_tools(tr: ToolRegistry, search: SearchOrchestrator):
      tr.register(
          name="web_search",
          toolset="search",
          schema={
              "description": "Search the web for current information. Returns ranked results with URLs, titles, and snippets.",
              "parameters": {
                  "type": "object",
                  "properties": {
                      "query": {"type": "string", "description": "Search query"},
                      "max_results": {"type": "integer", "default": 5},
                      "category": {"type": "string", "enum": ["general", "news", "science"]},
                  },
                  "required": ["query"],
              },
          },
          handler=lambda query, max_results=5, category="general": asyncio.run(search.search(
              SearchRequest(query=query, max_results=max_results, depth=SearchDepth.QUICK, categories=[SearchCategory(category)])
          )),
          check_fn=lambda: True,
      )
      # web_extract tool: takes URL, returns extracted content via Scrapling
      # web_research tool: takes topic, depth, runs multi-query deep research
  ```
  - `web_search`: QUICK depth, extracts snippets only, fast response (<3s target)
  - `web_extract`: takes URL, uses ScraplingParser.parse_url, returns full content
  - `web_research`: DEEP depth, multi-query, returns synthesized results (takes longer, 10-30s)

- [ ] **Step 2: Create search_router.py** for direct API access
  ```python
  router = APIRouter(prefix="/api/search", tags=["search"])

  @router.post("/search", response_model=SearchResponse)
  async def api_search(request: SearchRequest):
      return await orchestrator.search(request)

  @router.get("/health")
  async def search_health():
      return await orchestrator.self_check()
  ```

- [ ] **Step 3: Integration test**
  - Test that HermesOrchestrator can call `web_search` tool
  - Test that `web_research` tool returns multi-query results
  - Test error propagation from components

---

## Task 4.2: Production Hardening (Priority 2)

**Goal:** Security audit, performance optimization, scaling prep, monitoring.

---

### 4.2.1: Security Audit

**Files:**
- Create: `backend/app/services/encryption.py` — Fernet key encryption
- Create: `backend/app/middleware/rate_limit.py` — rate limiter
- Modify: `backend/app/config.py` — add rate limit + encryption settings
- Modify: `backend/app/main.py` — add middleware
- Modify: `backend/app/routers/auth.py` — JWT hardening + refresh tokens
- Create: `backend/tests/test_encryption.py` — encryption tests
- Create: `backend/tests/test_rate_limit.py` — rate limit tests

**Steps:**

- [ ] **Step 1: Write encryption service** in `encryption.py`
  ```python
  from cryptography.fernet import Fernet, MultiFernet

  class EncryptionService:
      def __init__(self, master_key: str | None = None):
          # Initialize from settings.encryption_key
          # Support key rotation: MultiFernet([current, *previous])

      def encrypt_api_key(self, plaintext: str) -> str:
          # Fernet.encrypt(plaintext.encode()).decode()

      def decrypt_api_key(self, ciphertext: str) -> str:
          # Fernet.decrypt(ciphertext.encode()).decode()

      def rotate_key(self, new_key: str):
          # Add new key, re-encrypt all existing values
  ```
  - Add `encryption_key` to `Settings` class in `config.py`
  - Warn on startup if `encryption_key` is empty or default
  - Add `get_encryption_service()` singleton

- [ ] **Step 2: Migrate existing API keys**
  - In User model read path: if key not encrypted (check by prefix), encrypt on read
  - Future: store all new keys encrypted by default
  - Migration script for existing plaintext keys

- [ ] **Step 3: JWT hardening** in `auth.py`
  - Add refresh token flow:
    - `POST /api/auth/refresh` — takes refresh token, returns new access + refresh pair
    - Store refresh token hash in DB (revocable)
    - Access token: 15 min expiry
    - Refresh token: 7 day expiry, one-time use (rotation)
  - Add JWT ID (`jti`) claim
  - Add `logout_all_sessions(user_id)` endpoint — deletes all refresh tokens for user
  - Rate limit auth: 10 req/min per IP on register/login, 30 req/min on refresh
  - Add `check_current_user_idle` endpoint that returns token remaining TTL

- [ ] **Step 4: Write rate limiter middleware** in `middleware/rate_limit.py`
  ```python
  class RateLimitConfig:
      tiers: dict[str, int] = {
          "auth": 10,       # requests per minute
          "search": 30,
          "trade": 5,
          "general": 100,
          "global_per_user": 500,
      }

  class RateLimiter:
      def __init__(self, config: RateLimitConfig):
          # Sliding window counter in memory
          # _windows: dict[key, list[timestamp]]

      async def check(self, key: str, tier: str, cost: int = 1) -> bool:
          # Remove timestamps older than 60s
          # Count remaining in window
          # Return True if under limit, False if exceeded

      def remaining(self, key: str, tier: str) -> int:
          # Return remaining requests in current window
  ```
  - Add rate limit middleware to `main.py`:
    - Determine tier from request path pattern
    - Check per-IP for auth, per-user for other endpoints
    - Add response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    - Return 429 with `Retry-After` when exceeded
  - Add `RateLimitExceeded` exception handler

- [ ] **Step 5: Dependency security scan**
  - Run `pip-audit` on `pyproject.toml` dependencies
  - Pin all dependencies to exact versions
  - Fix any reported CVEs
  - Document audit results

- [ ] **Step 6: General security hardening**
  - CORS: restrict to known origins (not wildcard)
  - Add security headers middleware (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
  - Input validation: ensure all endpoints validate input with Pydantic
  - Remove debug endpoints in production
  - Add request ID to all requests (for tracing)

---

### 4.2.2: Performance Optimization

**Files:**
- Modify: `backend/app/data/duckdb_manager.py` — query indexing + materialization
- Modify: `backend/app/data/lancedb_manager.py` — index tuning
- Create: `backend/app/services/response_cache.py` — API caching

**Steps:**

- [ ] **Step 1: DuckDB optimization**
  - Profile top 5 queries with `.explain()` to identify full table scans
  - Add indexes on: `market_analytics.category`, `market_analytics.platform`, `market_analytics.status`, `market_analytics.volume`
  - Materialize hot aggregations:
    ```sql
    CREATE MATERIALIZED VIEW IF NOT EXISTS category_summary AS
    SELECT category, COUNT(*) as count, AVG(current_odds) as avg_odds, SUM(volume) as total_volume
    FROM market_analytics GROUP BY category;
    ```
  - Configure: `SET memory_limit = '2GB'`, `SET threads = 4`

- [ ] **Step 2: LanceDB optimization**
  - Benchmark current ANN search latency (target: <50ms for top-20)
  - Add IVF index with `num_partitions = sqrt(num_rows)`
  - Tune `nprobes`: start at 10, benchmark, increase until diminishing returns
  - Consider Product Quantization (PQ) for memory reduction if dataset >100K vectors

- [ ] **Step 3: API caching**
  ```python
  class ResponseCache:
      def __init__(self, maxsize: int = 500, ttl: int = 30):
          # TTLCache from cachetools

      async def get(self, key: str) -> Any | None:
      async def set(self, key: str, value: Any):
      async def invalidate(self, pattern: str):
  ```
  - Cache: `/api/markets` (TTL 30s), `/api/risk/summary` (TTL 60s), `/api/strategies` (TTL 10s)
  - Invalidate on POST/PUT/DELETE to same resource
  - Add `Cache-Control` response headers

---

### 4.2.3: Horizontal Scaling

**Files:**
- Modify: `infrastructure/docker-compose.yml` — add PgBouncer, Redis
- Create: `infrastructure/pgbouncer/pgbouncer.ini` — PgBouncer config
- Create: `infrastructure/pgbouncer/userlist.txt` — PgBouncer auth

**Steps:**

- [ ] **Step 1: Add PgBouncer**
  - Add to docker-compose:
    ```yaml
    pgbouncer:
      image: edoburu/pgbouncer:latest
      environment:
        DB_USER: pmuser
        DB_PASSWORD: pmpass
        DB_HOST: postgres
        DB_PORT: 5432
        DB_NAME: pmbuilder
        POOL_MODE: transaction
        DEFAULT_POOL_SIZE: 25
        MAX_CLIENT_CONN: 100
    ```
  - Update backend `DATABASE_URL` to point at `pgbouncer:6432` instead of `postgres:5432`

- [ ] **Step 2: Add Redis**
  - Add to docker-compose:
    ```yaml
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
      volumes: ["redis-data:/data"]
    ```
  - Add `REDIS_URL` to settings
  - Migrate in-memory rate limiter + response cache to Redis
  - Migrate WebSocket session tracking to Redis (for multi-backend WebSocket support)

- [ ] **Step 3: Verify statelessness**
  - Audit backend for in-memory per-process state
  - Move any such state to Redis/DB
  - Confirm all services can scale to N instances behind a load balancer

---

### 4.2.4: Monitoring & Alerting

**Files:**
- Create: `backend/app/services/metrics.py` — Prometheus metrics
- Modify: `backend/app/main.py` — expose `/metrics` endpoint
- Create: `infrastructure/prometheus/prometheus.yml` — scrape config
- Create: `infrastructure/grafana/dashboards/system.json` — dashboard
- Modify: `infrastructure/docker-compose.yml` — add prometheus + grafana

**Steps:**

- [ ] **Step 1: Instrument metrics** in `metrics.py`
  ```python
  from prometheus_client import Counter, Histogram, Gauge

  http_requests = Counter("http_requests_total", "Total HTTP requests",
                          ["method", "endpoint", "status"])
  http_duration = Histogram("http_request_duration_seconds", "HTTP latency",
                            ["method", "endpoint"],
                            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0])
  searches_total = Counter("searches_total", "Total searches by engine", ["engine", "status"])
  trades_total = Counter("trades_total", "Total trades by platform", ["platform", "status"])
  ws_connections = Gauge("active_websocket_connections", "Active WS connections")
  rate_limit_hits = Counter("rate_limit_hits_total", "Rate limit hits by tier", ["tier"])
  ```
  - Create middleware to auto-instrument `http_requests` and `http_duration`
  - Add search metrics in orchestrator
  - Add trade metrics in execution engine

- [ ] **Step 2: Add `/metrics` endpoint** in `main.py`
  - Create a Prometheus middleware that instruments all requests
  - Expose `/metrics` for Prometheus scraping

- [ ] **Step 3: Add Prometheus + Grafana** to docker-compose
  ```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes: ["./infrastructure/prometheus:/etc/prometheus"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
  ```
  - Create `prometheus.yml` with backend scrape target

- [ ] **Step 4: Create Grafana dashboard** JSON
  - Panels: request rate, P50/P95/P99 latency, error rate, search volume, trade volume, WebSocket connections, Python memory/GC
  - Add alert rules for: error rate > 5% over 5min, P95 > 2s, rate limit hits > 100/min

---

## Task 4.1: Production Execution Engine (Priority 3)

**Design decision:** Harden existing Python `SimulatedExecutionEngine` into a real exchange execution service. Rust engine deferred to v2.

**Current state:** `backend/app/services/execution.py` has `SimulatedExecutionEngine` and `SimulatedOrderBook` classes that generate fake order books and simulate fills probabilistically. Docker-compose has no execution-specific services.

---

### 4.1.1: Polymarket Real Execution Connector

**Files:**
- Refactor: `backend/app/services/execution.py` — replace simulated with real
- Create: `backend/app/services/exchange_base.py` — abstract exchange connector
- Create: `backend/app/services/polymarket_connector.py` — Polymarket CLOB v4
- Create: `backend/tests/test_polymarket_connector.py` — integration tests

**Steps:**

- [ ] **Step 1: Create ExchangeBase abstract class** in `exchange_base.py`
  ```python
  from abc import ABC, abstractmethod
  from typing import Any

  class ExchangeOrder:
      platform: str
      market_id: str
      side: Literal["buy", "sell"]
      order_type: Literal["limit", "market"]
      price: float
      amount: float

  class ExchangeConnector(ABC):
      @abstractmethod
      async def get_order_book(self, market_id: str) -> dict: ...

      @abstractmethod
      async def place_order(self, order: ExchangeOrder, credentials: dict) -> dict: ...

      @abstractmethod
      async def cancel_order(self, order_id: str) -> bool: ...

      @abstractmethod
      async def get_order_status(self, order_id: str) -> dict: ...

      @abstractmethod
      async def get_balance(self, credentials: dict) -> dict: ...

      @abstractmethod
      async def available(self) -> bool: ...
  ```

- [ ] **Step 2: Write PolymarketConnector** in `polymarket_connector.py`
  - Inherits from `ExchangeConnector`
  - CLOB API v4 integration:
    - `GET /books` — order book
    - `POST /order` — signed order submission (EIP-712 typed data)
    - `DELETE /order` — cancel
    - `GET /order` — status
    - `GET /balance` — USDC balance
  - Signing: use `eth_account` library for ECDSA signing of EIP-712 typed data
  - Key management: read decrypted key from `EncryptionService`
  - Rate limit: respect CLOB API rate limits (retry-after header)
  - Error handling: nonce errors (re-sign with new nonce), insufficient balance, market not found
  - WebSocket: connect to CLOB websocket for real-time order events (filled, cancelled, failed)

- [ ] **Step 3: Write tests** for Polymarket connector
  - Test order book fetching with mock httpx
  - Test order submission with mock signing
  - Test error handling for each error type
  - Test balance fetching

---

### 4.1.2: Kalshi + Drift Connectors

**Files:**
- Create: `backend/app/services/kalshi_connector.py`
- Create: `backend/app/services/drift_connector.py`
- Create: `backend/tests/test_kalshi_connector.py`
- Create: `backend/tests/test_drift_connector.py`

**Steps:**

- [ ] **Step 1: Write KalshiConnector**
  - REST API v2: `/trade-api/v2/portfolio/order`, `/market/{ticker}`, etc.
  - Auth: RSA key pair signing (Kalshi uses RSA-SHA256 for API auth)
  - Order types: limit, market, stop-loss
  - REST-only (Kalshi WebSocket not needed for execution)

- [ ] **Step 2: Write DriftConnector**
  - Drift protocol API endpoints
  - Auth: API key in headers
  - Order types: limit, market

---

### 4.1.3: Real Execution Engine

**Files:**
- Refactor: `backend/app/services/execution.py` — real order execution
- Create: `backend/app/services/execution_config.py` — per-exchange settings
- Create: `backend/tests/test_execution_real.py` — unit tests

**Steps:**

- [ ] **Step 1: Refactor ExecutionEngine**
  ```python
  class ExecutionEngine:
      def __init__(self, encryption: EncryptionService):
          self.connectors = {
              "polymarket": PolymarketConnector(),
              "kalshi": KalshiConnector(),
              "drift": DriftConnector(),
          }

      async def place_order(self, platform: str, market_id: str, side: str,
                           amount: float, price: float, user_id: str) -> dict:
          # Get user's decrypted API key from EncryptionService
          # Create ExchangeOrder
          # Route to appropriate connector
          # Submit order
          # Track in DB (order_id, platform_order_id, status, timestamp)
          # Return execution result

      async def get_order_book(self, platform: str, market_id: str) -> dict:
          # Real order book from exchange API
          # Return {bids: [{price, size}], asks: [{price, size}], spread, mid_price}

      async def calculate_slippage(self, platform: str, market_id: str,
                                    amount: float, side: str) -> dict:
          # Get real order book
          # Simulate walking the book for given amount
          # Return {estimated_slippage, price_impact, filled_price}

      async def monitor_order(self, order_id: str) -> dict:
          # Poll exchange for order status (every 2s, up to 60s)
          # Update DB on status change
          # Return final status: filled/partial/cancelled/failed
  ```
  - Keep `SimulatedExecutionEngine` as a fallback for paper trading
  - Add `mode: Literal["paper", "live"]` to switch between engines

- [ ] **Step 2: Real slippage calculator**
  - Walk the order book: for a buy order, consume asks from best to worst until amount filled
  - Impact cost = (execution_price - mid_price) / mid_price
  - Return: estimated_slippage, price_impact, fill_curve (list of {price, cumulative_amount} pairs)

- [ ] **Step 3: Transaction monitoring**
  - After order submission, poll status every 2s
  - Max wait: 120s for CLOB orders, 300s for on-chain
  - On timeout: mark as "pending_review" (don't assume failed — exchange might have accepted)
  - WebSocket event listener for push-based status updates (faster than polling)

---

### 4.1.4: Integration with Paper Trading

**Files:**
- Modify: `backend/app/services/paper_trading.py` — add live execution path
- Modify: `backend/app/routers/paper_trading.py` — add real trade toggle

**Steps:**

- [ ] **Step 1: Paper trading mode toggle**
  - Add per-user `trading_mode` preference: "paper" | "live"
  - Paper mode uses `SimulatedExecutionEngine`
  - Live mode uses `ExecutionEngine` with real exchange connectors
  - Always allow paper mode regardless of real keys

- [ ] **Step 2: Safety guards**
  - Require explicit confirmation before first live trade
  - Max loss limit per-session (configurable, default $100)
  - Kill switch: endpoint to cancel all open orders across all platforms
  - Require successful connection test before allowing live trading

---

### 4.1.5: Rust Engine v2 Plan (Deferred)

**Record this for future:**
- Architecture: standalone microservice with `axum` HTTP server
- `ethers-rs` for EIP-712 signing
- `reqwest` for API calls
- `tokio-tungstenite` for WebSocket streams
- Python calls via `localhost:9000` HTTP
- Key design: one process, multi-tenant signing, shared connection pool
- Docker multi-stage build (compile → 5MB runtime image)
- Estimated effort: 3-4 weeks for production-ready engine

---

## Task 4.4: Launch Preparation (Priority 4)

**Goal:** Documentation, deployment scripts, load testing.

---

### 4.4.1: Documentation

**Files:**
- Create: `docs/user-guide.md` — user-facing documentation
- Create: `docs/api-reference.md` — API reference
- Create: `docs/strategy-templates.md` — strategy template docs

**Steps:**

- [ ] **Step 1: User guide** — covers:
  - Architecture overview (5-layer system)
  - Quick start: authentication, market browsing, first strategy
  - Chat mode: natural language strategy creation
  - Node mode: visual strategy builder walkthrough
  - Strategy types: threshold, momentum, sentiment, arbitrage, multi-condition
  - Risk management: position sizing, VaR, drawdown limits
  - Paper trading: virtual wallet, backtesting, performance tracking
  - Real trading: API key setup, safety limits, execution monitoring
  - Analytics dashboard: portfolio view, risk metrics, performance charts

- [ ] **Step 2: API reference**
  - Auto-generate OpenAPI spec from FastAPI routes
  - Hand-write key endpoint documentation: auth flow, market search, strategy CRUD, risk endpoints, WebSocket chat protocol

- [ ] **Step 3: Strategy template docs**
  - Document each node type with examples
  - Template patterns: momentum following, mean reversion, volatility breakout, cross-market arbitrage, news sentiment, hedging
  - Include sample node graphs (JSON)

---

### 4.4.2: Onboarding Flow Polish

**Note:** Needs a UX audit of current flow. Plan outline:

- [ ] **Step 1: Audit current onboarding**
  - Walk through: login → first view → create strategy → paper trade → real trade
  - Identify friction points (cognitive load, unclear CTAs, empty states)
  - Time each step

- [ ] **Step 2: Implement improvements based on audit**
  - Empty state illustrations + call-to-action
  - Guided tour for first-time users
  - Sample strategies pre-loaded in paper mode
  - Progressive disclosure: don't show advanced options until user needs them

---

### 4.4.3: Load Testing

**Files:**
- Create: `infrastructure/load-tests/k6-scripts/smoke.js` — smoke test
- Create: `infrastructure/load-tests/k6-scripts/load.js` — load test
- Create: `infrastructure/load-tests/k6-scripts/stress.js` — stress test
- Create: `infrastructure/load-tests/README.md` — how to run

**Steps:**

- [ ] **Step 1: Write k6 smoke test**
  - 1 virtual user, iterate through all endpoints
  - Verify baseline latency and correctness

- [ ] **Step 2: Write k6 load test**
  - 10 VUs, 5 min duration
  - Mix: 60% market listing, 20% strategy evaluation, 10% WebSocket chat, 10% risk metrics
  - Target: P95 < 1s, error rate < 1%

- [ ] **Step 3: Write k6 stress test**
  - Ramp from 1 to 200 VUs over 10 min
  - Find breaking point (where error rate > 5% or latency > 5s)
  - Document capacity limits

- [ ] **Step 4: Run and fix**
  - Run each test, record results
  - Fix identified bottlenecks (add indexes, optimize queries, increase resources)
  - Re-test until targets met

---

### 4.4.4: Deployment Scripts

**Files:**
- Create: `infrastructure/scripts/deploy.sh` — deployment script
- Create: `infrastructure/scripts/migrate.sh` — migration script
- Create: `infrastructure/scripts/rollback.sh` — rollback
- Create: `infrastructure/scripts/backup.sh` — backup
- Create: `infrastructure/scripts/seed_data.py` — seed data
- Create: `infrastructure/nginx.conf` — reverse proxy
- Create: `infrastructure/cloudflare.toml` — Cloudflare config

**Steps:**

- [ ] **Step 1: deploy.sh**
  - Pull latest from git
  - Build frontend: `npm run build`
  - Build backend: `docker compose build backend`
  - Run DB migrations: `alembic upgrade head`
  - Restart services with zero-downtime: `docker compose up -d --no-deps --scale backend=2 backend`
  - Health check before declaring success
  - Rollback on failure

- [ ] **Step 2: nginx.conf**
  - Reverse proxy: `/api/` → backend, `/ws` → backend WebSocket, `/*` → frontend
  - SSL termination
  - Rate limiting at proxy level
  - Gzip compression
  - Static file caching
  - Request size limits

- [ ] **Step 3: cloudflare.toml**
  - DNS: A records for app domain
  - SSL/TLS: Full (strict)
  - WAF rules: rate limiting, bot fight mode, SQL injection protection
  - Caching rules for static assets
  - Page Rules: always online, SSL

- [ ] **Step 4: Backup strategy**
  - Daily Postgres dump: `pg_dump`
  - Backup retention: 7 daily, 4 weekly, 3 monthly
  - Encrypt backups before upload to cloud storage
  - Test restore procedure quarterly

- [ ] **Step 5: seed_data.py**
  - Create admin user
  - Create sample strategies
  - Create template risk profiles
  - Only runs on empty DB (no-overwrite guard)

---

*End of Phase 4 Implementation Plan*
