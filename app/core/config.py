"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings backed by environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SupportFlow AI"
    app_env: str = "development"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql+asyncpg://supportflow:supportflow@localhost:5432/supportflow"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "mock"
    llm_fallback_provider: str = "mock"
    llm_timeout_seconds: float = 30.0
    llm_max_repair_retries: int = 2
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    webhook_target_url: str = "https://example.com/webhooks/supportflow"
    webhook_hmac_secret: str = "change-me"
    webhook_dry_run: bool = True

    google_sheets_dry_run: bool = True
    google_sheets_spreadsheet_id: str = "demo-spreadsheet-id"
    google_sheets_credentials_json: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        """Return parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
