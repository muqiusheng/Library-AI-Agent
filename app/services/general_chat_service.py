import json
from sqlalchemy.orm import Session

from app.db.models import Conversation, MessageRole, User
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider
from app.repositories.conversation_repository import ConversationRepository

from pydantic import BaseModel, Field

_LIBRARY_TERMS = (
    "书", "图书", "借阅", "借书", "还书", "馆藏", "可借", "索书号",
    "推荐", "阅读", "教材", "课程", "学习", "入门", "进阶", "作者",
    "出版社", "预约", "路线"
)

class IntentClassification(BaseModel):
    is_library_search: bool = Field(description="True if the user explicitly wants to search or get book recommendations. False if the user is chatting, asking a follow-up question, or if their intent is highly ambiguous (e.g. just a keyword like 'Java').")
    reason: str = Field(description="The reasoning behind the classification.")


class GeneralChatService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.provider = provider or DeepSeekProvider()

    async def is_library_request(self, conversation: Conversation, user: User, text: str) -> bool:
        normalized = text.casefold()
        fallback_result = any(term in normalized for term in _LIBRARY_TERMS)
        if not self.provider.available:
            return fallback_result

        history = ConversationRepository(self.session).messages(
            conversation.id, conversation.user_id
        )[-6:]
        
        from app.services.recommendation_service import RecommendationService
        profile_json = json.dumps(RecommendationService._profile_snapshot(user), ensure_ascii=False) if user.profile else "{}"
        
        system_prompt = (
            "Analyze the user's latest message and determine if it is a primary request to search/recommend books from the library. "
            "If the user is asking a follow-up question (e.g., 'Why did you recommend these books?'), asking for clarification, just chatting, "
            "or if the intent is highly ambiguous (e.g. just a single noun like 'Python' or 'Agent' without indicating they want books), set is_library_search to false. "
            "IMPORTANT: If the user explicitly asks for books, learning resources, or recommendations (e.g. '我想学langchain', '推荐关于xxx的书'), "
            "you MUST set is_library_search to true, regardless of whether it matches their profile or not."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            if msg.role in {MessageRole.USER, MessageRole.ASSISTANT}:
                messages.append({"role": msg.role.value, "content": msg.content})
        
        # In case the text is not yet saved in history or to emphasize the current query
        if not history or history[-1].content != text:
            messages.append({"role": "user", "content": text})
            
        try:
            classification = await self.provider.structured(messages, IntentClassification)
            return classification.is_library_search
        except Exception:
            return fallback_result

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
                    "当前系统没有实时网页搜索工具；被问到是否联网时必须如实说明。"
                    "不要在用户没有明确询问图书时强行推荐或检索图书。"
                    "【重要指令】如果用户的输入意图非常模糊（例如仅仅输入了“机器学习”或者“Java”等一个名词，不清楚是想找书还是了解概念），"
                    "请你主动向用户提供选项。例如：“您是希望我为您推荐关于'XXX'的馆藏图书，还是希望我为您解释'XXX'的基本概念呢？”并引导用户做出选择。"
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

    from collections.abc import AsyncIterator

    async def stream_answer(self, conversation: Conversation, user: User, question: str) -> AsyncIterator[str]:
        if not self.provider.available:
            yield self._fallback(question)
            return
        history = ConversationRepository(self.session).messages(
            conversation.id, conversation.user_id
        )[-12:]
        
        from app.services.recommendation_service import RecommendationService
        profile_json = json.dumps(RecommendationService._profile_snapshot(user), ensure_ascii=False) if user.profile else "{}"
        
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 BookPath AI（书途智引）的智能助手。直接、自然地回答用户当前问题。"
                    "你既可以回答一般知识与身份说明，也可以协助馆藏推荐。"
                    "当前系统没有实时网页搜索工具；被问到是否联网时必须如实说明。"
                    "不要在用户没有明确询问图书时强行推荐或检索图书。"
                    f"用户的当前画像信息：{profile_json}。"
                    "【重要指令】如果用户的输入意图非常模糊（例如仅仅输入了“机器学习”或者“Agent”等名词，或者可能存在多领域歧义且没有明确要书），"
                    "请你**主动向用户提供选项**。例如：“为了给您推荐最合适的 Agent 图书，请问您指的是人工智能方向的 AI Agent，还是网络代理？”并引导用户做出选择。"
                    "请使用 Markdown 格式来排版你的回答，使之结构清晰美观。"
                ),
            },
            *[
                {"role": message.role.value, "content": message.content}
                for message in history
                if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
            ],
        ]
        try:
            async for chunk in self.provider.stream_chat(messages, temperature=0.5):
                yield chunk
        except DeepSeekError:
            yield self._fallback(question)

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
