from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


class AdminOverview(BaseModel):
    users: int
    conversations: int
    recommendation_sets: int
    published_books: int
    published_holdings: int
    active_reservations: int
    import_batches: int
    pending_tags: int
    evaluation_samples: int


class AIProviderStatus(BaseModel):
    provider_id: str
    provider: str
    configured: bool
    base_url: str
    chat_model: str
    reasoning_model: str
    key_source: str


class AIProviderUpdate(BaseModel):
    provider_id: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    provider: str = Field(min_length=1, max_length=100)
    api_key: SecretStr | None = Field(default=None, max_length=500)
    base_url: str = Field(min_length=8, max_length=500)
    chat_model: str = Field(min_length=1, max_length=100)
    reasoning_model: str = Field(min_length=1, max_length=100)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("https://", "http://")):
            raise ValueError("API 地址必须以 http:// 或 https:// 开头")
        return normalized

    @field_validator("provider", "chat_model", "reasoning_model")
    @classmethod
    def normalize_model_name(cls, value: str) -> str:
        return value.strip()


class SystemSettingRead(BaseModel):
    key: str
    value: dict[str, Any] | list[Any] | str | int | float | bool
    description: str


class SystemSettingUpdate(BaseModel):
    value: dict[str, Any] | list[Any] | str | int | float | bool


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, dict[str, Any] | list[Any] | str | int | float | bool] = Field(
        min_length=1, max_length=10
    )
