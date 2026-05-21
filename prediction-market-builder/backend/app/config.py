from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./pmbuilder.db"
    postgres_url: str = "postgresql+asyncpg://pmuser:pmpass@localhost:5432/pmbuilder"
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
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
