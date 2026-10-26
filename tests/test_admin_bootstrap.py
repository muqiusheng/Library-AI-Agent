from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.db.models import User, UserRole
from app.services.admin_seed import bootstrap_admin


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_empty_installation_can_login_with_initial_super_admin(session: Session) -> None:
    result = bootstrap_admin(session, Settings(_env_file=None))

    assert result is not None and result.created
    user = session.scalar(select(User).where(User.student_no == "admin"))
    assert user is not None
    assert user.role == UserRole.SUPER_ADMIN
    assert user.is_active
    assert verify_password("BookPath@123", user.password_hash)


@pytest.mark.parametrize("role", list(UserRole))
def test_existing_installation_is_unchanged_even_with_different_bootstrap_credentials(
    session: Session, role: UserRole
) -> None:
    user = User(
        student_no="existing-user",
        password_hash="existing-hash",
        display_name="Original name",
        role=role,
        is_active=False,
    )
    session.add(user)
    session.commit()

    result = bootstrap_admin(
        session,
        Settings(
            bootstrap_admin_student_no="new-admin",
            bootstrap_admin_password="invalid",
            _env_file=None,
        ),
    )

    assert result is None
    assert session.scalars(select(User)).all() == [user]
    session.refresh(user)
    assert user.student_no == "existing-user"
    assert user.password_hash == "existing-hash"
    assert user.display_name == "Original name"
    assert user.role == role
    assert user.is_active is False


def test_restart_preserves_changed_password(session: Session) -> None:
    settings = Settings(_env_file=None)
    bootstrap_admin(session, settings)
    user = session.scalar(select(User).where(User.student_no == "admin"))
    assert user is not None
    user.password_hash = hash_password("ChangedPass123!")
    session.commit()

    assert bootstrap_admin(session, settings) is None
    session.refresh(user)
    assert verify_password("ChangedPass123!", user.password_hash)
    assert not verify_password("BookPath@123", user.password_hash)


def test_empty_installation_accepts_custom_initial_credentials(session: Session) -> None:
    settings = Settings(
        bootstrap_admin_student_no=" owner ",
        bootstrap_admin_password="CustomPass123!",
        _env_file=None,
    )
    result = bootstrap_admin(session, settings)

    assert result is not None and result.student_no == "owner"
    user = session.scalar(select(User).where(User.student_no == "owner"))
    assert user is not None
    assert verify_password("CustomPass123!", user.password_hash)


def test_automatic_initialization_can_be_disabled(session: Session) -> None:
    result = bootstrap_admin(session, Settings(bootstrap_admin_enabled=False, _env_file=None))

    assert result is None
    assert session.scalar(select(User.id)) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"bootstrap_admin_password": "short"},
        {"bootstrap_admin_password": "password-is-too-long"},
        {"bootstrap_admin_student_no": "   "},
        {"bootstrap_admin_student_no": "a" * 65},
    ],
)
def test_invalid_initial_credentials_do_not_create_users(session: Session, overrides: dict) -> None:
    with pytest.raises(ValueError, match="BOOTSTRAP_ADMIN"):
        bootstrap_admin(session, Settings(**overrides, _env_file=None))
    assert session.scalar(select(User.id)) is None
