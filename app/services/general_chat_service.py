from sqlalchemy.orm import Session

from app.db.models import Conversation, MessageRole
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider
from app.repositories.conversation_repository import ConversationRepository

_LIBRARY_TERMS = (
    "书",
    "图书",
    "借阅",
    "借书",
    "还书",
    "馆藏",
    "可借",
    "索书号",
    "推荐",
    "阅读",
    "教材",
    "课程",
    "学习",
    "入门",
    "进阶",
    "作者",
    "出版社",
    "预约",
)


class GeneralChatService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.provider = provider or DeepSeekProvider()

    @staticmethod
    def is_library_request(text: str) -> bool:
        normalized = text.casefold()
        return any(term in normalized for term in _LIBRARY_TERMS)

    async def answer(self, conversation: Conversation, question: str) -> str:
        if not self.provider.available:
            return self._fallback(question)
        history = ConversationRepository(self.session).messages(
            conversation.id, conversation.user_id
        )[-12:]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 BookPath AI（书途智引）的智能助手。直接、自然地回答用户当前问题。"
                    "你既可以回答一般知识与身份说明，也可以协助馆藏推荐。"
                    "当前系统没有实时网页搜索工具；被问到是否联网时必须如实说明："
                    "可以调用管理员配置的大模型 API 和本地馆藏数据库，但不能自行浏览实时互联网。"
                    "不要在用户没有询问图书时强行推荐或检索图书。"
                ),
            },
            *[
                {"role": message.role.value, "content": message.content}
                for message in history
                if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
            ],
        ]
        try:
            return await self.provider.chat(messages, temperature=0.5)
        except DeepSeekError:
            return self._fallback(question)

    @staticmethod
    def _fallback(question: str) -> str:
        if "谁" in question and any(word in question for word in ("你", "助手")):
            return (
                "我是 BookPath AI（书途智引），可以回答一般问题，"
                "也能结合本地图书馆馆藏帮你规划阅读与学习。"
            )
        if any(word in question for word in ("联网", "连网", "上网", "网络")):
            return (
                "我可以连接管理员配置的大模型 API 和本地馆藏数据库，"
                "但当前没有实时浏览互联网网页的能力。"
            )
        return (
            "我可以回答这个问题，但当前大模型 API 暂不可用。"
            "你可以稍后重试，或联系管理员检查模型配置。"
        )
