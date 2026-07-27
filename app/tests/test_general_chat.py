from app.services.general_chat_service import GeneralChatService


def test_general_chat_intent_does_not_force_library_search() -> None:
    assert not GeneralChatService.is_library_request("你是谁")
    assert not GeneralChatService.is_library_request("你连网了没有")
    assert GeneralChatService.is_library_request("推荐几本 Java 入门书")


def test_general_chat_fallback_answers_identity_and_connectivity() -> None:
    assert "BookPath AI" in GeneralChatService._fallback("你是谁")
    assert "实时浏览互联网" in GeneralChatService._fallback("你连网了没有")
