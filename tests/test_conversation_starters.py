from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.conversation import ConstraintRead, ConversationTask
from app.services.conversation_context_service import ConversationContext
from app.services.conversation_turn_service import ConversationTurnService


@pytest.mark.asyncio
@pytest.mark.parametrize("entry, expected", [
    ("入门一个新领域", "哪个领域"),
    ("找课程或考试参考书", "什么课程"),
    ("为项目或论文找资料", "什么主题"),
    ("按兴趣找几本好书", "什么话题"),
])
async def test_starters_ask_a_relevant_question_before_search(entry, expected):
    provider = MagicMock(available=True)
    provider.structured = AsyncMock()
    context = ConversationContext(ConversationTask(), ConstraintRead(), [], {})
    service = ConversationTurnService(provider)
    result = await service.resolve(context, entry)
    assert result.action == "clarify"
    assert expected in result.clarification
    provider.structured.assert_not_called()
    service.apply(context, result, entry)
    assert context.task.pending_question == entry
    followup = service.fallback(context, "中国现当代文学")
    assert followup.action == "recommend"
    assert followup.standalone_query == "中国现当代文学"


@pytest.mark.asyncio
async def test_new_general_entry_clears_previous_goal_and_filters():
    provider = MagicMock(available=False)
    context = ConversationContext(
        ConversationTask(topic="Python", request="Python教材"),
        ConstraintRead(difficulty="入门", only_available=True), [], {},
    )
    service = ConversationTurnService(provider)
    result = await service.resolve(context, "入门一个新领域")
    service.apply(context, result, "入门一个新领域")
    assert not context.task.request
    assert not context.task.topic
    assert context.constraints == ConstraintRead()
