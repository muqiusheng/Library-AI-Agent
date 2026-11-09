import logging
import re

from app.integrations.llm.deepseek import DeepSeekProvider
from app.schemas.conversation import ConstraintRead, ConversationTask, TurnResolution
from app.services.conversation_context_service import ConversationContext

logger = logging.getLogger(__name__)

_STARTER_QUESTIONS = {
    "入门一个新领域": "你想学习哪个领域？之前接触过吗？",
    "找课程或考试参考书": "你正在学习什么课程，或准备什么考试？",
    "为项目或论文找资料": "你的项目或论文是什么主题？目前需要解决什么问题？",
    "按兴趣找几本好书": "你最近对什么话题感兴趣？也可以告诉我一本喜欢的书。",
}

_PROMPT = """你负责解析图书馆连续对话，只返回符合结构的结果。
action: recommend=首次或新主题荐书；refine=调整、换书、补充条件；
explain=解释已推荐图书；availability=查询指定图书可借状态；chat=普通知识问答；
clarify=缺少任务主题或指代不明确，需要澄清。
结合当前任务、历史和本轮输入，补全 standalone_query，保留原主题及用户仍有效的要求。
“简单一点、换一批、不要第一本”等属于 refine，不能因省略书名而转为闲聊。
只有确实切换主题才设 new_topic；“其他要求不变”设 keep_constraints。
target_rank 为最近推荐列表中的位置（从1开始）；无法唯一确定时澄清，禁止猜测。
standalone_query 只保留主题和学习目标，不夹带难度、排除、可借等筛选条件，筛选条件放 constraints。
constraints 只填写用户本轮明确变更的字段，不要复制旧值；撤销难度用 null，撤销排除用 []。
不要把帮朋友找书或本次条件写成长期画像。explain 和 availability 不重新推荐。
澄清回复应结合 pending_question 理解。普通知识问答不要转成荐书。
澄清每轮只问最关键的一两个问题；历史中已明确的学习基础与目标不重复询问。
"""


class ConversationTurnService:
    def __init__(self, provider: DeepSeekProvider | None = None) -> None:
        self.provider = provider or DeepSeekProvider()

    async def resolve(self, context: ConversationContext, text: str) -> TurnResolution:
        if text.strip() in _STARTER_QUESTIONS:
            return TurnResolution(
                action="clarify", new_topic=True,
                clarification=_STARTER_QUESTIONS[text.strip()],
            )
        result = self.fallback(context, text)
        if self.provider.available:
            try:
                result = await self.provider.structured(
                    [
                        {
                            "role": "system",
                            "content": _PROMPT + "\n当前上下文：" + context.prompt(),
                        },
                        *context.history,
                        *(
                            []
                            if context.history
                            and context.history[-1]["role"] == "user"
                            and context.history[-1]["content"] == text
                            else [{"role": "user", "content": text}]
                        ),
                    ],
                    TurnResolution,
                )
            except Exception:
                logger.warning(
                    "Turn resolution failed; using local conversation rules", exc_info=True
                )
        # Explicit ordinal references are resolved by the server, never invented by the model.
        rank = self.rank(text)
        if rank is not None:
            result.target_rank = rank
        if result.action == "refine" and result.target_rank is None and "换一本" in text:
            books = context.recommendation.items if context.recommendation else []
            result.target_rank = next(
                (
                    i + 1
                    for i, book in enumerate(books)
                    if book.book_id == context.task.focused_book_id or book.title in text
                ),
                None,
            )
            if result.target_rank is None and len(books) != 1:
                result.action = "clarify"
                result.clarification = "你想替换最近推荐中的第几本？"
            elif len(books) == 1:
                result.target_rank = 1
        whole_list = (
            result.action == "explain"
            and rank is None
            and any(word in text for word in ("这些", "这几本", "这个书单", "这批"))
        )
        if whole_list:
            result.target_rank = None
        if (
            result.action in {"explain", "availability"} and not whole_list
        ) or result.target_rank is not None:
            books = context.recommendation.items if context.recommendation else []
            if rank is None:
                result.target_rank = None
            if result.target_rank is None:
                matches = [i + 1 for i, book in enumerate(books) if book.title in text]
                if len(matches) == 1:
                    result.target_rank = matches[0]
                elif context.task.focused_book_id is not None:
                    result.target_rank = next(
                        (
                            i + 1
                            for i, book in enumerate(books)
                            if book.book_id == context.task.focused_book_id
                        ),
                        None,
                    )
                    if result.target_rank is None:
                        result.action = "clarify"
                elif len(books) == 1:
                    result.target_rank = 1
                else:
                    result.action = "clarify"
            if result.target_rank is not None and not 1 <= result.target_rank <= len(books):
                result.action = "clarify"
            if result.action == "clarify":
                result.clarification = "请告诉我是最近推荐中的第几本，或提供书名。"
        if result.action == "refine" and not (context.task.request or result.topic):
            result.action = "clarify"
            result.clarification = "你想调整哪个主题的图书推荐？"
        if result.action == "refine" and not result.new_topic and context.task.topic:
            result.topic = context.task.topic
        return result

    @staticmethod
    def rank(text: str) -> int | None:
        match = re.search(r"第([一二三四五六七八九十]|\d+)[本个]", text)
        if not match:
            return None
        value = match[1]
        return int(value) if value.isdigit() else "一二三四五六七八九十".index(value) + 1

    @staticmethod
    def fallback(context: ConversationContext, text: str) -> TurnResolution:
        if text.strip() in _STARTER_QUESTIONS:
            return TurnResolution(action="clarify", new_topic=True, clarification=_STARTER_QUESTIONS[text.strip()])
        action = "chat"
        rank = ConversationTurnService.rank(text)
        named_book = bool(
            context.recommendation
            and any(book.title in text for book in context.recommendation.items)
        )
        if any(word in text for word in ("能借", "可借", "在馆", "借得到")) and (
            rank is not None or named_book or any(word in text for word in ("这本", "那本", "它"))
        ):
            action = "availability"
        elif any(word in text for word in ("为什么推荐", "为何推荐", "适合我", "介绍这本")):
            action = "explain"
        elif (
            any(
                word in text
                for word in (
                    "简单",
                    "太难",
                    "难一点",
                    "进阶一些",
                    "零基础",
                    "换一",
                    "再推荐",
                    "还有别的",
                    "不要第",
                    "排除",
                    "不想看",
                    "取消",
                    "不限",
                    "只看可借",
                    "不必只看可借",
                )
            )
            and context.task.request
        ):
            action = "refine"
        elif any(word in text for word in ("推荐", "找书", "图书", "教材", "我想学")):
            action = "recommend"
        topics = re.findall(
            r"java|python|langchain|agent|数据库|算法|机器学习|人工智能|考研数学|操作系统|计算机网络",
            text,
            re.IGNORECASE,
        )
        topic = topics[0] if topics else ""
        new_topic = bool(
            topic and context.task.topic and topic.casefold() not in context.task.topic.casefold()
        )
        if new_topic and action in {"recommend", "refine"}:
            action = "recommend"
        if not context.task.request and text.strip().casefold() in {
            "java",
            "python",
            "agent",
            "机器学习",
        }:
            action = "clarify"
        if context.task.pending_question in _STARTER_QUESTIONS and action == "chat":
            # A subject supplied in response to an entry question is a book request.
            action = "recommend"
        request = text if new_topic or not context.task.request else context.task.request
        if context.task.request and not new_topic and action == "refine":
            # Preserve learning goals without turning ordinal references into search terms.
            if any(word in text for word in ("练习", "项目", "考试", "考研", "案例")):
                request += "；" + text
        return TurnResolution(
            action=action,
            topic=topic,
            new_topic=new_topic,
            target_rank=rank,
            keep_constraints="其他要求不变" in text,
            standalone_query=request,
            clarification="你希望了解这个概念，还是查找相关馆藏图书？",
        )

    @staticmethod
    def apply(context: ConversationContext, result: TurnResolution, text: str) -> str:
        if result.action == "clarify":
            if text.strip() in _STARTER_QUESTIONS:
                context.task = ConversationTask()
                context.constraints = ConstraintRead()
            context.task.pending_question = text
            return text
        if result.action not in {"recommend", "refine"}:
            if result.target_rank is not None and context.recommendation:
                context.task.focused_book_id = context.recommendation.items[
                    result.target_rank - 1
                ].book_id
            return text
        if result.new_topic:
            if not result.keep_constraints:
                context.constraints = ConstraintRead()
            context.task = ConversationTask()
        if result.topic:
            context.task.topic = result.topic
        context.task.request = result.standalone_query or context.task.request or text
        context.task.pending_question = ""
        context.task.focused_book_id = None
        for field in result.constraints.model_fields_set:
            value = getattr(result.constraints, field)
            if value is not None or field == "difficulty":
                setattr(context.constraints, field, value)
        if "取消限制" in text or "取消所有限制" in text:
            context.task.excluded_book_ids = []
        if any(word in text for word in ("取消", "不限", "不必只看可借")):
            context.task.request = re.sub(
                r"只看可借|仅在馆可借|必须可借|简单一点|零基础|入门|进阶|不要[A-Za-z+#.]+",
                "",
                context.task.request,
            )
        # Conditions are rendered from state, so cancelled instructions cannot linger in the query.
        return ConversationTurnService.query(context)

    @staticmethod
    def query(context: ConversationContext) -> str:
        topic = context.task.topic or context.task.request
        query = f"{topic}；学习需求：{context.task.request}"
        if context.constraints.difficulty:
            query += f"；难度：{context.constraints.difficulty}"
        if context.constraints.only_available:
            query += "；仅在馆可借"
        if context.constraints.excluded_terms:
            query += "；排除：" + "、".join(context.constraints.excluded_terms)
        return query
