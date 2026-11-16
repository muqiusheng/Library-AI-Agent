from datetime import timedelta
from importlib import import_module
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.base import utc_now
from app.db.models import (
    Book,
    BookUserState,
    BookUserStateValue,
    DataVersion,
    DataVersionStatus,
    LearningPath,
    LearningPathBook,
    LearningPathStage,
    LearningPathStatus,
    ReadingInterest,
    ReadingInterestEvent,
    User,
)
from app.db.session import engine, get_db
from app.main import create_app
from app.services.engagement_service import EngagementService
from app.services.learning_path_service import LearningPathService
from app.services.reading_interest_service import ReadingInterestService


@pytest.fixture
def reading_db():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            version = DataVersion(
                name=f"interest-{uuid4()}",
                status=DataVersionStatus.PUBLISHED,
                published_at=utc_now() + timedelta(days=1),
            )
            users = [
                User(student_no=f"interest-{uuid4()}", password_hash="test", display_name="读者")
                for _ in range(2)
            ]
            session.add_all([version, *users])
            session.flush()
            books = [
                Book(
                    data_version_id=version.id,
                    title=f"图书{i}",
                    normalized_title=f"图书{i}",
                    source_fingerprint=uuid4().hex,
                )
                for i in range(3)
            ]
            session.add_all(books)
            session.commit()
            yield session, users, books
        transaction.rollback()


def add_path(session, user, books):
    path = LearningPath(
        user_id=user.id, title="学习计划", goal="学习", status=LearningPathStatus.DRAFT
    )
    session.add(path)
    session.flush()
    stage = LearningPathStage(
        path_id=path.id,
        position=1,
        title="阶段",
        objective="目标",
        duration_text="一周",
        completion_criteria="读完",
    )
    session.add(stage)
    session.flush()
    session.add_all(
        [
            LearningPathBook(
                stage_id=stage.id,
                book_id=b.id,
                position=i + 1,
                state=BookUserStateValue.NOT_STARTED,
            )
            for i, b in enumerate(books)
        ]
    )
    session.commit()
    return path, stage


def test_interest_toggle_idempotence_and_progress_independence(reading_db):
    db, users, books = reading_db
    service = ReadingInterestService(db)
    uid, bid = users[0].id, books[0].id
    EngagementService(db).set_book_state(uid, bid, BookUserStateValue.COMPLETED)
    assert service.set_interest(uid, bid, True)["heat_count"] == 1
    service.set_interest(uid, bid, True)
    assert (
        db.scalar(
            select(func.count())
            .select_from(ReadingInterestEvent)
            .where(ReadingInterestEvent.user_id.in_([u.id for u in users]))
        )
        == 1
    )
    result = service.set_interest(uid, bid, False)
    assert not result["wanted"] and result["heat_count"] == 1
    assert result["state"] == BookUserStateValue.COMPLETED
    assert service.mine(uid, 1, 20)["total"] == 0
    service.set_interest(uid, bid, True)
    assert service.ranking(uid, 30, 1, 20)["items"][0]["heat_count"] == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(ReadingInterestEvent)
            .where(ReadingInterestEvent.user_id.in_([u.id for u in users]))
        )
        == 2
    )
    service.set_interest(users[1].id, bid, True)
    assert service.statuses(uid, [bid])[0]["heat_count"] == 2
    assert service.mine(users[1].id, 1, 20)["total"] == 1


def test_rolling_windows_unique_people_and_rank_ties(reading_db, monkeypatch):
    db, users, books = reading_db
    now = utc_now()
    monkeypatch.setattr("app.services.reading_interest_service.utc_now", lambda: now)
    events = [(0, 0, 1), (0, 0, 2), (1, 0, 1), (0, 1, 1), (1, 1, 29), (0, 2, 30), (1, 2, 366)]
    db.add_all(
        [
            ReadingInterestEvent(
                user_id=users[u].id, book_id=books[b].id, created_at=now - timedelta(days=age)
            )
            for u, b, age in events
        ]
    )
    db.commit()
    service = ReadingInterestService(db)
    week = service.ranking(users[0].id, 7, 1, 20)
    assert [(r["rank"], r["heat_count"]) for r in week["items"]] == [(1, 2), (2, 1)]
    month = service.ranking(users[0].id, 30, 1, 20)
    assert [(r["rank"], r["heat_count"]) for r in month["items"]] == [(1, 2), (1, 2), (3, 1)]
    assert service.ranking(users[0].id, 365, 1, 20)["items"][-1]["heat_count"] == 1
    page1 = service.ranking(users[0].id, 30, 1, 1)["items"][0]
    page2 = service.ranking(users[0].id, 30, 2, 1)["items"][0]
    assert page1["book_id"] != page2["book_id"]
    assert page1["rank"] == page2["rank"] == 1


def test_progress_synchronizes_all_paths_and_accounts_are_isolated(reading_db):
    db, users, books = reading_db
    path1, stage1 = add_path(db, users[0], books[:2])
    path2, _ = add_path(db, users[0], books[:1])
    other, _ = add_path(db, users[1], books[:1])
    service = LearningPathService(db)
    service.update_book_state(path1.id, books[0].id, users[0].id, BookUserStateValue.COMPLETED)
    assert service.get_owned(path1.id, users[0].id).progress == 50
    assert service.get_owned(path2.id, users[0].id).progress == 100
    assert service.get_owned(other.id, users[1].id).progress == 0
    service.complete_stage(path1.id, stage1.id, users[0].id)
    assert service.get_owned(path1.id, users[0].id).progress == 100
    EngagementService(db).set_book_state(users[0].id, books[0].id, BookUserStateValue.NOT_STARTED)
    assert service.get_owned(path1.id, users[0].id).progress == 50
    assert service.get_owned(path2.id, users[0].id).status == LearningPathStatus.ACTIVE
    assert (
        db.scalar(
            select(func.count())
            .select_from(ReadingInterestEvent)
            .where(ReadingInterestEvent.user_id.in_([u.id for u in users]))
        )
        == 0
    )


def test_http_routes_authorization_validation_and_user_cap(reading_db):
    db, users, books = reading_db
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: users[0]
    with TestClient(app) as client:
        response = client.get("/api/v1/books/popular")
        for days in (7, 30, 365):
            assert client.get(f"/api/v1/books/popular?days={days}").status_code == 200
        assert response.status_code == 200  # Must precede /books/{book_id} UUID matching.
        assert response.json()["data"]["items"] == []
        assert client.get("/api/v1/admin/books/popular").status_code == 403
        assert client.get("/api/v1/books/popular?days=8").status_code == 422
        assert (
            client.put(f"/api/v1/user-books/{uuid4()}/interest", json={"wanted": True}).status_code
            == 404
        )
        bid = str(books[0].id)
        assert client.put(f"/api/v1/user-books/{bid}/interest", json={"wanted": True}).json()[
            "data"
        ]["wanted"]
        assert client.post("/api/v1/user-books/status", json={"book_ids": [bid]}).status_code == 200
        assert client.get("/api/v1/user-books/wanted").json()["data"]["total"] == 1
        users[0].role = "admin"
        db.commit()
        user_items = client.get("/api/v1/books/popular").json()["data"]["items"]
        admin_items = client.get("/api/v1/admin/books/popular").json()["data"]["items"]
        assert user_items == admin_items
        app.dependency_overrides.pop(get_current_user)
        assert client.get("/api/v1/books/popular").status_code == 401


def test_migration_preserves_interest_without_inventing_heat(reading_db):
    db, users, books = reading_db
    path, _ = add_path(db, users[0], books[:2])
    uid, bid = users[0].id, books[0].id
    db.add(BookUserState(user_id=uid, book_id=bid, state=BookUserStateValue.NOT_STARTED))
    db.commit()
    migration = import_module("app.db.migrations.versions.a74d192f0b31_reading_interest")
    connection = db.connection()
    with Operations.context(MigrationContext.configure(connection)):
        migration.downgrade()
        connection.execute(
            text("UPDATE learning_path_books SET state = 'completed' WHERE book_id = :b"),
            {"b": bid},
        )
        migration.upgrade()
    db.expire_all()
    interest = db.get(ReadingInterest, (uid, bid))
    assert interest.active
    assert db.get(BookUserState, (uid, bid)).state == BookUserStateValue.COMPLETED
    assert db.get(LearningPath, path.id).progress == 50
    assert (
        db.scalar(
            select(func.count())
            .select_from(ReadingInterestEvent)
            .where(ReadingInterestEvent.user_id.in_([u.id for u in users]))
        )
        == 0
    )


def test_new_learning_path_inherits_personal_progress(reading_db):
    from app.db.models import Conversation, RecommendationItem, RecommendationSet

    db, users, books = reading_db
    uid = users[0].id
    conversation = Conversation(user_id=uid, title="测试推荐")
    db.add(conversation)
    db.flush()
    recommendation = RecommendationSet(
        user_id=uid,
        conversation_id=conversation.id,
        query="学习",
        profile_snapshot={},
        constraints_snapshot={},
    )
    db.add(recommendation)
    db.flush()
    for i, book in enumerate(books[:2]):
        db.add(
            RecommendationItem(
                set_id=recommendation.id,
                book_id=book.id,
                rank=i + 1,
                total_score=80,
                goal_score=80,
                difficulty_score=80,
                major_score=80,
                interest_score=80,
                semantic_score=80,
                availability_score=80,
                reason="适合",
                reason_source="rule",
            )
        )
    db.commit()
    EngagementService(db).set_book_state(uid, books[0].id, BookUserStateValue.COMPLETED)
    path = LearningPathService(db).create_from_recommendation(uid, recommendation.id, None)
    assert path.progress == 50
    assert path.status == LearningPathStatus.ACTIVE
    states = {b.book_id: b.state for s in path.stages for b in s.books}
    assert states[books[0].id] == BookUserStateValue.COMPLETED
    assert states[books[1].id] == BookUserStateValue.NOT_STARTED


def test_ranking_public_cap_and_admin_pagination(reading_db):
    db, users, books = reading_db
    added = [
        Book(
            data_version_id=books[0].data_version_id,
            title=f"分页图书{i}",
            normalized_title=f"分页图书{i}",
            source_fingerprint=uuid4().hex,
        )
        for i in range(24)
    ]
    db.add_all(added)
    db.flush()
    db.add_all([ReadingInterestEvent(user_id=users[0].id, book_id=b.id) for b in added])
    db.commit()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: users[0]
    with TestClient(app) as client:
        public = client.get("/api/v1/books/popular?days=30").json()["data"]
        assert len(public["items"]) == 20
        assert public["total"] == 24
        users[0].role = "admin"
        db.commit()
        second = client.get("/api/v1/admin/books/popular?days=30&page=2").json()["data"]
        assert len(second["items"]) == 4
        assert all(row["rank"] == 1 for row in second["items"])
        assert not (
            {row["book_id"] for row in public["items"]}
            & {row["book_id"] for row in second["items"]}
        )
