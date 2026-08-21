import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_SECRET_VALUES = {"", "change-me-in-production", "changeme", "secret", "password"}


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./pmbuilder.db"
    redis_url: str = ""
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
    rlm_archive_root: str = "./data/archives"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 10080
    rate_limit_per_minute: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be set (at least 32 characters). "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if self.secret_key.strip().lower() in _INSECURE_SECRET_VALUES:
            raise ValueError("SECRET_KEY must not be a placeholder value")
        if not self.encryption_key or len(self.encryption_key) < 16:
            raise ValueError(
                "ENCRYPTION_KEY must be set (at least 16 characters). "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self


settings = Settings()
