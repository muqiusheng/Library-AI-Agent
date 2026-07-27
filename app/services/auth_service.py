from datetime import UTC, datetime
from secrets import compare_digest

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.db.models import User, UserProfile, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.services.registration_invite_service import RegistrationInviteService

_DUMMY_PASSWORD_HASH = hash_password("bookpath-dummy-password")


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register(self, payload: RegisterRequest) -> User:
        settings = get_settings()
        if not settings.registration_enabled:
            raise AppError(status_code=403, code="REGISTRATION_DISABLED", message="当前未开放注册")
        supplied_code = (
            payload.registration_code.get_secret_value() if payload.registration_code else ""
        )
        invite_service = RegistrationInviteService(self.session)
        invite_configured, _ = invite_service.status()
        valid_invite = (
            compare_digest(supplied_code, settings.registration_invite_code)
            if settings.registration_invite_code
            else invite_service.verify(supplied_code)
        )
        if (settings.registration_invite_code or invite_configured) and not valid_invite:
            raise AppError(
                status_code=403,
                code="INVALID_REGISTRATION_CODE",
                message="邀请码无效",
            )
        account_count = self.session.scalar(select(func.count()).select_from(User)) or 0
        if account_count >= settings.max_account_count:
            raise AppError(
                status_code=403,
                code="ACCOUNT_LIMIT_REACHED",
                message="账户数量已达到上限",
            )
        student_no = payload.student_no.strip()
        if self.users.get_by_student_no(student_no) is not None:
            raise AppError(
                status_code=409,
                code="STUDENT_NO_EXISTS",
                message="该学号已注册",
            )

        profile_data = payload.profile.model_dump()
        user = User(
            student_no=student_no,
            password_hash=hash_password(payload.password.get_secret_value()),
            display_name=payload.display_name.strip() if payload.display_name else None,
            role=UserRole.STUDENT,
            is_active=True,
        )
        user.profile = UserProfile(**profile_data)
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                status_code=409,
                code="STUDENT_NO_EXISTS",
                message="该学号已注册",
            ) from exc
        return self.users.get_by_id(user.id, with_profile=True) or user

    def authenticate(self, student_no: str, password: str) -> User:
        user = self.users.get_by_student_no(student_no.strip(), with_profile=True)
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_valid = verify_password(password, password_hash)
        if user is None or not password_valid:
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="学号或密码错误",
            )
        if not user.is_active:
            raise AppError(
                status_code=403,
                code="USER_DISABLED",
                message="账户已停用",
            )
        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        return user
