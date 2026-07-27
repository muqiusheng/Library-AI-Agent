from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from secrets import choice
from string import ascii_uppercase, digits
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import SystemSetting

_SETTING_KEY = "registration_invite"
_ALPHABET = ascii_uppercase + digits


class RegistrationInviteService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def status(self) -> tuple[bool, datetime | None]:
        setting = self.session.get(SystemSetting, _SETTING_KEY)
        value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
        return bool(value.get("code_hash")), setting.updated_at if setting else None

    def generate(self, admin_id: UUID) -> tuple[str, datetime]:
        code = "".join(choice(_ALPHABET) for _ in range(12))
        value = {"code_hash": self._hash(code), "version": 1}
        setting = self.session.get(SystemSetting, _SETTING_KEY)
        if setting is None:
            setting = SystemSetting(
                key=_SETTING_KEY,
                value_json=value,
                description="全站固定注册邀请码摘要",
                updated_by_id=admin_id,
            )
            self.session.add(setting)
        else:
            setting.value_json = value
            setting.updated_by_id = admin_id
        self.session.commit()
        self.session.refresh(setting)
        return code, setting.updated_at

    def verify(self, supplied_code: str) -> bool:
        setting = self.session.get(SystemSetting, _SETTING_KEY)
        value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
        expected = str(value.get("code_hash") or "")
        return bool(expected) and compare_digest(self._hash(supplied_code), expected)

    @staticmethod
    def _hash(code: str) -> str:
        return sha256(code.encode("utf-8")).hexdigest()
