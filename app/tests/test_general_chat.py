import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.general_chat_service import GeneralChatService, IntentClassification

@pytest.mark.asyncio
async def test_general_chat_intent_does_not_force_library_search() -> None:
    # Mock dependencies
    provider = MagicMock()
    provider.available = True
    provider.structured = AsyncMock()
    
    session = MagicMock()
    conversation = MagicMock()
    conversation.id = "conv_1"
    conversation.user_id = "user_1"
    
    chat_service = GeneralChatService(session, provider)
    
    # 1. 闲聊场景
    provider.structured.return_value = IntentClassification(is_library_search=False, reason="chat")
    assert not await chat_service.is_library_request(conversation, "你是谁")
    
    # 2. 也是闲聊
    provider.structured.return_value = IntentClassification(is_library_search=False, reason="chat")
    assert not await chat_service.is_library_request(conversation, "你连网了没有")
    
    # 3. 找书场景
    provider.structured.return_value = IntentClassification(is_library_search=True, reason="search")
    assert await chat_service.is_library_request(conversation, "推荐几本 Java 入门书")
    
    # 4. 追问场景 (针对刚才的内容提问)
    provider.structured.return_value = IntentClassification(is_library_search=False, reason="follow up")
    assert not await chat_service.is_library_request(conversation, "为什么推荐上面这些书")

def test_general_chat_fallback_answers_identity_and_connectivity() -> None:
    assert "BookPath AI" in GeneralChatService._fallback("你是谁")
    assert "实时浏览互联网" in GeneralChatService._fallback("你连网了没有")

