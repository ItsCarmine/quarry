"""Quarry configuration — loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "QUARRY_", "env_file": ".env"}

    # LLM API keys
    anthropic_api_key: str = ""
    google_api_key: str = ""
    xai_api_key: str = ""
    moonshot_api_key: str = ""
    openai_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///quarry.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
