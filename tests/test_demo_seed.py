from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.models import Conversation, User
from app.db.session import engine
from app.services.demo_seed import DEMO_ACCOUNTS, reset_demo_activity, seed_demo_accounts


@pytest.fixture
def demo_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_demo_seed_is_idempotent_and_reset_preserves_accounts(demo_session: Session) -> None:
    # Remove persistent demo accounts if a developer seeded them before running tests;
    # the surrounding transaction restores the original database state.
    existing = list(
        demo_session.scalars(
            select(User).where(
                User.student_no.in_([value["student_no"] for value in DEMO_ACCOUNTS])
            )
        )
    )
    for user in existing:
        demo_session.delete(user)
    demo_session.commit()

    first = seed_demo_accounts(demo_session, "demo password for local test")
    second = seed_demo_accounts(demo_session, "must not replace existing password")
    assert len(first.created) == 2
    assert len(second.existing) == 2

    user = demo_session.scalar(select(User).where(User.student_no == "demo_java"))
    assert user is not None
    assert verify_password("demo password for local test", user.password_hash)
    demo_session.add(Conversation(user_id=user.id, title="临时演示会话"))
    demo_session.commit()

    assert reset_demo_activity(demo_session) == 2
    assert demo_session.scalar(select(func.count(User.id)).where(User.id == user.id)) == 1
    assert (
        demo_session.scalar(
            select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
        )
        == 0
    )
