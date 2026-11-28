import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from openpyxl import Workbook
from sqlalchemy import insert, select
from test_conversation_memory import memory_session as memory_session

from app.core.content_orientation import (
    orientation_score,
    parse_orientation,
    recommendation_weights,
)
from app.db.models import Book, DataVersion, Holding, ImportIssue, RecommendationItem
from app.pipelines.content_orientation import backfill_content_orientation
from app.pipelines.import_excel import ExcelLibraryImporter
from app.pipelines.index import BookIndexService
from app.schemas.conversation import LearningNeedState
from app.services.need_clarification_service import NeedClarificationService, NeedExtraction
from app.services.recommendation_service import RecommendationService, RerankOutput
from app.services.system_config_service import SystemConfigService


@pytest.mark.parametrize(
    "label,code", [("偏理论", "theory"), ("理论实践结合", "balanced"), ("偏实践", "practice")]
)
def test_dataset_values(label, code):
    assert parse_orientation(" " + label + " ") == code
    assert parse_orientation(code) == code


def test_unknown_is_not_balanced():
    assert parse_orientation(None) is None
    with pytest.raises(ValueError):
        parse_orientation("理论或实践")
    assert orientation_score("any", "balanced") is None
    assert orientation_score(None, "theory") is None
    assert orientation_score("practice", None) is None
    assert (
        orientation_score("practice", "practice")
        > orientation_score("practice", "balanced")
        > orientation_score("practice", "theory")
    )
    assert orientation_score("balanced", "balanced") > orientation_score("balanced", "practice")


def test_legacy_weight_config_keeps_proportions():
    old = {
        "goal": 0.3,
        "difficulty": 0.2,
        "major": 0.15,
        "interest": 0.1,
        "semantic": 0.15,
        "availability": 0.1,
    }
    upgraded = SystemConfigService._validate("recommendation_weights", old)
    assert upgraded["orientation"] == 0.1
    assert sum(upgraded.values()) == pytest.approx(1)
    assert upgraded["goal"] / upgraded["difficulty"] == pytest.approx(1.5)
    assert recommendation_weights(upgraded) == upgraded


def test_backfill_is_idempotent_and_rejects_copy_conflicts(memory_session):
    session, _, _ = memory_session
    version = session.scalar(select(DataVersion))
    book = session.scalar(select(Book))
    book.holdings[0].raw_payload = {"内容取向": "偏实践"}
    session.commit()
    assert backfill_content_orientation(session, version.id)["updated"] == 1
    assert book.content_orientation == "practice"
    assert backfill_content_orientation(session, version.id)["updated"] == 0
    book.holdings.append(
        Holding(
            source_row_no=2,
            book_status="available",
            circulation_status="lendable",
            raw_payload={"内容取向": "偏理论"},
        )
    )
    session.commit()
    with pytest.raises(ValueError, match="不一致"):
        backfill_content_orientation(session, version.id)
    assert book.content_orientation == "practice"


def test_import_preserves_labels_and_reports_conflicting_or_invalid_values(
    memory_session, tmp_path
):
    session, _, _ = memory_session

    class TestImporter(ExcelLibraryImporter):
        def _copy_rows(self, table, columns, rows):
            model = {"books": Book, "holdings": Holding, "import_issues": ImportIssue}[table]
            self.session.execute(insert(model), rows)

    wb = Workbook()
    sheet = wb.active
    sheet.append(
        ["序号", "题名", "索书号", "馆藏地", "所在地", "书刊状态", "流通状态", "ISBN", "内容取向"]
    )
    for i, title, label in [
        (1, "冲突书", "偏理论"),
        (2, "冲突书", "偏实践"),
        (3, "完整书", None),
        (4, "完整书", "理论实践结合"),
        (5, "异常书", "随便"),
    ]:
        sheet.append([i, title, f"TP/{i}", "测试馆", "测试馆", "可借", "在架", None, label])
    path = tmp_path / "orientation.xlsx"
    wb.save(path)
    wb.close()
    report = TestImporter(session).import_file(path, publish=False)
    books = {
        b.title: b
        for b in session.scalars(
            select(Book).where(Book.data_version_id == UUID(report.data_version_id))
        )
    }
    assert books["冲突书"].content_orientation is None
    assert books["完整书"].content_orientation == "balanced"
    assert books["异常书"].content_orientation is None
    assert report.issues == 2
    assert report.content_orientation_distribution == {"未标注": 2, "理论实践结合": 1}
    assert {h.raw_payload.get("内容取向") for h in books["冲突书"].holdings} == {"偏理论", "偏实践"}


@pytest.mark.asyncio
async def test_preference_changes_rank_and_persisted_score_without_forcing_filter(memory_session):
    session, user, conversation = memory_session
    books = list(session.scalars(select(Book)).all())[:3]
    for book, value in zip(books, ["theory", "balanced", "practice"], strict=True):
        book.title = "Java 教程"
        book.description = "Java 技术知识"
        book.content_orientation = value
    session.commit()
    service = RecommendationService(session)
    service.library.search_candidates = lambda query, **kwargs: books
    for preference in ["theory", "balanced", "practice"]:
        result = await service.recommend(
            user=user,
            conversation_id=conversation.id,
            query="Java",
            constraints={"learning_need": {"topic": "Java", "content_preference": preference}},
        )
        assert len(result.items) == 3
        assert result.items[0].content_orientation == preference
        assert result.items[0].scores.orientation == 100
        restored = service.get_set(result.id, user.id)
        assert restored.items[0].scores.orientation == 100
    historical = session.scalar(
        select(RecommendationItem)
        .where(RecommendationItem.set_id == result.id)
        .order_by(RecommendationItem.rank)
    )
    total = float(historical.total_score)
    historical.orientation_score = None
    session.commit()
    restored = service.get_set(result.id, user.id)
    assert restored.items[0].scores.orientation is None
    assert restored.items[0].total_score == total
    result = await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Java",
        constraints={"learning_need": {"topic": "Java", "content_preference": "any"}},
    )
    assert all(card.scores.orientation is None for card in result.items)
    result = await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Java",
        constraints={
            "learning_need": {
                "topic": "Java",
                "content_preference": "practice",
                "orientation_required": True,
            }
        },
    )
    assert [card.content_orientation for card in result.items] == ["practice"]


def test_unknown_and_old_scores_remain_neutral(memory_session):
    session, user, _ = memory_session
    book = session.scalar(select(Book))
    service = RecommendationService(session)
    original = service._score(book, "Java", user)
    book.content_orientation = "practice"
    unrestricted = service._score(book, "Java", user, content_preference="any")
    assert original.total == unrestricted.total
    assert unrestricted.scores.orientation is None


@pytest.mark.asyncio
async def test_orientation_is_in_index_and_model_payload(memory_session):
    session, user, _ = memory_session
    book = session.scalar(select(Book))
    book.content_orientation = "practice"
    assert "内容取向：偏实践" in BookIndexService.document_for(book)
    service = RecommendationService(session)
    provider = SimpleNamespace(
        available=True, structured=AsyncMock(return_value=RerankOutput(items=[]))
    )
    service.llm = provider
    candidate = service._score(book, "Java", user, content_preference="practice")
    await service._rerank("Java", [candidate], content_preference="practice")
    messages, _ = provider.structured.call_args.args
    assert "content_preference：practice" in messages[1]["content"]
    payload = json.loads(messages[1]["content"].split("候选：")[1])
    assert payload[0]["content_orientation"] == "practice"
    assert payload[0]["orientation_match"] == 100


def test_any_clears_strict_requirement():
    state = LearningNeedState(
        topic="数据库", content_preference="practice", orientation_required=True
    )
    result = NeedClarificationService._merge(state, NeedExtraction(content_preference="any"))
    assert result.orientation_required is False
