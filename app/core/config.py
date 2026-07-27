from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_frontend_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:5173",
        ]
    )

    database_url: str = "postgresql+psycopg://bookpath:bookpath@localhost:5432/bookpath"
    database_pool_size: int = 5
    database_max_overflow: int = 5

    chroma_persist_directory: Path = Path("data/chroma")
    chroma_collection_prefix: str = "bookpath"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    import_upload_directory: Path = Path("data/uploads")
    import_max_bytes: int = 64 * 1024 * 1024

    jwt_secret: str = Field(default="change-me-before-deployment-32chars", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 120

    registration_enabled: bool = True
    registration_invite_code: str = ""
    max_account_count: int = Field(default=50, ge=1, le=10000)

    rate_limit_enabled: bool = False
    rate_limit_register_per_minute: int = Field(default=5, ge=1, le=10000)
    rate_limit_login_per_minute: int = Field(default=10, ge=1, le=10000)
    rate_limit_ai_per_minute: int = Field(default=6, ge=1, le=10000)
    rate_limit_batch_tag_per_minute: int = Field(default=2, ge=1, le=10000)

    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_chat_model: str = "deepseek-v4-flash"
    deepseek_reasoning_model: str = "deepseek-v4-pro"
    llm_provider: str = "deepseek"

    @field_validator("app_frontend_origins")
    @classmethod
    def reject_wildcard_origins(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS origins must be explicit when credentials are enabled")
        return origins

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env != "production":
            return self
        if self.jwt_secret == "change-me-before-deployment-32chars" or "__" in self.jwt_secret:
            raise ValueError("JWT_SECRET must be generated for production")
        database_uses_placeholder = (
            "bookpath:bookpath@" in self.database_url
            or "__POSTGRES_PASSWORD__" in self.database_url
        )
        if database_uses_placeholder:
            raise ValueError("DATABASE_URL must use a generated PostgreSQL password in production")
        if not self.rate_limit_enabled:
            raise ValueError("RATE_LIMIT_ENABLED must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
