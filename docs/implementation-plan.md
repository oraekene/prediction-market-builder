# Prediction Market Strategy Builder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web-based prediction market terminal with hybrid chat+node strategy builder, powered by TabPFN/Toto-2/Hermes-Agent AI pipeline, targeting Polymarket/Kalshi/Drift.

**Architecture:** Five-layer system: React+Vite frontend (Shadcn/UI + React Flow node canvas) → FastAPI backend → Hermes-Agent orchestration → TabPFN/Toto-2/RLM analysis layer → LanceDB/DuckDB/ChromaDB data layer. Deployed on Oracle Cloud + Postgres + Cloudflare, with serverless GPU for AI inference.

**Tech Stack:** React 19, TypeScript, Vite, Shadcn/UI, Tailwind, React Flow, TanStack Query, Zustand, FastAPI, Python 3.12, LanceDB, DuckDB, ChromaDB, TabPFN, Toto-2, Hermes-Agent, DSPy, SearXNG, Scrapling, Camoufox/Playwright, ONNX Runtime, Oracle Cloud, Postgres, Cloudflare.

---

## File Structure

```
prediction-market-builder/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── lib/
│   │   │   ├── api.ts              # API client (TanStack Query hooks)
│   │   │   ├── websocket.ts        # Real-time data connection
│   │   │   ├── store.ts            # Zustand global store
│   │   │   ├── validators.ts       # Zod schemas
│   │   │   └── utils.ts            # Shared utilities
│   │   ├── components/
│   │   │   ├── ui/                 # Shadcn/UI primitives
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── StatusBar.tsx
│   │   │   │   └── MainLayout.tsx
│   │   │   ├── markets/
│   │   │   │   ├── MarketTable.tsx
│   │   │   │   ├── MarketRow.tsx
│   │   │   │   ├── MarketDetail.tsx
│   │   │   │   ├── MarketSearch.tsx
│   │   │   │   └── OddsComparison.tsx
│   │   │   ├── strategies/
│   │   │   │   ├── StrategyList.tsx
│   │   │   │   ├── StrategyCard.tsx
│   │   │   │   ├── NodeCanvas.tsx   # React Flow wrapper
│   │   │   │   ├── NodePalette.tsx
│   │   │   │   ├── NodePropertyPanel.tsx
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   └── BacktestResults.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatInterface.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   └── ChatInput.tsx
│   │   │   ├── analytics/
│   │   │   │   ├── PortfolioView.tsx
│   │   │   │   ├── PerformanceChart.tsx
│   │   │   │   └── RiskDashboard.tsx
│   │   │   └── alerts/
│   │   │       ├── AlertList.tsx
│   │   │       └── AlertForm.tsx
│   │   ├── hooks/
│   │   │   ├── useMarkets.ts
│   │   │   ├── useStrategies.ts
│   │   │   ├── usePortfolio.ts
│   │   │   └── useWebSocket.ts
│   │   ├── types/
│   │   │   ├── market.ts
│   │   │   ├── strategy.ts
│   │   │   ├── node.ts
│   │   │   └── api.ts
│   │   └── pages/
│   │       ├── MarketsPage.tsx
│   │       ├── StrategiesPage.tsx
│   │       ├── AnalyticsPage.tsx
│   │       └── SettingsPage.tsx
│   └── public/
│       └── favicon.svg
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── market.py
│   │   │   ├── strategy.py
│   │   │   └── trade.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── markets.py
│   │   │   ├── strategies.py
│   │   │   ├── portfolio.py
│   │   │   ├── alerts.py
│   │   │   └── analytics.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_aggregator.py
│   │   │   ├── strategy_engine.py
│   │   │   ├── backtester.py
│   │   │   ├── risk_manager.py
│   │   │   ├── execution.py
│   │   │   └── alerts.py
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── tabpfn_service.py
│   │   │   ├── toto2_service.py
│   │   │   ├── hermes_agent.py
│   │   │   ├── rlm_service.py
│   │   │   ├── autoresearch.py
│   │   │   ├── embeddings.py
│   │   │   └── reranker.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── duckdb_manager.py
│   │   │   ├── lancedb_manager.py
│   │   │   └── chromadb_manager.py
│   │   └── agentic_search/
│   │       ├── __init__.py
│   │       ├── searxng_client.py
│   │       ├── scrapling_parser.py
│   │       ├── camoufox_playwright.py
│   │       └── search_orchestrator.py
│   └── tests/
│       ├── conftest.py
│       ├── test_markets.py
│       ├── test_strategies.py
│       ├── test_backtester.py
│       ├── test_risk_manager.py
│       └── test_ai_services.py
├── infrastructure/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   ├── cloudflare.toml
│   └── scripts/
│       ├── deploy.sh
│       ├── seed_data.py
│       └── migrate.sh
└── .env.example
```

---

## Phase 1: Foundation (Weeks 1-6)

**Goal:** Working terminal with data aggregation + basic strategy creation. Infrastructure, data ingestion, UI shell, market discovery, chat interface, simple threshold-based strategies.

---

### Task 1.1: Project Scaffolding & Infrastructure

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `infrastructure/docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create backend pyproject.toml**

```toml
[project]
name = "pm-strategy-builder"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.13.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.27.0",
    "websockets>=12.0",
    "lancedb>=0.10.0",
    "duckdb>=1.0.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "numpy>=1.26.0",
    "pandas>=2.2.0",
    "tabpfn>=0.1.0",
    "dspy>=2.5.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: Create backend requirements.txt**

```
-r pyproject.toml
```

- [ ] **Step 3: Create backend config**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/pmbuilder"
    postgres_url: str = "postgresql+asyncpg://user:pass@localhost:5432/pmbuilder"
    duckdb_path: str = "./data/analytics.duckdb"
    lancedb_path: str = "./data/vectors"
    chromadb_path: str = "./data/memory"
    oracle_instance_id: str = ""
    cloudflare_api_token: str = ""
    claude_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    tabpfn_model: str = "tabpfn-2.5"
    toto2_model: str = "toto-2"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Create FastAPI app entry point**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    await engine.dispose()


app = FastAPI(title="PM Strategy Builder", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 5: Create database setup**

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 6: Create frontend package.json**

```json
{
  "name": "pm-strategy-builder-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^5.0.0",
    "react-router-dom": "^7.0.0",
    "@xyflow/react": "^12.0.0",
    "lucide-react": "^0.450.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "zod": "^3.23.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 7: Create vite config**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 8: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 9: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PM Strategy Builder</title>
  </head>
  <body class="dark">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 10: Create main.tsx**

```typescript
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 11: Create App.tsx (routing shell)**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/components/layout/MainLayout'
import MarketsPage from '@/pages/MarketsPage'
import StrategiesPage from '@/pages/StrategiesPage'
import AnalyticsPage from '@/pages/AnalyticsPage'
import SettingsPage from '@/pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/markets" replace />} />
          <Route path="/markets" element={<MarketsPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 12: Create docker-compose.yml**

```yaml
# infrastructure/docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pmbuilder
      POSTGRES_USER: pmuser
      POSTGRES_PASSWORD: pmpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  searxng:
    image: searxng/searxng:latest
    ports:
      - "8888:8080"
    volumes:
      - searxng-data:/etc/searxng
    environment:
      SEARXNG_BASE_URL: http://localhost:8888

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
    volumes:
      - ./data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  pgdata:
  searxng-data:
```

- [ ] **Step 13: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://pmuser:pmpass@localhost:5432/pmbuilder
SECRET_KEY=change-me-in-production
CLAUDE_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

- [ ] **Step 14: Verify both projects start**

Run: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
Expected: Server starts on port 8000, `/health` returns `{"status": "ok"}`

Run: `cd frontend && npm install && npm run dev`
Expected: Vite dev server starts on port 5173

---

### Task 1.2: Data Models & Database Migrations

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/market.py`
- Create: `backend/app/models/strategy.py`
- Create: `backend/app/models/trade.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create User model**

```python
# backend/app/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Platform API keys stored encrypted
    polymarket_key: Mapped[str] = mapped_column(String, nullable=True)
    kalshi_key: Mapped[str] = mapped_column(String, nullable=True)
    drift_key: Mapped[str] = mapped_column(String, nullable=True)
    # Preferences
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
```

- [ ] **Step 2: Create Market model**

```python
# backend/app/models/market.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class MarketPlatform(str, enum.Enum):
    POLYMARKET = "polymarket"
    KALSHI = "kalshi"
    DRIFT = "drift"


class MarketStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    platform: Mapped[MarketPlatform] = mapped_column(SAEnum(MarketPlatform))
    platform_market_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    current_odds: Mapped[float] = mapped_column(Float)
    bid: Mapped[float] = mapped_column(Float, nullable=True)
    ask: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, default=0)
    liquidity: Mapped[float] = mapped_column(Float, default=0)
    participants: Mapped[int] = mapped_column(Float, default=0)
    close_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolution_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[MarketStatus] = mapped_column(SAEnum(MarketStatus), default=MarketStatus.OPEN)
    outcomes: Mapped[dict] = mapped_column(JSON, default=list)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        sa.UniqueConstraint("platform", "platform_market_id", name="uq_platform_market"),
    )
```

- [ ] **Step 3: Create Strategy model**

```python
# backend/app/models/strategy.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[StrategyStatus] = mapped_column(SAEnum(StrategyStatus), default=StrategyStatus.DRAFT)
    mode: Mapped[str] = mapped_column(String, default="chat")  # chat | node | hybrid
    nodes: Mapped[dict] = mapped_column(JSON, default=list)
    edges: Mapped[dict] = mapped_column(JSON, default=list)
    risk_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Create Trade model**

```python
# backend/app/models/trade.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String, nullable=True)
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)  # buy | sell | yes | no
    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[TradeStatus] = mapped_column(SAEnum(TradeStatus), default=TradeStatus.PENDING)
    platform_trade_id: Mapped[str] = mapped_column(String, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Create conftest.py**

```python
# backend/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_market():
    return {
        "platform": "polymarket",
        "platform_market_id": "test-123",
        "title": "Will candidate X win?",
        "current_odds": 0.65,
        "volume": 1000000,
        "status": "open",
    }
```

- [ ] **Step 6: Create Alembic initial migration**

Run: `cd backend && alembic init alembic && alembic revision --autogenerate -m "initial models" && alembic upgrade head`
Expected: Tables `users`, `markets`, `strategies`, `trades` created in Postgres

---

### Task 1.3: Authentication

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`

- [ ] **Step 1: Create auth router**

```python
# backend/app/routers/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext

from app.database import get_session
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        hashed_password=pwd_context.hash(req.password),
        display_name=req.display_name,
    )
    session.add(user)
    await session.commit()
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.secret_key,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.secret_key,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, user_id=user.id)
```

- [ ] **Step 2: Register router in main.py**

```python
# Add to backend/app/main.py after app = FastAPI(...)
from app.routers import auth
app.include_router(auth.router)
```

- [ ] **Step 3: Test auth endpoints**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: Register + login tests pass

---

### Task 1.4: Market Data Aggregation — Polymarket API Connector

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/market_aggregator.py`
- Create: `backend/app/routers/markets.py`
- Create: `backend/tests/test_markets.py`

- [ ] **Step 1: Create market aggregator service**

```python
# backend/app/services/market_aggregator.py
import httpx
from datetime import datetime
from typing import Any
from app.models.market import MarketPlatform, MarketStatus


class PolymarketConnector:
    BASE_URL = "https://clob.polymarket.com"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/markets",
                params={"limit": limit, "offset": offset},
                timeout=30,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json().get("data", [])]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/markets/{market_id}", timeout=30)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._normalize(resp.json())

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": MarketPlatform.POLYMARKET,
            "platform_market_id": raw.get("id", ""),
            "title": raw.get("question", raw.get("title", "")),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "current_odds": float(raw.get("outcomePrices", [0.5])[0]) if raw.get("outcomePrices") else 0.5,
            "bid": float(raw.get("bid", 0)),
            "ask": float(raw.get("ask", 0)),
            "volume": float(raw.get("volume", 0)),
            "liquidity": float(raw.get("liquidity", 0)),
            "participants": int(raw.get("participants", 0)),
            "close_time": raw.get("closeTime"),
            "status": MarketStatus.OPEN if raw.get("closed") is False else MarketStatus.CLOSED,
            "outcomes": raw.get("outcomes", ["Yes", "No"]),
            "raw_data": raw,
            "last_updated": datetime.utcnow().isoformat(),
        }


class KalshiConnector:
    BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/markets",
                params={"limit": limit, "offset": offset},
                timeout=30,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json().get("markets", [])]
        # _normalize follows same pattern as PolymarketConnector

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": MarketPlatform.KALSHI,
            "platform_market_id": raw.get("ticker", raw.get("id", "")),
            "title": raw.get("title", raw.get("question", "")),
            "current_odds": float(raw.get("yes_bid", 0.5)),
            "volume": float(raw.get("volume", 0)),
            "status": MarketStatus.OPEN if raw.get("status") == "open" else MarketStatus.CLOSED,
            "outcomes": ["Yes", "No"],
            "raw_data": raw,
            "last_updated": datetime.utcnow().isoformat(),
        }


class DriftConnector:
    BASE_URL = "https://api.drift.trade"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v2/markets",
                params={"limit": limit, "offset": offset},
                timeout=30,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json()]


class MarketAggregator:
    def __init__(self):
        self.connectors = {
            "polymarket": PolymarketConnector(),
            "kalshi": KalshiConnector(),
            "drift": DriftConnector(),
        }

    async def fetch_all(self, platforms: list[str] | None = None) -> list[dict[str, Any]]:
        targets = platforms or list(self.connectors.keys())
        results = []
        for platform in targets:
            connector = self.connectors.get(platform)
            if connector:
                try:
                    markets = await connector.fetch_markets()
                    results.extend(markets)
                except Exception as e:
                    print(f"Failed to fetch from {platform}: {e}")
        return results
```

- [ ] **Step 2: Create markets router**

```python
# backend/app/routers/markets.py
from fastapi import APIRouter, Query
from app.services.market_aggregator import MarketAggregator

router = APIRouter(prefix="/api/markets", tags=["markets"])
aggregator = MarketAggregator()


@router.get("")
async def list_markets(
    platform: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    min_volume: float | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    platforms = [platform] if platform else None
    markets = await aggregator.fetch_all(platforms)
    # Apply filters
    if category:
        markets = [m for m in markets if m.get("category", "").lower() == category.lower()]
    if search:
        markets = [m for m in markets if search.lower() in m.get("title", "").lower()]
    if min_volume:
        markets = [m for m in markets if (m.get("volume") or 0) >= min_volume]
    return {"markets": markets[offset: offset + limit], "total": len(markets)}


@router.get("/{market_id}")
async def get_market(market_id: str):
    for connector in aggregator.connectors.values():
        market = await connector.fetch_market(market_id)
        if market:
            return market
    return {"error": "Market not found"}
```

- [ ] **Step 3: Register markets router in main.py**

```python
# Add to backend/app/main.py
from app.routers import markets
app.include_router(markets.router)
```

- [ ] **Step 4: Create test for market aggregator**

```python
# backend/tests/test_markets.py
import pytest
from app.services.market_aggregator import PolymarketConnector


@pytest.mark.asyncio
async def test_polymarket_normalize():
    connector = PolymarketConnector()
    raw = {
        "id": "123",
        "question": "Will it rain?",
        "outcomePrices": ["0.65", "0.35"],
        "volume": "1000000",
        "closed": False,
    }
    result = connector._normalize(raw)
    assert result["platform_market_id"] == "123"
    assert result["title"] == "Will it rain?"
    assert result["current_odds"] == 0.65
    assert result["volume"] == 1000000.0
```

Run: `pytest tests/test_markets.py -v`
Expected: All tests pass

---

### Task 1.5: Main Layout — Header, Sidebar, Terminal Shell

**Files:**
- Create: `frontend/src/components/layout/MainLayout.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/StatusBar.tsx`
- Create: `frontend/src/pages/MarketsPage.tsx`
- Create: `frontend/src/pages/StrategiesPage.tsx`
- Create: `frontend/src/pages/AnalyticsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/types/market.ts`
- Create: `frontend/src/types/strategy.ts`

- [ ] **Step 1: Create types**

```typescript
// frontend/src/types/market.ts
export type MarketPlatform = 'polymarket' | 'kalshi' | 'drift'
export type MarketStatus = 'open' | 'closed' | 'resolved'

export interface Market {
  id: string
  platform: MarketPlatform
  platform_market_id: string
  title: string
  description?: string
  category?: string
  current_odds: number
  bid?: number
  ask?: number
  volume: number
  liquidity: number
  participants: number
  close_time?: string
  status: MarketStatus
  outcomes: string[]
  last_updated: string
}
```

```typescript
// frontend/src/types/strategy.ts
export type StrategyStatus = 'draft' | 'active' | 'paused' | 'archived'
export type StrategyMode = 'chat' | 'node' | 'hybrid'

export interface StrategyNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export interface StrategyEdge {
  id: string
  source: string
  target: string
}

export interface Strategy {
  id: string
  name: string
  description?: string
  status: StrategyStatus
  mode: StrategyMode
  nodes: StrategyNode[]
  edges: StrategyEdge[]
  risk_profile: Record<string, unknown>
  created_at: string
  updated_at: string
}
```

- [ ] **Step 2: Create utils**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatOdds(odds: number): string {
  return `${(odds * 100).toFixed(1)}%`
}

export function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`
  return volume.toFixed(0)
}

export function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
```

- [ ] **Step 3: Create Header component**

```typescript
// frontend/src/components/layout/Header.tsx
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/markets', label: 'Markets' },
  { path: '/strategies', label: 'Strategies' },
  { path: '/analytics', label: 'Analytics' },
  { path: '/settings', label: 'Settings' },
]

export default function Header() {
  const location = useLocation()
  return (
    <header className="border-b border-gray-800 bg-gray-950 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <span className="text-lg font-bold text-white">PM Builder</span>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm transition-colors',
                  location.pathname.startsWith(item.path)
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-white'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">Connected</span>
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 4: Create Sidebar**

```typescript
// frontend/src/components/layout/Sidebar.tsx
import { useState } from 'react'

export default function Sidebar() {
  const [activeSection, setActiveSection] = useState('watchlist')
  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-950 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Market Watch</h3>
      <div className="space-y-1">
        {['All Markets', 'Politics', 'Economy', 'Crypto', 'Sports', 'Watchlist'].map((item) => (
          <button
            key={item}
            onClick={() => setActiveSection(item.toLowerCase())}
            className={`w-full rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
              activeSection === item.toLowerCase()
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {item}
          </button>
        ))}
      </div>
    </aside>
  )
}
```

- [ ] **Step 5: Create StatusBar**

```typescript
// frontend/src/components/layout/StatusBar.tsx
export default function StatusBar() {
  return (
    <footer className="border-t border-gray-800 bg-gray-950 px-6 py-1.5">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Polymarket: Live | Kalshi: Live | Drift: Live</span>
        <span>Last updated: {new Date().toLocaleTimeString()}</span>
      </div>
    </footer>
  )
}
```

- [ ] **Step 6: Create MainLayout**

```typescript
// frontend/src/components/layout/MainLayout.tsx
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'

export default function MainLayout() {
  return (
    <div className="flex h-screen flex-col bg-gray-900 text-gray-100">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <StatusBar />
    </div>
  )
}
```

- [ ] **Step 7: Create placeholder pages**

```typescript
// frontend/src/pages/MarketsPage.tsx
export default function MarketsPage() {
  return <div><h1 className="text-xl font-semibold">Markets</h1><p className="mt-2 text-gray-400">Market data will appear here.</p></div>
}

// frontend/src/pages/StrategiesPage.tsx
export default function StrategiesPage() {
  return <div><h1 className="text-xl font-semibold">Strategies</h1><p className="mt-2 text-gray-400">Strategy builder will appear here.</p></div>
}

// frontend/src/pages/AnalyticsPage.tsx
export default function AnalyticsPage() {
  return <div><h1 className="text-xl font-semibold">Analytics</h1><p className="mt-2 text-gray-400">Analytics will appear here.</p></div>
}

// frontend/src/pages/SettingsPage.tsx
export default function SettingsPage() {
  return <div><h1 className="text-xl font-semibold">Settings</h1><p className="mt-2 text-gray-400">Settings will appear here.</p></div>
}
```

- [ ] **Step 8: Update index.css with Tailwind**

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: dark;
}

body {
  @apply bg-gray-900 text-gray-100;
}
```

- [ ] **Step 9: Verify layout renders**

Run: `cd frontend && npm run dev`
Expected: Browser shows dark terminal layout with header, sidebar, main area, status bar

---

### Task 1.6: Market Table — Real-Time Data Display

**Files:**
- Create: `frontend/src/components/ui/` (Shadcn table primitives)
- Create: `frontend/src/components/markets/MarketTable.tsx`
- Create: `frontend/src/components/markets/MarketRow.tsx`
- Create: `frontend/src/components/markets/MarketSearch.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useMarkets.ts`

- [ ] **Step 1: Create API client**

```typescript
// frontend/src/lib/api.ts
const BASE_URL = '/api'

export async function fetchMarkets(params?: Record<string, string>): Promise<{ markets: any[]; total: number }> {
  const searchParams = new URLSearchParams(params)
  const res = await fetch(`${BASE_URL}/markets?${searchParams}`)
  if (!res.ok) throw new Error('Failed to fetch markets')
  return res.json()
}

export async function fetchMarket(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/markets/${id}`)
  if (!res.ok) throw new Error('Market not found')
  return res.json()
}
```

- [ ] **Step 2: Create useMarkets hook**

```typescript
// frontend/src/hooks/useMarkets.ts
import { useQuery } from '@tanstack/react-query'
import { fetchMarkets } from '@/lib/api'

export function useMarkets(params?: Record<string, string>) {
  return useQuery({
    queryKey: ['markets', params],
    queryFn: () => fetchMarkets(params),
    refetchInterval: 30_000, // Poll every 30s
  })
}

export function useMarket(id: string) {
  return useQuery({
    queryKey: ['market', id],
    queryFn: () => fetch(`/api/markets/${id}`).then(r => r.json()),
    enabled: !!id,
  })
}
```

- [ ] **Step 3: Create MarketTable component**

```typescript
// frontend/src/components/markets/MarketTable.tsx
import { useMarkets } from '@/hooks/useMarkets'
import { formatOdds, formatVolume, formatTime } from '@/lib/utils'
import MarketSearch from './MarketSearch'

export default function MarketTable() {
  const { data, isLoading, error } = useMarkets()

  if (isLoading) return <div className="text-gray-400">Loading markets...</div>
  if (error) return <div className="text-red-400">Error loading markets</div>

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Markets</h1>
        <MarketSearch />
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-950 text-left text-xs uppercase text-gray-500">
              <th className="px-4 py-3 font-medium">Market</th>
              <th className="px-4 py-3 font-medium">Platform</th>
              <th className="px-4 py-3 font-medium">Odds</th>
              <th className="px-4 py-3 font-medium">Volume</th>
              <th className="px-4 py-3 font-medium">Close</th>
            </tr>
          </thead>
          <tbody>
            {data?.markets.map((market: any) => (
              <MarketRow key={`${market.platform}-${market.platform_market_id}`} market={market} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MarketRow({ market }: { market: any }) {
  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/50">
      <td className="px-4 py-3">
        <div className="font-medium text-white">{market.title}</div>
        {market.category && <div className="text-xs text-gray-500">{market.category}</div>}
      </td>
      <td className="px-4 py-3">
        <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs capitalize">{market.platform}</span>
      </td>
      <td className={`px-4 py-3 font-mono font-medium ${market.current_odds >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
        {formatOdds(market.current_odds)}
      </td>
      <td className="px-4 py-3 font-mono text-gray-300">{formatVolume(market.volume)}</td>
      <td className="px-4 py-3 text-gray-400">{market.close_time ? formatTime(market.close_time) : '-'}</td>
    </tr>
  )
}
```

- [ ] **Step 4: Create MarketSearch**

```typescript
// frontend/src/components/markets/MarketSearch.tsx
import { useState } from 'react'

export default function MarketSearch() {
  const [query, setQuery] = useState('')
  return (
    <input
      type="text"
      placeholder="Search markets..."
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      className="w-64 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
    />
  )
}
```

- [ ] **Step 5: Update MarketsPage to use MarketTable**

```typescript
// frontend/src/pages/MarketsPage.tsx
import MarketTable from '@/components/markets/MarketTable'
export default function MarketsPage() {
  return <MarketTable />
}
```

- [ ] **Step 6: Verify market table renders**

Run: `cd frontend && npm run dev`
Expected: Market table with header, loading state, and data from API

---

### Task 1.7: Chat Interface — Guided Mode for Beginners

**Files:**
- Create: `frontend/src/components/chat/ChatInterface.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/lib/websocket.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Create WebSocket client**

```typescript
// frontend/src/lib/websocket.ts
export class ChatWebSocket {
  private ws: WebSocket | null = null
  private listeners: Map<string, (data: any) => void> = new Map()

  connect() {
    this.ws = new WebSocket(`ws://${window.location.host}/ws/chat`)
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      const handler = this.listeners.get(msg.type)
      if (handler) handler(msg)
    }
  }

  send(type: string, payload: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }))
    }
  }

  on(type: string, handler: (data: any) => void) {
    this.listeners.set(type, handler)
  }

  disconnect() {
    this.ws?.close()
  }
}

export const chatWs = new ChatWebSocket()
```

- [ ] **Step 2: Create ChatMessage component**

```typescript
// frontend/src/components/chat/ChatMessage.tsx
import { cn } from '@/lib/utils'

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export default function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  return (
    <div className={cn('mb-3 flex', role === 'user' ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          role === 'user' && 'bg-blue-600 text-white',
          role === 'assistant' && 'bg-gray-800 text-gray-100',
          role === 'system' && 'bg-gray-950 text-gray-400 text-xs italic',
        )}
      >
        <p className="text-sm">{content}</p>
        {timestamp && <p className="mt-1 text-right text-xs opacity-50">{timestamp}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create ChatInput**

```typescript
// frontend/src/components/chat/ChatInput.tsx
import { useState, useRef } from 'react'
import { chatWs } from '@/lib/websocket'

interface ChatInputProps {
  onSend?: (message: string) => void
}

export default function ChatInput({ onSend }: ChatInputProps) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    const msg = input.trim()
    setInput('')
    chatWs.send('chat_message', { content: msg })
    onSend?.(msg)
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-800 p-4">
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything... e.g. 'Show me political markets' or 'Create a strategy'"
          className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Send
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 4: Create ChatInterface**

```typescript
// frontend/src/components/chat/ChatInterface.tsx
import { useState, useEffect, useRef } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import { chatWs } from '@/lib/websocket'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '0', role: 'system', content: 'Welcome! I can help you discover markets, create strategies, and analyze predictions. Try: "Show me trending markets" or "Create a strategy"', timestamp: new Date().toISOString() },
  ])
  const [isOpen, setIsOpen] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatWs.connect()
    chatWs.on('chat_response', (data) => {
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'assistant', content: data.content, timestamp: new Date().toISOString() }])
    })
    return () => chatWs.disconnect()
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend(content: string) {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content, timestamp: new Date().toISOString() }])
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-20 right-6 z-50 rounded-full bg-blue-600 p-3 text-white shadow-lg hover:bg-blue-700"
      >
        {isOpen ? 'X' : 'Chat'}
      </button>
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[500px] w-[400px] flex-col rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
          <div className="flex-1 overflow-y-auto p-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} role={msg.role} content={msg.content} timestamp={msg.timestamp} />
            ))}
            <div ref={endRef} />
          </div>
          <ChatInput onSend={handleSend} />
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 5: Add ChatInterface to App.tsx**

```typescript
// Add to frontend/src/App.tsx
import ChatInterface from '@/components/chat/ChatInterface'
// ... inside BrowserRouter, before closing tag:
<ChatInterface />
```

- [ ] **Step 6: Create WebSocket chat handler in backend**

```python
# Create backend/app/routers/chat.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()


class ChatManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def handle_message(self, websocket: WebSocket, data: dict):
        content = data.get("payload", {}).get("content", "")
        # TODO: Route to Hermes-Agent for processing
        # For now, echo a simple response
        response = {"type": "chat_response", "content": f"Received: {content}. AI processing coming in Phase 2."}
        await websocket.send_json(response)


chat_manager = ChatManager()


@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await chat_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await chat_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket)
```

- [ ] **Step 7: Register chat router in main.py**

```python
from app.routers import chat
# Add before lifespan
# No additional line needed — included with pattern
```

- [ ] **Step 8: Verify chat interface works**

Run both backend and frontend. Click chat button → type message → see response.

---

## Phase 2: Intelligence (Weeks 7-12)

**Goal:** AI-powered analysis with TabPFN/Toto-2, LanceDB/DuckDB data layer, node canvas strategy builder.

---

### Task 2.1: Vector & Analytics Data Layer Setup

**Files:**
- Create: `backend/app/data/__init__.py`
- Create: `backend/app/data/lancedb_manager.py`
- Create: `backend/app/data/duckdb_manager.py`
- Create: `backend/app/data/chromadb_manager.py`
- Create: `backend/tests/test_data_layer.py`

- [ ] **Step 1: Create LanceDB manager**

```python
# backend/app/data/lancedb_manager.py
import lancedb
import pyarrow as pa
from app.config import settings

class LanceDBManager:
    def __init__(self):
        self.db = lancedb.connect(settings.lancedb_path)
        self._ensure_tables()

    def _ensure_tables(self):
        tables = self.db.table_names()
        if "market_vectors" not in tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("market_id", pa.string()),
                pa.field("platform", pa.string()),
                pa.field("embedding", pa.list_(pa.float32(), 384)),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ])
            self.db.create_table("market_vectors", schema=schema)

    def search_markets(self, query_vector: list[float], filter_ids: list[str] | None = None, top_k: int = 20):
        table = self.db.open_table("market_vectors")
        query = table.search(query_vector)
        if filter_ids:
            query = query.where(f"market_id IN ({','.join(f"'{f}'" for f in filter_ids)})")
        return query.limit(top_k).to_list()

    def upsert_market_vector(self, id: str, market_id: str, platform: str, embedding: list[float], text: str, metadata: str = "{}"):
        table = self.db.open_table("market_vectors")
        table.merge_insert(["id"]).when_matched_update_all().execute([{
            "id": id,
            "market_id": market_id,
            "platform": platform,
            "embedding": embedding,
            "text": text,
            "metadata": metadata,
        }])
```

- [ ] **Step 2: Create DuckDB manager**

```python
# backend/app/data/duckdb_manager.py
import duckdb
from app.config import settings

class DuckDBManager:
    def __init__(self):
        self.conn = duckdb.connect(settings.duckdb_path)
        self._ensure_tables()

    def _ensure_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_analytics (
                id VARCHAR,
                platform VARCHAR,
                title VARCHAR,
                category VARCHAR,
                current_odds DOUBLE,
                volume DOUBLE,
                liquidity DOUBLE,
                participants INTEGER,
                close_time TIMESTAMP,
                status VARCHAR,
                last_updated TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id VARCHAR,
                strategy_id VARCHAR,
                total_trades INTEGER,
                win_rate DOUBLE,
                profit_loss DOUBLE,
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                period_start DATE,
                period_end DATE
            )
        """)

    def query_markets(self, sql_filter: str = "1=1", limit: int = 1000) -> list[dict]:
        result = self.conn.execute(f"""
            SELECT * FROM market_analytics WHERE {sql_filter} LIMIT {limit}
        """)
        return [dict(row) for row in result.fetchall()]

    def insert_market(self, data: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO market_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [data.get(k) for k in ["id", "platform", "title", "category", "current_odds", "volume", "liquidity", "participants", "close_time", "status", "last_updated"]])

    def get_top_categories(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT category, COUNT(*) as count FROM market_analytics GROUP BY category ORDER BY count DESC").fetchall()]

    def get_volume_leaders(self, top_n: int = 10) -> list[dict]:
        return [dict(r) for r in self.conn.execute(f"SELECT title, platform, volume FROM market_analytics ORDER BY volume DESC LIMIT {top_n}").fetchall()]
```

- [ ] **Step 3: Create ChromaDB manager**

```python
# backend/app/data/chromadb_manager.py
import chromadb
from app.config import settings

class ChromaDBManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chromadb_path)
        self._ensure_collections()

    def _ensure_collections(self):
        for name in ["agent_memory", "strategy_templates"]:
            try:
                self.client.get_collection(name)
            except ValueError:
                self.client.create_collection(name)

    def store_memory(self, collection: str, memory_id: str, text: str, metadata: dict | None = None):
        col = self.client.get_collection(collection)
        col.add(documents=[text], ids=[memory_id], metadatas=[metadata or {}])

    def recall_similar(self, collection: str, query: str, n_results: int = 5) -> list[dict]:
        col = self.client.get_collection(collection)
        results = col.query(query_texts=[query], n_results=n_results)
        return [
            {"id": results["ids"][0][i], "text": results["documents"][0][i], "metadata": results["metadatas"][0][i]}
            for i in range(len(results["ids"][0]))
        ]
```

- [ ] **Step 4: Create tests**

```python
# backend/tests/test_data_layer.py
import pytest
from app.data.duckdb_manager import DuckDBManager

def test_duckdb_insert_and_query():
    mgr = DuckDBManager()
    mgr.insert_market({
        "id": "test-1", "platform": "polymarket", "title": "Test Market",
        "category": "politics", "current_odds": 0.65, "volume": 100000,
        "liquidity": 50000, "participants": 100, "close_time": None,
        "status": "open", "last_updated": None,
    })
    results = mgr.query_markets("category = 'politics'")
    assert len(results) >= 1
    assert results[0]["title"] == "Test Market"
```

Run: `pytest tests/test_data_layer.py -v`
Expected: All tests pass

---

### Task 2.2: TabPFN Service Integration

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/tabpfn_service.py`
- Create: `backend/app/ai/embeddings.py`
- Create: `backend/tests/test_ai_services.py`

- [ ] **Step 1: Create embeddings service**

```python
# backend/app/ai/embeddings.py
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._instance

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def encode_market(self, market: dict) -> list[float]:
        text = f"{market.get('title', '')} {market.get('description', '')} {market.get('category', '')}"
        return self.encode(text)
```

- [ ] **Step 2: Create TabPFN service**

```python
# backend/app/ai/tabpfn_service.py
import numpy as np
import pandas as pd

class TabPFNService:
    def __init__(self):
        self.model = None

    async def initialize(self):
        """Lazy-load TabPFN model (large download on first use)."""
        if self.model is None:
            from tabpfn import TabPFNClassifier
            self.model = TabPFNClassifier()

    async def predict_probability(self, features: pd.DataFrame, context: pd.DataFrame | None = None) -> float:
        """Zero-shot Bayesian inference. Returns calibrated probability."""
        await self.initialize()
        if context is not None:
            X_train = context.drop(columns=["target"], errors="ignore")
            y_train = context["target"] if "target" in context.columns else None
        else:
            X_train = features
            y_train = None
        probabilities = self.model.predict_proba(features)
        return float(probabilities[0][1]) if probabilities.shape[1] > 1 else float(probabilities[0][0])

    async def validate_signal(self, market_data: dict, regime_vector: list[float] | None = None) -> dict:
        """Validate a trading signal using TabPFN Bayesian inference."""
        df = pd.DataFrame([{
            "odds": market_data.get("current_odds", 0.5),
            "volume": market_data.get("volume", 0) / 1_000_000,
            "liquidity": market_data.get("liquidity", 0) / 1_000_000,
            "spread": (market_data.get("ask", 0) or 0) - (market_data.get("bid", 0) or 0),
            "participants": market_data.get("participants", 0) / 1000,
        }])
        if regime_vector:
            for i, v in enumerate(regime_vector):
                df[f"regime_{i}"] = v
        probability = await self.predict_probability(df)
        confidence = min(probability, 1 - probability) * 2  # Scale to 0-1
        return {
            "probability": probability,
            "confidence": round(confidence, 3),
            "edge": round(probability - (market_data.get("current_odds", 0.5)), 4),
            "verdict": "APPROVED" if probability > 0.6 else "REJECTED",
        }

    async def get_feature_importance(self, features: pd.DataFrame) -> dict[str, float]:
        """Return SHAP-style feature importance scores."""
        await self.initialize()
        # Simplified: use model internal feature attribution
        if hasattr(self.model, "feature_importances_"):
            return dict(zip(features.columns, self.model.feature_importances_))
        return {col: 0.0 for col in features.columns}
```

- [ ] **Step 3: Create tests**

```python
# backend/tests/test_ai_services.py
import pytest
import pandas as pd
from app.ai.tabpfn_service import TabPFNService
from app.ai.embeddings import EmbeddingService

@pytest.mark.asyncio
async def test_tabpfn_signal_validation():
    service = TabPFNService()
    result = await service.validate_signal({
        "current_odds": 0.45,
        "volume": 1_000_000,
        "liquidity": 500_000,
        "bid": 0.44,
        "ask": 0.46,
        "participants": 500,
    })
    assert "probability" in result
    assert "verdict" in result
    assert result["verdict"] in ("APPROVED", "REJECTED")

def test_embedding_encode():
    service = EmbeddingService()
    vec = service.encode("Will the Fed cut rates in June?")
    assert len(vec) == 384
    assert all(isinstance(v, float) for v in vec)
```

---

### Task 2.3: Node Canvas Strategy Builder

**Files:**
- Create: `frontend/src/components/strategies/NodeCanvas.tsx`
- Create: `frontend/src/components/strategies/NodePalette.tsx`
- Create: `frontend/src/components/strategies/NodePropertyPanel.tsx`
- Create: `frontend/src/components/strategies/StrategyList.tsx`
- Create: `frontend/src/hooks/useStrategies.ts`
- Modify: `frontend/src/pages/StrategiesPage.tsx`

- [ ] **Step 1: Create custom nodes for React Flow**

```typescript
// frontend/src/components/strategies/NodeCanvas.tsx
import { useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

const initialNodes: Node[] = [
  {
    id: 'source-1',
    type: 'default',
    position: { x: 50, y: 100 },
    data: { label: 'Polymarket Data' },
  },
  {
    id: 'condition-1',
    type: 'default',
    position: { x: 300, y: 100 },
    data: { label: 'Odds < 45%' },
  },
  {
    id: 'action-1',
    type: 'default',
    position: { x: 550, y: 100 },
    data: { label: 'Place Bet' },
  },
]

const initialEdges: Edge[] = [
  { id: 'e1', source: 'source-1', target: 'condition-1' },
  { id: 'e2', source: 'condition-1', target: 'action-1' },
]

export default function NodeCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const type = event.dataTransfer.getData('application/reactflow')
      if (!type) return
      const position = { x: event.clientX - 100, y: event.clientY - 50 }
      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type: 'default',
        position,
        data: { label: type },
      }
      setNodes((nds) => nds.concat(newNode))
    },
    [setNodes],
  )

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
```

- [ ] **Step 2: Create NodePalette**

```typescript
// frontend/src/components/strategies/NodePalette.tsx
const nodeTypes = [
  { category: 'Sources', items: ['Polymarket', 'Kalshi', 'Drift', 'Web Search', 'News'] },
  { category: 'Filters', items: ['TabPFN Signal', 'Toto-2 Climate', 'Sentiment'] },
  { category: 'Conditions', items: ['Threshold', 'Time-Based', 'AND/OR', 'Branch'] },
  { category: 'Actions', items: ['Place Bet', 'Send Alert', 'Forward', 'Webhook'] },
  { category: 'Risk', items: ['Kelly Criterion', 'Stop-Loss', 'Drawdown'] },
  { category: 'Analysis', items: ['Bayesian Inference', 'Monte Carlo', 'Backtest'] },
]

export default function NodePalette() {
  function onDragStart(event: React.DragEvent, nodeType: string) {
    event.dataTransfer.setData('application/reactflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="w-48 border-r border-gray-800 bg-gray-950 p-3">
      <h3 className="mb-3 text-xs font-semibold uppercase text-gray-500">Nodes</h3>
      {nodeTypes.map((group) => (
        <div key={group.category} className="mb-3">
          <h4 className="mb-1 text-xs text-gray-600">{group.category}</h4>
          <div className="space-y-1">
            {group.items.map((item) => (
              <div
                key={item}
                draggable
                onDragStart={(e) => onDragStart(e, item)}
                className="cursor-grab rounded border border-gray-700 bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:border-blue-500"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ))}
    </aside>
  )
}
```

- [ ] **Step 3: Create NodePropertyPanel**

```typescript
// frontend/src/components/strategies/NodePropertyPanel.tsx
import type { Node } from '@xyflow/react'

interface Props {
  selectedNode: Node | null
}

export default function NodePropertyPanel({ selectedNode }: Props) {
  if (!selectedNode) {
    return (
      <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4">
        <p className="text-sm text-gray-500">Select a node to configure</p>
      </aside>
    )
  }

  return (
    <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4">
      <h3 className="mb-3 text-sm font-semibold text-white">Configure: {selectedNode.data.label as string}</h3>
      <div className="space-y-3">
        <label className="block">
          <span className="text-xs text-gray-400">Parameter</span>
          <input className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-white" placeholder="Value" />
        </label>
      </div>
    </aside>
  )
}
```

- [ ] **Step 4: Create useStrategies hook**

```typescript
// frontend/src/hooks/useStrategies.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Strategy } from '@/types/strategy'

async function fetchStrategies(): Promise<Strategy[]> {
  const res = await fetch('/api/strategies')
  if (!res.ok) throw new Error('Failed to fetch strategies')
  return res.json()
}

async function createStrategy(data: Partial<Strategy>): Promise<Strategy> {
  const res = await fetch('/api/strategies', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
  if (!res.ok) throw new Error('Failed to create strategy')
  return res.json()
}

export function useStrategies() {
  return useQuery({ queryKey: ['strategies'], queryFn: fetchStrategies })
}

export function useCreateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createStrategy,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  })
}
```

- [ ] **Step 5: Update StrategiesPage**

```typescript
// frontend/src/pages/StrategiesPage.tsx
import { useState } from 'react'
import type { Node } from '@xyflow/react'
import NodeCanvas from '@/components/strategies/NodeCanvas'
import NodePalette from '@/components/strategies/NodePalette'
import NodePropertyPanel from '@/components/strategies/NodePropertyPanel'
import StrategyList from '@/components/strategies/StrategyList'

export default function StrategiesPage() {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showCanvas, setShowCanvas] = useState(false)

  if (!showCanvas) {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Strategies</h1>
          <button
            onClick={() => setShowCanvas(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Create Strategy
          </button>
        </div>
        <StrategyList />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <NodePalette />
      <div className="flex-1">
        <NodeCanvas />
      </div>
      <NodePropertyPanel selectedNode={selectedNode} />
    </div>
  )
}
```

- [ ] **Step 6: Create strategies router (backend)**

```python
# backend/app/routers/strategies.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.strategy import Strategy

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
async def list_strategies(user_id: str = "default", session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Strategy).where(Strategy.user_id == user_id))
    strategies = result.scalars().all()
    return strategies


@router.post("")
async def create_strategy(data: dict, session: AsyncSession = Depends(get_session)):
    strategy = Strategy(user_id=data.get("user_id", "default"), name=data.get("name", "New Strategy"))
    session.add(strategy)
    await session.commit()
    return strategy
```

---

## Phase 3: Autonomy (Weeks 13-18)

**Goal:** Self-improving strategies, pi-autoresearch, RLM integration, full Risk Manager system, paper trading.

**Key tasks (high-level, each will be expanded during Phase 3 execution):**

### Task 3.1: Hermes-Agent Orchestrator

- Integrate Hermes-Agent as the central state machine
- Implement memory system (ChromaDB recall/store)
- Build skill creation pipeline (LLM generates Python → containers → registers as tool)
- Implement self-correction loop
- Add watchdog trigger system

### Task 3.2: pi-autoresearch Integration

- Wrap pi-autoresearch as a Hermes-Agent sub-process
- Implement the research loop: hypothesis → code → TabPFN evaluation → Git commit/rollback
- Build experiment dashboard showing iteration history
- Add multi-objective optimization (NSGA-II) for strategy tuning

### Task 3.3: RLM (DSPy) Deep Archive Mining

- Integrate dspy.RLM for recursive archive scanning
- Build pipeline: massive unstructured data → programmatic filter → sub-agent analysis → structured alpha vector
- Implement linguistic change-point detection for narrative mining

### Task 3.4: Risk Manager — Full Strategy Template System

- Refactor Risk Manager from preset Kelly Criterion to full strategy template
- Add position sizing algorithms (dynamic sizing based on portfolio volatility)
- Implement drawdown protection, correlation hedging, portfolio rebalancing
- Add TabPFN quantile regression for VaR/Expected Shortfall
- Build risk dashboard showing real-time portfolio risk metrics

### Task 3.5: Paper Trading Environment

- Create simulated execution engine (matches Polymarket/Kalshi/Drift order books)
- Implement paper wallet system with virtual balance
- Build performance tracking with win rate, Sharpe, max drawdown
- Add strategy comparison tools

---

## Phase 4: Production (Weeks 19-24)

**Goal:** Production-hardened platform with real execution.

### Task 4.1: Rust Execution Engine Bridge

- Build Rust-based order execution service (using ethers-rs for blockchain interactions)
- Implement multi-platform order dispatcher (Polymarket/Kalshi/Drift)
- Add slippage calculator and gas fee optimizer (Toto-2 powered)
- Build transaction monitoring and confirmation system

### Task 4.2: Production Hardening

- Security audit (API key encryption, JWT hardening, rate limiting)
- Performance optimization (DuckDB query tuning, LanceDB index optimization)
- Horizontal scaling preparation (read replicas, connection pooling)
- Monitoring and alerting for system health

### Task 4.3: Agentic Search Pipeline

- Deploy SearXNG for multi-engine discovery
- Implement Scrapling fast parse gatekeeper
- Configure Camoufox + Playwright with Accessibility Tree extraction
- Build search orchestrator connecting all layers

### Task 4.4: Launch Preparation

- Documentation (user guide, API reference, strategy template docs)
- Onboarding flow polish
- Load testing
- Production deployment scripts

---

## Post-Launch (Future)

- WhatsApp bot integration
- Social media DM bots (TikTok, Instagram, Twitter/X)
- Chrome extension (injects UI into Polymarket/Kalshi and social media)
- Mobile app
- Public API for external developers
- Strategy marketplace
- llama.cpp for custom fine-tuned models

---

*End of Implementation Plan*
