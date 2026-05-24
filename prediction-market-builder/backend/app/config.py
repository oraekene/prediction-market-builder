import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./pmbuilder.db"
    postgres_url: str = "postgresql+asyncpg://pmuser:CHANGE_ME@localhost:5432/pmbuilder"
    pgbouncer_url: str = "postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmbuilder"
    redis_url: str = "redis://redis:6379/0"
    duckdb_path: str = "./data/analytics.duckdb"
    lancedb_path: str = "./data/vectors"
    chromadb_path: str = "./data/memory"
    oracle_instance_id: str = ""
    cloudflare_api_token: str = ""
    claude_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    tabpfn_model: str = "tabpfn-2.5"
    tabpfn_mode: str = "local"
    market_regime_model: str = "heuristic-ensemble"
    secret_key: str = ""
    encryption_key: str = ""
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 10080
    rate_limit_per_minute: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()

if not settings.secret_key:
    logger.warning("SECRET_KEY is not set — JWT auth will fail at runtime. Set it in .env")
if settings.secret_key == "change-me-in-production":
    logger.warning("SECRET_KEY is still the placeholder 'change-me-in-production' — this is insecure")
