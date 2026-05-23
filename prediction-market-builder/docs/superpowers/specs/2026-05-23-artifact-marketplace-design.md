# Artifact Inventory & Marketplace Schema Design

## 1. Motivation

The system has 15 SQLAlchemy models across 13 files. 7 are directly user-owned, 3 are indirectly user-owned, and 4 serve system-level functions. **None have share/copy/monetization fields.** This document inventories every artifact, maps its ownership model, catalogues integration gaps, and designs the schema additions needed for a future marketplace.

## 2. Complete Artifact Inventory

### 2.1 Directly User-Owned Artifacts (7)

These models have a direct `user_id` column. Every row belongs to exactly one user.

| # | Model | Table | `user_id`? | Rows/user | Marketable? |
|---|-------|-------|------------|-----------|-------------|
| 1 | `Strategy` | `strategies` | Yes | Many | Yes — node graphs can be sold |
| 2 | `MetaStrategy` | `meta_strategies` | Yes | Many | Yes — pool management configs |
| 3 | `ResearchSession` | `research_sessions` | Yes | Many | No — session lifecycle data |
| 4 | `ResearchSessionConfig` | `research_session_configs` | Yes (unique) | One | No — user preferences |
| 5 | `RiskTemplate` | `risk_templates` | Yes | Many | Yes — risk rule templates |
| 6 | `Trade` | `trades` | Yes | Many | No — execution records |
| 7 | `PaperWallet` | `paper_wallets` | Yes | One | No — simulated balance |

**Total directly owned rows created by users:** strategies + meta-strategies + research sessions + risk templates + trades. These represent the bulk of user-generated value.

### 2.2 Indirectly User-Owned Artifacts (3)

These models belong to a user through a foreign-key chain.

| # | Model | Table | Owner via | Marketable? |
|---|-------|-------|-----------|-------------|
| 8 | `ExperimentResult` | `experiment_results` | `session_id` → `ResearchSession.user_id` | No — immutable research log |
| 9 | `HermesTrace` | `hermes_traces` | `session_id` → `ResearchSession.user_id` | No — LLM interaction log |
| 10 | `PaperOrder` | `paper_orders` | `wallet_id` → `PaperWallet.user_id` | No — simulated trade log |

### 2.3 System-Level Artifacts (4)

These models have no user owner. They serve system-wide functions.

| # | Model | Table | Owner | Marketable? |
|---|-------|-------|-------|-------------|
| 11 | `User` | `users` | Self (identity) | No — user accounts |
| 12 | `StrategyTemplate` | `strategy_templates` | None (system) | Yes — extend with creator + pricing |
| 13 | `Market` | `markets` | None (external data) | No — market data ingest |
| 14 | `RLMAlphaVector` | `rlm_alpha_vectors` | None (system) | No — RLM processing results |

### 2.4 In-Memory / Code-Defined Artifacts (non-SQL)

These are not persisted but represent user-generated value.

| # | Artifact | Location | Currently Shareable? |
|---|----------|----------|---------------------|
| 15 | `HypothesisIndividual` | `genetic_programming.py` | No — in-memory only |
| 16 | `MetaStrategyHypothesis` | design doc | No — not yet implemented |
| 17 | Custom skill nodes | HermesOrchestrator registry | No — in registry only |

## 3. Current Schema Gap Analysis

### 3.1 Visibility

**Gap: No row can be made public.** Every artifact is invisible to all users except its owner.

No model has any of:
- `is_public: bool` — toggles public listing
- `shared_with: list[str]` — explicit user-level permissions
- `visibility: enum(PUBLIC, PRIVATE, SHARED)` — composite visibility control

### 3.2 Cloning / Forking

**Gap: No artifact tracks its lineage.** When a user copies another user's strategy, there is no way to record:
- `cloned_from: str | None` — original artifact ID
- `cloned_from_user_id: str | None` — original creator (for attribution)
- `clone_count: int` — how many times this has been cloned

### 3.3 Monetization

**Gap: No artifact has pricing or licensing.** No model has:
- `price: float | None` — purchase price (0 = free)
- `license_type: enum` — MIT, CC-BY-NC, custom, restricted
- `royalty_percentage: float | None` — creator royalty on resale
- `revenue_model: enum` — one_time, subscription, usage_based

## 4. Integration Gap Analysis

### 4.1 Critical Missing Connections

| From | To | Missing | Impact |
|------|----|---------|--------|
| `ExperimentResult` | `Strategy` | No `strategy_id` link when result is KEPT | Hypothesis discovered by research cannot be deployed as a Strategy |
| `HypothesisIndividual` | DB | No persistence layer | GP population lost on restart |
| `CustomNodeTemplate` | `HYPOTHESIS_TEMPLATES` | No auto-discovery | Custom nodes invisible to research |
| `MetaStrategy` | `StrategySpec` | No hypothesis template format | Meta-strategies have no GP-evolvable representation |
| `ResearchSession` | `MetaStrategy` | No link from session to meta-strategy findings | Research results cannot feed pool management |
| `StrategyTemplate` | `User` | No `creator_id` | System templates cannot be user-contributed |

### 4.2 Existing Working Connections

| From | To | Connection | Notes |
|------|----|------------|-------|
| `Strategy` | `Trade` | `strategy_id` | Strategies record trades |
| `Strategy` | `MetaStrategy` | `strategy_ids` (JSON) | Meta-strategies reference child strategies |
| `Strategy` | `ResearchSession` | `strategy_id` | Sessions are scoped to a strategy |
| `ResearchSession` | `ExperimentResult` | `session_id` | Session owns experiment results |
| `PaperWallet` | `PaperOrder` | `wallet_id` | Wallet owns paper orders |

## 5. Marketplace Schema Design

### 5.1 Visibility Mixin (shared across all marketable artifacts)

```python
class VisibilityMixin:
    """Mixin for all marketplace-eligible artifacts."""
    visibility: str = Column(String, default="private")  # private | public | shared
    shared_with_user_ids: list = Column(JSON, default=list)  # Explicit share targets
    published_at: datetime | None = Column(DateTime, nullable=True)
```

### 5.2 Clone/Fork Tracking Mixin

```python
class CloneTrackingMixin:
    """Mixin to track artifact lineage through clones."""
    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    cloned_from_user_id: str | None = Column(String, nullable=True)
    clone_count: int = Column(Integer, default=0)  # How many times this has been cloned
    original_created_at: datetime | None = Column(DateTime, nullable=True)  # When the lineage started
```

### 5.3 Monetization Mixin

```python
class MonetizationMixin:
    """Mixin for sellable artifacts."""
    price: float | None = Column(Float, nullable=True)      # NULL = not for sale, 0 = free
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="standard")  # standard | commercial | academic | custom
    royalty_bps: int | None = Column(Integer, nullable=True) # Basis points (100 = 1%) on resale
    revenue_model: str = Column(String, default="one_time")  # one_time | subscription | usage_based
```

### 5.4 Per-Table Schema Additions

#### 5.4.1 `Strategy` (highest marketability)

```python
class Strategy(Base):
    # ... existing fields ...
    # Visibility
    visibility: str = Column(String, default="private")
    shared_with_user_ids: list = Column(JSON, default=list)
    published_at: datetime | None = Column(DateTime, nullable=True)

    # Clone tracking
    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    cloned_from_user_id: str | None = Column(String, nullable=True)
    clone_count: int = Column(Integer, default=0)

    # Monetization
    price: float | None = Column(Float, nullable=True)
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="standard")
    royalty_bps: int | None = Column(Integer, nullable=True)
    revenue_model: str = Column(String, default="one_time")

    # Marketplace metadata
    market_rating: float = Column(Float, default=0.0)
    market_downloads: int = Column(Integer, default=0)
    featured_until: datetime | None = Column(DateTime, nullable=True)
```

#### 5.4.2 `MetaStrategy` (high marketability)

```python
class MetaStrategy(Base):
    # ... existing fields ...
    visibility: str = Column(String, default="private")
    shared_with_user_ids: list = Column(JSON, default=list)
    published_at: datetime | None = Column(DateTime, nullable=True)

    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    cloned_from_user_id: str | None = Column(String, nullable=True)
    clone_count: int = Column(Integer, default=0)

    price: float | None = Column(Float, nullable=True)
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="standard")
    royalty_bps: int | None = Column(Integer, nullable=True)
    revenue_model: str = Column(String, default="one_time")

    market_rating: float = Column(Float, default=0.0)
    market_downloads: int = Column(Integer, default=0)
```

#### 5.4.3 `RiskTemplate` (medium marketability)

```python
class RiskTemplate(Base):
    # ... existing fields ...
    visibility: str = Column(String, default="private")
    shared_with_user_ids: list = Column(JSON, default=list)
    published_at: datetime | None = Column(DateTime, nullable=True)

    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    cloned_from_user_id: str | None = Column(String, nullable=True)
    clone_count: int = Column(Integer, default=0)

    price: float | None = Column(Float, nullable=True)
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="standard")
    royalty_bps: int | None = Column(Integer, nullable=True)
    revenue_model: str = Column(String, default="one_time")

    market_downloads: int = Column(Integer, default=0)
```

#### 5.4.4 `StrategyTemplate` (system → community-contributed)

Currently system-only with no `user_id`. Needs the most structural change.

```python
class StrategyTemplate(Base):
    # ... existing fields ...
    creator_id: str | None = Column(String, nullable=True, index=True)  # NULL = system-provided
    visibility: str = Column(String, default="system")  # system | public | private
    published_at: datetime | None = Column(DateTime, nullable=True)

    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    clone_count: int = Column(Integer, default=0)
    # StrategyTemplates are the hypothesis patterns. Cloning one means
    # using it as a starting point for your own experiment.

    price: float | None = Column(Float, nullable=True)  # NULL = system template, free
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="cc-by-nc")
    royalty_bps: int | None = Column(Integer, nullable=True)
    revenue_model: str = Column(String, default="one_time")

    market_rating: float = Column(Float, default=0.0)
    market_downloads: int = Column(Integer, default=0)
```

#### 5.4.5 `ResearchSession` (not marketable, but needs visibility)

Research sessions are not sellable but users should be able to share results.

```python
class ResearchSession(Base):
    # ... existing fields ...
    visibility: str = Column(String, default="private")
    shared_with_user_ids: list = Column(JSON, default=list)
    published_at: datetime | None = Column(DateTime, nullable=True)
    # No monetization — sessions are not sellable artifacts
```

#### 5.4.6 `CustomNodeTemplate` (from bridge design)

This table is proposed in the bridge design doc. It represents user-created custom node handlers.

```python
class CustomNodeTemplate(Base):
    __tablename__ = "custom_node_templates"

    id: str = Column(String, primary_key=True, default=uuid4)
    skill_id: str = Column(String, nullable=False, index=True)
    user_id: str = Column(String, nullable=False, index=True)
    node_type: str = Column(String, nullable=False)
    template_description: str = Column(String, nullable=False)
    default_params: dict = Column(JSON, default={})
    param_schema: dict = Column(JSON, default={})
    regime_affinity: list = Column(JSON, default=["all"])
    is_active: bool = Column(Boolean, default=True)

    # Visibility
    visibility: str = Column(String, default="private")
    shared_with_user_ids: list = Column(JSON, default=list)
    published_at: datetime | None = Column(DateTime, nullable=True)

    # Clone tracking
    cloned_from_id: str | None = Column(String, nullable=True, index=True)
    cloned_from_user_id: str | None = Column(String, nullable=True)
    clone_count: int = Column(Integer, default=0)

    # Monetization
    price: float | None = Column(Float, nullable=True)
    currency: str = Column(String, default="USD")
    license_type: str = Column(String, default="standard")
    royalty_bps: int | None = Column(Integer, nullable=True)
    revenue_model: str = Column(String, default="one_time")

    # Marketplace metadata
    market_downloads: int = Column(Integer, default=0)

    created_at: DateTime = Column(DateTime, default=now)
```

### 5.5 Summary of Field Additions by Artifact

| Artifact | Visibility | Clone Track | Monetization | Marketable? |
|----------|-----------|-------------|-------------|-------------|
| `Strategy` | +3 fields | +4 fields | +6 fields | Yes |
| `MetaStrategy` | +3 fields | +4 fields | +6 fields | Yes |
| `RiskTemplate` | +3 fields | +4 fields | +6 fields | Yes |
| `StrategyTemplate` | +3 fields + `creator_id` | +3 fields | +6 fields | Yes |
| `CustomNodeTemplate` | +3 fields | +4 fields | +6 fields | Yes |
| `ResearchSession` | +3 fields | — | — | No (share only) |
| `Trade` | — | — | — | No |
| `PaperWallet` | — | — | — | No |
| `PaperOrder` | — | — | — | No |
| `ExperimentResult` | — | — | — | No |
| `HermesTrace` | — | — | — | No |
| `Market` | — | — | — | No |
| `RLMAlphaVector` | — | — | — | No |
| `User` | — | — | — | No |

## 6. Clone / Fork Behavior

### 6.1 What Cloning Means Per Artifact Type

| Artifact | Clone Semantics | Behavior |
|----------|----------------|----------|
| `Strategy` | Full fork of node graph | Copies `nodes`, `edges`, `risk_profile`. Sets `cloned_from_id`. Resets owner. |
| `MetaStrategy` | Full fork of pool config | Copies `scoring_config`, `promotion_config`, `confluence_config`. Links new strategies. |
| `RiskTemplate` | Full copy of rules | Copies `rules`. Sets `cloned_from_id`. Resets owner. |
| `StrategyTemplate` | Fork as starting point | Copies `config`. New template owned by cloner. Linked to original. |
| `CustomNodeTemplate` | Full copy (node must be registered) | Copies `param_schema`, `default_params`. New owner must re-register node handler. |

### 6.2 Clone API Contract

```python
POST /api/{artifact_type}/{id}/clone
Authorization: Bearer <token>

Response 201:
{
    "id": "new-uuid",
    "cloned_from_id": "original-uuid",
    "cloned_from_user_id": "original-creator-uuid",
    "name": "{original name} (clone)",
    "visibility": "private",        # Clones are always private initially
    "created_at": "..."
}

Error 404: Original not found or not public
Error 403: Original is private, not shared with caller
Error 402: Original has a price > 0 and caller has not purchased
```

### 6.3 Clone Counter Propagation

When a clone is created, the original's `clone_count` increments atomically:

```python
async def clone_artifact(original_id: str, user_id: str, artifact_cls: type) -> dict:
    original = await db.get(artifact_cls, original_id)
    _assert_can_clone(original, user_id)

    clone = artifact_cls(
        cloned_from_id=original.id,
        cloned_from_user_id=original.user_id,
        **{k: _clone_field(k, v) for k, v in original._marketplace_fields()},
    )
    # Override ownership
    clone.user_id = user_id
    clone.visibility = "private"
    clone.published_at = None
    clone.market_downloads = 0

    # Atomic increment
    await db.execute(
        update(artifact_cls)
        .where(artifact_cls.id == original_id)
        .values(clone_count=artifact_cls.clone_count + 1)
    )

    db.add(clone)
    await db.commit()
    return clone.to_dict()
```

### 6.4 Clone Chains vs. Direct Clones

```
Chain model: A → B → C (every clone tracks direct parent)
Direct model: A ← B is_direct, A ← C is_direct, B ← C is_direct

Strategy: Chain model. C knows it came from B, B knows it came from A.
  This preserves attribution across the chain.
  ui_text: "Cloned from @userB, originally by @userA"

To find original root: follow `cloned_from_id` until NULL.
  This requires at most 2 JOINs (chain depth is rarely > 3).
```

## 7. Monetization Models

### 7.1 Pricing Model Per Artifact

| Artifact | Best Model | Rationale |
|----------|-----------|-----------|
| `Strategy` | One-time + resale royalty | Pay once to deploy the strategy. If resold, original creator gets royalty_bps. |
| `MetaStrategy` | One-time | Pool configs are less reusable; one-time pricing is simpler. |
| `RiskTemplate` | Free or one-time | Risk rules are small; most should be free with premium options. |
| `StrategyTemplate` | Free (system) / One-time (community) | System templates are always free. Community templates can be paid. |
| `CustomNodeTemplate` | Usage-based or one-time | Complex nodes (ML models) justify usage-based; simple transforms should be one-time. |

### 7.2 Revenue Models

```python
class RevenueModel(str, enum.Enum):
    ONE_TIME = "one_time"         # Single purchase, permanent access
    SUBSCRIPTION = "subscription" # Recurring (monthly) for access
    USAGE_BASED = "usage_based"   # Pay per evaluation / deployment
    FREE = "free"                 # Free with attribution
```

### 7.3 License Types

```python
class LicenseType(str, enum.Enum):
    STANDARD = "standard"         # Personal use, no redistribution
    COMMERCIAL = "commercial"     # Commercial use allowed
    ACADEMIC = "academic"         # Research/educational use only
    CC_BY_NC = "cc-by-nc"        # Creative Commons Non-Commercial
    CUSTOM = "custom"             # Custom license text
```

### 7.4 Purchase Flow

```
User discovers artifact (public/featured/search)
       │
       ▼
GET /api/{type}/{id}
  → shows: name, description, price, license, preview
  → if price == NULL: "Not for sale"
  → if price == 0: "Free — download now"
  → if price > 0: "Buy for ${price}"
       │
       ▼
POST /api/{type}/{id}/purchase
  → Deducts from user's balance
  → Records in purchase_history table
  → Gives user access to clone/download
       │
       ▼
POST /api/{type}/{id}/clone
  → Creates clone with cloned_from lineage
  → Increments clone_count on original
  → Payload includes license terms
```

### 7.5 Royalty / Resale Model

When user A's strategy is purchased by user B, and user B later resells it:

```
Original Creator (A): receives royalty_bps of B's sale price
Secondary Creator (B): retains (10000 - royalty_bps) / 10000 of sale
Platform: retains a platform fee (configurable, e.g. 5%)
```

## 8. Marketplace Index Tables

For query performance, dedicated marketplace lookup tables:

```sql
CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY,
    artifact_type VARCHAR(32) NOT NULL,     -- "strategy" | "meta_strategy" | "risk_template" | "strategy_template" | "custom_node"
    artifact_id VARCHAR(64) NOT NULL,       -- FK to the specific table
    creator_id VARCHAR(64) NOT NULL,        -- FK to users
    title VARCHAR(256) NOT NULL,
    description TEXT,
    price FLOAT,                             -- NULL = not for sale
    currency VARCHAR(3) DEFAULT 'USD',
    revenue_model VARCHAR(32) DEFAULT 'one_time',
    license_type VARCHAR(32) DEFAULT 'standard',
    royalty_bps INT,
    tags JSON DEFAULT [],
    rating FLOAT DEFAULT 0.0,
    download_count INT DEFAULT 0,
    featured BOOLEAN DEFAULT FALSE,
    featured_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(artifact_type, artifact_id)       -- One listing per artifact
);
```

```sql
CREATE TABLE purchase_history (
    id UUID PRIMARY KEY,
    buyer_id VARCHAR(64) NOT NULL,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
    artifact_type VARCHAR(32) NOT NULL,
    artifact_id VARCHAR(64) NOT NULL,
    price_paid FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    royalty_paid FLOAT DEFAULT 0.0,          -- Royalty to original creator
    platform_fee FLOAT DEFAULT 0.0,          -- Platform fee
    purchase_type VARCHAR(16) DEFAULT 'one_time',  -- one_time | subscription | usage
    purchased_at TIMESTAMP DEFAULT NOW()
);
```

## 9. Migration Strategy

### Phase 1: Schema Only (no marketplace features — 1 session)
1. Add `visibility`, `shared_with_user_ids`, `published_at` to all marketable tables
2. Add `cloned_from_id`, `cloned_from_user_id`, `clone_count` to marketable tables
3. Add `creator_id` to `StrategyTemplate`
4. Add `price`, `currency`, `license_type`, `royalty_bps`, `revenue_model` to marketable tables

### Phase 2: Sharing & Cloning (2 sessions)
1. Implement `POST /api/{type}/{id}/clone` for all marketable types
2. Implement visibility filtering in all list/GET endpoints
3. Implement `GET /api/marketplace/discover` — browse public artifacts
4. Add `market_downloads`, `market_rating` fields

### Phase 3: Monetization (2-3 sessions)
1. Create `marketplace_listings` table
2. Create `purchase_history` table
3. Implement `POST /api/{type}/{id}/purchase`
4. Implement royalty splitting on clone + resell
5. Add `featured` flag + admin endpoint
6. Add marketplace search (by tag, creator, price range)

### Phase 4: Marketplace Frontend (3-4 sessions)
1. Browse/discover page with search + filtering
2. Artifact detail page with preview
3. Purchase flow + wallet integration
4. Creator dashboard (downloads, revenue, ratings)
5. Admin panel (featured listings, fraud detection)

## 10. Risk & Compliance

| Risk | Mitigation |
|------|------------|
| Cloned strategy references deleted strategies | Soft-delete or nullify `strategy_ids` on clone |
| Purchased strategy depends on custom node buyer doesn't have | Include dependency manifest in listing; validate on purchase |
| Royalty tracking across deep clone chains | Chain model (each clone tracks direct parent). Walk chain for royalty distribution. |
| Users selling strategies built on copyrighted code | License terms in EULA; DMCA takedown endpoint |
| Fraudulent purchases / chargebacks | All purchases via internal wallet balance; no external payment integration in v1 |

## 11. Future Marketplace Features

- **Strategy bundles**: Buy "Volatility Trading Pack" (3 strategies + 2 risk templates)
- **Subscription tiers**: Monthly access to curated template catalog
- **Performance badges**: Verified sharpe/win-rate badges on listings
- **Review system**: 5-star rating + written review after purchase
- **Strategy leasing**: Time-limited access (30 days) at lower price
- **Team sharing**: Group/clan-based artifact libraries
- **Cross-user evolution**: GP that evolves from public template pool with attribution
