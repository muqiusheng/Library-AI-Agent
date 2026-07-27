from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import (
    Book,
    BookTag,
    Conversation,
    DataVersion,
    DataVersionStatus,
    EvaluationRecord,
    Holding,
    ImportBatch,
    RecommendationSet,
    Reservation,
    ReservationStatus,
    ReviewStatus,
    SystemSetting,
    User,
)
from app.schemas.admin_system import (
    AdminOverview,
    AIProviderStatus,
    AIProviderUpdate,
    SystemSettingRead,
)

_AI_PROVIDER_KEY = "ai_provider_config"

_DEFAULTS: dict[str, tuple[Any, str]] = {
    "recommendation_top_k": (5, "每轮返回的推荐图书数量"),
    "ai_tag_batch_size": (50, "管理员单次 AI 标签处理书目上限"),
    "reservation_expiry_days": (3, "模拟预约默认保留天数"),
    "recommendation_weights": (
        {
            "goal": 0.30,
            "difficulty": 0.20,
            "major": 0.15,
            "interest": 0.10,
            "semantic": 0.15,
            "availability": 0.10,
        },
        "推荐六维评分权重，总和必须为 1",
    ),
}


class SystemConfigService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def overview(self) -> AdminOverview:
        published_id = self.session.scalar(
            select(DataVersion.id)
            .where(DataVersion.status == DataVersionStatus.PUBLISHED)
            .order_by(DataVersion.published_at.desc())
            .limit(1)
        )

        def count(model, *conditions) -> int:
            return int(
                self.session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
            )

        return AdminOverview(
            users=count(User),
            conversations=count(Conversation),
            recommendation_sets=count(RecommendationSet),
            published_books=count(Book, Book.data_version_id == published_id)
            if published_id
            else 0,
            published_holdings=(
                count(
                    Holding,
                    Holding.book_id.in_(
                        select(Book.id).where(Book.data_version_id == published_id)
                    ),
                )
                if published_id
                else 0
            ),
            active_reservations=count(Reservation, Reservation.status == ReservationStatus.ACTIVE),
            import_batches=count(ImportBatch),
            pending_tags=count(BookTag, BookTag.review_status == ReviewStatus.PENDING),
            evaluation_samples=count(EvaluationRecord),
        )

    def get_ai_provider_status(self) -> AIProviderStatus:
        settings = get_settings()
        stored = self.session.get(SystemSetting, _AI_PROVIDER_KEY)
        value = stored.value_json if stored and isinstance(stored.value_json, dict) else {}
        provider_id = str(value.get("provider_id") or settings.llm_provider)
        provider = str(value.get("provider") or "DeepSeek")
        api_key = str(value.get("api_key") or settings.deepseek_api_key)
        base_url = str(value.get("base_url") or settings.deepseek_base_url)
        chat_model = str(value.get("chat_model") or settings.deepseek_chat_model)
        reasoning_model = str(value.get("reasoning_model") or settings.deepseek_reasoning_model)
        self._apply_ai_provider(api_key, base_url, chat_model, reasoning_model, provider_id)
        return AIProviderStatus(
            provider_id=provider_id,
            provider=provider,
            configured=bool(api_key),
            base_url=base_url,
            chat_model=chat_model,
            reasoning_model=reasoning_model,
            key_source="管理员后台安全保存（密钥不会通过接口返回）"
            if value.get("api_key")
            else "环境变量 DEEPSEEK_API_KEY（密钥不会通过接口返回）",
        )

    def update_ai_provider(
        self, payload: AIProviderUpdate, admin_id: UUID
    ) -> AIProviderStatus:
        settings = get_settings()
        stored = self.session.get(SystemSetting, _AI_PROVIDER_KEY)
        previous = stored.value_json if stored and isinstance(stored.value_json, dict) else {}
        submitted_key = payload.api_key.get_secret_value().strip() if payload.api_key else ""
        previous_provider = str(previous.get("provider_id") or settings.llm_provider)
        if submitted_key:
            api_key = submitted_key
        elif payload.provider_id == previous_provider:
            api_key = str(previous.get("api_key") or settings.deepseek_api_key)
        elif payload.provider_id == "deepseek":
            api_key = settings.deepseek_api_key
        else:
            api_key = ""
        value = {
            "provider_id": payload.provider_id,
            "provider": payload.provider,
            "api_key": api_key,
            "base_url": payload.base_url,
            "chat_model": payload.chat_model,
            "reasoning_model": payload.reasoning_model,
        }
        if stored is None:
            stored = SystemSetting(
                key=_AI_PROVIDER_KEY,
                value_json=value,
                description="DeepSeek API 运行配置（密钥不通过管理接口返回）",
                updated_by_id=admin_id,
            )
            self.session.add(stored)
        else:
            stored.value_json = value
            stored.updated_by_id = admin_id
        self.session.commit()
        self._apply_ai_provider(
            api_key,
            payload.base_url,
            payload.chat_model,
            payload.reasoning_model,
            payload.provider_id,
        )
        return self.get_ai_provider_status()

    @staticmethod
    def _apply_ai_provider(
        api_key: str,
        base_url: str,
        chat_model: str,
        reasoning_model: str,
        provider_id: str | None = None,
    ) -> None:
        settings = get_settings()
        settings.deepseek_api_key = api_key
        settings.deepseek_base_url = base_url
        settings.deepseek_chat_model = chat_model
        settings.deepseek_reasoning_model = reasoning_model
        if provider_id:
            settings.llm_provider = provider_id

    def list_settings(self) -> list[SystemSettingRead]:
        stored = {
            item.key: item
            for item in self.session.scalars(
                select(SystemSetting).where(SystemSetting.key.in_(_DEFAULTS))
            )
        }
        return [
            SystemSettingRead(
                key=key,
                value=stored[key].value_json if key in stored else default,
                description=description,
            )
            for key, (default, description) in _DEFAULTS.items()
        ]

    def get(self, key: str) -> Any:
        if key not in _DEFAULTS:
            raise AppError(
                status_code=400, code="SETTING_NOT_ALLOWED", message="配置项不在白名单中"
            )
        stored = self.session.get(SystemSetting, key)
        return stored.value_json if stored else _DEFAULTS[key][0]

    def update_many(self, values: dict[str, Any], admin_id: UUID) -> list[SystemSettingRead]:
        unknown = set(values) - set(_DEFAULTS)
        if unknown:
            raise AppError(
                status_code=400, code="SETTING_NOT_ALLOWED", message="包含非白名单配置项"
            )
        for key, value in values.items():
            normalized = self._validate(key, value)
            setting = self.session.get(SystemSetting, key)
            if setting is None:
                setting = SystemSetting(
                    key=key,
                    value_json=normalized,
                    description=_DEFAULTS[key][1],
                    updated_by_id=admin_id,
                )
                self.session.add(setting)
            else:
                setting.value_json = normalized
                setting.updated_by_id = admin_id
        self.session.commit()
        return self.list_settings()

    @staticmethod
    def _validate(key: str, value: Any) -> Any:
        ranges = {
            "recommendation_top_k": (1, 10),
            "ai_tag_batch_size": (1, 100),
            "reservation_expiry_days": (1, 14),
        }
        if key in ranges:
            minimum, maximum = ranges[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise AppError(
                    status_code=422, code="SETTING_VALUE_INVALID", message="配置值超出允许范围"
                )
            return value
        if key == "recommendation_weights":
            allowed = {"goal", "difficulty", "major", "interest", "semantic", "availability"}
            if not isinstance(value, dict) or set(value) != allowed:
                raise AppError(
                    status_code=422, code="SETTING_VALUE_INVALID", message="推荐权重字段不完整"
                )
            normalized = {name: float(weight) for name, weight in value.items()}
            if (
                any(weight < 0 or weight > 1 for weight in normalized.values())
                or abs(sum(normalized.values()) - 1) > 0.001
            ):
                raise AppError(
                    status_code=422,
                    code="SETTING_VALUE_INVALID",
                    message="推荐权重必须在 0–1 且总和为 1",
                )
            return normalized
        return value
