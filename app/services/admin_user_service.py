from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.schemas.admin_users import AdminCreateRequest, ManagedUserRead, ManagedUserUpdate


class AdminUserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_users(self, query: str | None = None) -> list[ManagedUserRead]:
        statement = (
            select(User).options(selectinload(User.profile)).order_by(User.created_at.desc())
        )
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(User.student_no.ilike(pattern), User.display_name.ilike(pattern))
            )
        return [self._read(user) for user in self.session.scalars(statement)]

    def create_admin(self, payload: AdminCreateRequest) -> ManagedUserRead:
        student_no = payload.student_no.strip()
        existing = self.session.scalar(select(User).where(User.student_no == student_no))
        if existing:
            raise AppError(status_code=409, code="STUDENT_NO_EXISTS", message="该账号已存在")
        user = User(
            student_no=student_no,
            display_name=payload.display_name.strip() if payload.display_name else None,
            password_hash=hash_password(payload.password.get_secret_value()),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return self._read(user)

    def update_user(
        self, user_id: UUID, payload: ManagedUserUpdate, current_admin: User
    ) -> ManagedUserRead:
        user = self._get(user_id)
        if user.role == UserRole.SUPER_ADMIN and (
            payload.role is not None or payload.is_active is not None
        ):
            raise AppError(
                status_code=409,
                code="SUPER_ADMIN_PROTECTED",
                message="超级管理员角色和状态不可修改",
            )
        if user.id == current_admin.id and payload.is_active is False:
            raise AppError(
                status_code=409,
                code="SELF_DEACTIVATION_FORBIDDEN",
                message="不能停用当前登录账号",
            )
        if "display_name" in payload.model_fields_set:
            user.display_name = payload.display_name.strip() if payload.display_name else None
        if payload.role is not None:
            user.role = UserRole(payload.role)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        self.session.commit()
        return self._read(user)

    def reset_password(self, user_id: UUID, password: str) -> ManagedUserRead:
        user = self._get(user_id)
        user.password_hash = hash_password(password)
        self.session.commit()
        return self._read(user)

    def _get(self, user_id: UUID) -> User:
        user = self.session.scalar(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        if user is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="用户不存在")
        return user

    @staticmethod
    def _read(user: User) -> ManagedUserRead:
        return ManagedUserRead(
            id=user.id,
            student_no=user.student_no,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            major=user.profile.major if user.profile else None,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
