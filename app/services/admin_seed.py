from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import User, UserRole


@dataclass(frozen=True)
class SeedAdminResult:
    created: bool
    student_no: str


def bootstrap_admin(session: Session, settings: Settings) -> SeedAdminResult | None:
    """Initialize an empty installation; never change an existing installation."""
    if not settings.bootstrap_admin_enabled:
        return None
    # Serialize first startup across PostgreSQL workers, including different usernames.
    # The transaction lock is released on commit or when the caller closes the session.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(728416209)"))
    if session.scalar(select(User.id).limit(1)) is not None:
        return None
    student_no = settings.bootstrap_admin_student_no.strip()
    password = settings.bootstrap_admin_password.get_secret_value()
    if not student_no or len(student_no) > 64:
        raise ValueError("BOOTSTRAP_ADMIN_STUDENT_NO must contain 1-64 characters")
    if not 8 <= len(password) <= 16:
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must contain 8-16 characters")
    return seed_admin(session, student_no=student_no, password=password)


def seed_admin(
    session: Session,
    *,
    student_no: str,
    password: str,
    display_name: str = "系统管理员",
) -> SeedAdminResult:
    normalized_student_no = student_no.strip()
    if not normalized_student_no:
        raise ValueError("student_no cannot be empty")

    existing = session.scalar(select(User).where(User.student_no == normalized_student_no))
    if existing is not None:
        if existing.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise ValueError("student_no already belongs to a non-admin user")
        if existing.role == UserRole.ADMIN:
            existing.role = UserRole.SUPER_ADMIN
            session.commit()
        return SeedAdminResult(created=False, student_no=normalized_student_no)

    session.add(
        User(
            student_no=normalized_student_no,
            password_hash=hash_password(password),
            display_name=display_name.strip() or "系统管理员",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
    )
    session.commit()
    return SeedAdminResult(created=True, student_no=normalized_student_no)
