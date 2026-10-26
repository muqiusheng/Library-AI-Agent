from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User, UserRole
from scripts.reset_admin_password import reset_super_admin_password


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_reset_changes_only_the_selected_super_admin_password(session: Session) -> None:
    target = User(
        student_no="admin",
        password_hash=hash_password("OldPassword123!"),
        role=UserRole.SUPER_ADMIN,
        display_name="Original name",
        is_active=False,
    )
    other = User(
        student_no="other-admin",
        password_hash=hash_password("OtherPass123!"),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    session.add_all([target, other])
    session.commit()

    assert reset_super_admin_password(session, " admin ", "NewPassword123!") == "admin"

    session.refresh(target)
    session.refresh(other)
    assert verify_password("NewPassword123!", target.password_hash)
    assert not verify_password("OldPassword123!", target.password_hash)
    assert target.role == UserRole.SUPER_ADMIN
    assert target.display_name == "Original name"
    assert target.is_active is False
    assert verify_password("OtherPass123!", other.password_hash)
    assert len(session.scalars(select(User)).all()) == 2


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.STUDENT, None])
def test_reset_never_creates_accounts_or_changes_other_roles(
    session: Session, role: UserRole | None
) -> None:
    if role is not None:
        session.add(User(student_no="admin", password_hash="unchanged", role=role))
        session.commit()

    with pytest.raises(ValueError, match="Super-admin account not found"):
        reset_super_admin_password(session, "admin", "NewPassword123!")

    users = session.scalars(select(User)).all()
    assert len(users) == (0 if role is None else 1)
    if users:
        assert users[0].password_hash == "unchanged"
        assert users[0].role == role


@pytest.mark.parametrize("password", ["short", "password-is-too-long"])
def test_invalid_password_leaves_existing_hash_unchanged(session: Session, password: str) -> None:
    user = User(student_no="admin", password_hash="unchanged", role=UserRole.SUPER_ADMIN)
    session.add(user)
    session.commit()

    with pytest.raises(ValueError, match="8-16"):
        reset_super_admin_password(session, "admin", password)

    session.refresh(user)
    assert user.password_hash == "unchanged"


def test_interactive_reset_confirms_password_without_printing_it(
    session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import app.db.session as database
    import scripts.reset_admin_password as recovery

    session.add(User(student_no="admin", password_hash="old", role=UserRole.SUPER_ADMIN))
    session.commit()
    answers = iter(["NewPassword123!", "NewPassword123!"])
    monkeypatch.setattr(recovery, "getpass", lambda _: next(answers))
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    assert recovery.main(["admin"]) == 0
    captured = capsys.readouterr()
    assert "Password updated for super-admin: admin" in captured.out
    assert "NewPassword123!" not in captured.out + captured.err
    user = session.scalar(select(User).where(User.student_no == "admin"))
    assert user is not None and verify_password("NewPassword123!", user.password_hash)


def test_mismatched_confirmation_cancels_reset(
    session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import scripts.reset_admin_password as recovery

    user = User(student_no="admin", password_hash="unchanged", role=UserRole.SUPER_ADMIN)
    session.add(user)
    session.commit()
    answers = iter(["NewPassword123!", "different"])
    monkeypatch.setattr(recovery, "getpass", lambda _: next(answers))

    assert recovery.main(["admin"]) == 1
    assert "do not match" in capsys.readouterr().err
    session.refresh(user)
    assert user.password_hash == "unchanged"


def test_no_hidden_terminal_cancels_reset(
    session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import warnings

    import scripts.reset_admin_password as recovery

    user = User(student_no="admin", password_hash="unchanged", role=UserRole.SUPER_ADMIN)
    session.add(user)
    session.commit()

    def unsafe_prompt(_: str) -> str:
        warnings.warn("Password input may be echoed.", recovery.GetPassWarning, stacklevel=1)
        raise AssertionError("Visible-input fallback must never be reached")

    monkeypatch.setattr(recovery, "getpass", unsafe_prompt)
    assert recovery.main(["admin"]) == 1
    assert "interactive terminal" in capsys.readouterr().err
    session.refresh(user)
    assert user.password_hash == "unchanged"
