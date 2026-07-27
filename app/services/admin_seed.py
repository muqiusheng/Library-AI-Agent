from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User, UserRole


@dataclass(frozen=True)
class SeedAdminResult:
    created: bool
    student_no: str


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
