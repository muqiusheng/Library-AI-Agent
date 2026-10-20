from unittest.mock import Mock

import pytest

from app.db.models import User, UserRole
from app.services.admin_seed import seed_admin


def test_seed_admin_creates_hashed_admin() -> None:
    session = Mock()
    session.scalar.return_value = None

    result = seed_admin(
        session,
        student_no=" admin ",
        password="correct horse battery staple",
    )

    created = session.add.call_args.args[0]
    assert result.created is True
    assert created.student_no == "admin"
    assert created.role == UserRole.SUPER_ADMIN
    assert created.password_hash != "correct horse battery staple"
    session.commit.assert_called_once_with()


def test_seed_admin_is_idempotent() -> None:
    session = Mock()
    session.scalar.return_value = User(
        student_no="admin",
        password_hash="existing-hash",
        role=UserRole.SUPER_ADMIN,
    )

    result = seed_admin(
        session,
        student_no="admin",
        password="correct horse battery staple",
    )

    assert result.created is False
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_seed_admin_rejects_existing_student() -> None:
    session = Mock()
    session.scalar.return_value = User(
        student_no="student-1",
        password_hash="existing-hash",
        role=UserRole.STUDENT,
    )

    with pytest.raises(ValueError, match="non-admin"):
        seed_admin(
            session,
            student_no="student-1",
            password="correct horse battery staple",
        )
