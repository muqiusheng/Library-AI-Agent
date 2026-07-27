import re
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Book,
    BookUserState,
    BookUserStateValue,
    FeedbackType,
    RecommendationFeedback,
    RecommendationItem,
    RecommendationSet,
    User,
)
from app.integrations.library.local import LocalLibraryAdapter
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider
from app.schemas.recommendation import (
    HoldingCard,
    RecommendationCard,
    RecommendationSetRead,
    ScoreBreakdown,
)
from app.services.system_config_service import SystemConfigService


class RerankItem(BaseModel):
    book_id: UUID
    rank: int = Field(ge=1, le=15)
    reason: str = Field(min_length=1, max_length=300)


class RerankOutput(BaseModel):
    items: list[RerankItem] = Field(max_length=5)


@dataclass
class ScoredBook:
    book: Book
    scores: ScoreBreakdown
    total: float
    reason: str


class RecommendationService:
    def __init__(
        self,
        session: Session,
        library: LocalLibraryAdapter | None = None,
        llm: DeepSeekProvider | None = None,
    ) -> None:
        self.session = session
        self.library = library or LocalLibraryAdapter(session)
        self.llm = llm or DeepSeekProvider()

    async def recommend(
        self,
        *,
        user: User,
        conversation_id: UUID,
        query: str,
        only_available: bool = False,
        constraints: dict | None = None,
    ) -> RecommendationSetRead:
        constraint_values = {"only_available": only_available, **(constraints or {})}
        config = SystemConfigService(self.session)
        top_k = int(config.get("recommendation_top_k"))
        weights = config.get("recommendation_weights")
        only_available = bool(constraint_values.get("only_available"))
        feedback = list(
            self.session.scalars(
                select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)
            )
        )
        excluded_ids = {
            value.book_id for value in feedback if value.type == FeedbackType.NOT_INTERESTED
        }
        completed_ids = set(
            self.session.scalars(
                select(BookUserState.book_id).where(
                    BookUserState.user_id == user.id,
                    BookUserState.state == BookUserStateValue.COMPLETED,
                )
            )
        )
        excluded_terms = [
            str(value).casefold() for value in constraint_values.get("excluded_terms", [])
        ]
        candidates = self.library.search_candidates(query, limit=50)
        candidates = [
            book
            for book in candidates
            if book.id not in excluded_ids
            and book.id not in completed_ids
            and not any(
                term in f"{book.title} {book.description or ''}".casefold()
                for term in excluded_terms
            )
        ]
        if only_available:
            candidates = [book for book in candidates if self._available_count(book) > 0]
        preferred = self._effective_preference(user, feedback, constraint_values.get("difficulty"))
        scored = sorted(
            (self._score(book, query, user, preferred, weights) for book in candidates),
            key=lambda item: item.total,
            reverse=True,
        )
        top = scored[:10]
        ordered = await self._rerank(query, top)
        final = ordered[:top_k]
        recommendation_set = RecommendationSet(
            user_id=user.id,
            conversation_id=conversation_id,
            query=query,
            profile_snapshot=self._profile_snapshot(user),
            constraints_snapshot=constraint_values,
            model_name=self.llm.settings.deepseek_chat_model
            if self.llm.available
            else "deterministic-v1",
        )
        self.session.add(recommendation_set)
        self.session.flush()
        cards: list[RecommendationCard] = []
        for rank, item in enumerate(final, start=1):
            self.session.add(
                RecommendationItem(
                    set_id=recommendation_set.id,
                    book_id=item.book.id,
                    rank=rank,
                    total_score=item.total,
                    goal_score=item.scores.goal,
                    difficulty_score=item.scores.difficulty,
                    major_score=item.scores.major,
                    interest_score=item.scores.interest,
                    semantic_score=item.scores.semantic,
                    availability_score=item.scores.availability,
                    reason=item.reason,
                    reason_source="llm" if self.llm.available else "template",
                )
            )
            cards.append(self._card(item))
        self.session.commit()
        return RecommendationSetRead(
            id=recommendation_set.id,
            query=query,
            summary=f"根据你的目标，从当前馆藏中筛选出 {len(cards)} 本匹配图书。",
            created_at=recommendation_set.created_at,
            items=cards,
        )

    def get_set(self, set_id: UUID, user_id: UUID) -> RecommendationSetRead | None:
        recommendation_set = self.session.get(RecommendationSet, set_id)
        if recommendation_set is None or recommendation_set.user_id != user_id:
            return None
        items = sorted(recommendation_set.items, key=lambda item: item.rank)
        books = {book.id: book for book in self.library.get_books([item.book_id for item in items])}
        cards = []
        for item in items:
            book = books.get(item.book_id)
            if not book:
                continue
            scored = ScoredBook(
                book=book,
                total=float(item.total_score),
                reason=item.reason,
                scores=ScoreBreakdown(
                    goal=float(item.goal_score),
                    difficulty=float(item.difficulty_score),
                    major=float(item.major_score),
                    interest=float(item.interest_score),
                    semantic=float(item.semantic_score),
                    availability=float(item.availability_score),
                ),
            )
            cards.append(self._card(scored))
        return RecommendationSetRead(
            id=recommendation_set.id,
            query=recommendation_set.query,
            summary=f"当前推荐包含 {len(cards)} 本真实馆藏图书。",
            created_at=recommendation_set.created_at,
            items=cards,
        )

    def _score(
        self,
        book: Book,
        query: str,
        user: User,
        preferred_difficulty: str | None = None,
        weights: dict[str, float] | None = None,
    ) -> ScoredBook:
        tags = {tag.tag_type: tag.tag_value for tag in book.tags}
        topics = [tag.tag_value for tag in book.tags if tag.tag_type == "topic"]
        haystack = " ".join([book.title, book.description or "", *topics]).casefold()
        terms = self._terms(query)
        matched = sum(1 for term in terms if term in haystack)
        goal = min(100.0, 45.0 + 55.0 * matched / max(1, len(terms))) if matched else 20.0
        preferred = preferred_difficulty or (
            user.profile.difficulty_preference.value if user.profile else "progressive"
        )
        difficulty_value = tags.get("difficulty", "intermediate")
        difficulty = self._difficulty_score(preferred, difficulty_value)
        major = (
            80.0
            if user.profile and any(part in haystack for part in self._terms(user.profile.major))
            else 55.0
        )
        interests = user.profile.interests if user.profile else []
        interest = 85.0 if any(value.casefold() in haystack for value in interests) else 50.0
        semantic = min(100.0, goal * 0.85 + (15.0 if topics else 0.0))
        availability = 100.0 if self._available_count(book) else 35.0 if book.holdings else 0.0
        active_weights = weights or {
            "goal": 0.30,
            "difficulty": 0.20,
            "major": 0.15,
            "interest": 0.10,
            "semantic": 0.15,
            "availability": 0.10,
        }
        total = round(
            goal * active_weights["goal"]
            + difficulty * active_weights["difficulty"]
            + major * active_weights["major"]
            + interest * active_weights["interest"]
            + semantic * active_weights["semantic"]
            + availability * active_weights["availability"],
            2,
        )
        reason = self._template_reason(book, difficulty_value, topics, availability)
        return ScoredBook(
            book=book,
            scores=ScoreBreakdown(
                goal=round(goal, 2),
                difficulty=round(difficulty, 2),
                major=round(major, 2),
                interest=round(interest, 2),
                semantic=round(semantic, 2),
                availability=round(availability, 2),
            ),
            total=total,
            reason=reason,
        )

    async def _rerank(self, query: str, candidates: list[ScoredBook]) -> list[ScoredBook]:
        if not self.llm.available or not candidates:
            return candidates
        allowed = {item.book.id: item for item in candidates}
        payload = [
            {"book_id": str(item.book.id), "title": item.book.title, "score": item.total}
            for item in candidates
        ]
        try:
            result = await self.llm.structured(
                [{"role": "user", "content": f"学习需求：{query}\n候选：{payload}"}],
                RerankOutput,
            )
        except DeepSeekError:
            return candidates
        ordered: list[ScoredBook] = []
        for reranked in sorted(result.items, key=lambda item: item.rank):
            if reranked.book_id in allowed:
                value = allowed.pop(reranked.book_id)
                value.reason = reranked.reason
                ordered.append(value)
        ordered.extend(item for item in candidates if item.book.id in allowed)
        return ordered

    def _card(self, item: ScoredBook) -> RecommendationCard:
        book = item.book
        topics = [tag.tag_value for tag in book.tags if tag.tag_type == "topic"]
        difficulty = next(
            (tag.tag_value for tag in book.tags if tag.tag_type == "difficulty"), "intermediate"
        )
        stage = next(
            (tag.tag_value for tag in book.tags if tag.tag_type == "learning_stage"), "核心"
        )
        holdings = [
            HoldingCard.model_validate(
                {
                    "id": holding.id,
                    "call_number": holding.call_number,
                    "collection_location": holding.collection_location,
                    "current_location": holding.current_location,
                    "shelf_number": holding.shelf_number,
                    "book_status": holding.book_status,
                    "circulation_status": holding.circulation_status,
                }
            )
            for holding in book.holdings
        ]
        return RecommendationCard(
            book_id=book.id,
            title=book.title,
            responsible_person=book.responsible_person,
            isbn=book.isbn13 or book.isbn10,
            publisher=book.publisher,
            publication_year=book.publication_year,
            description=book.description,
            topics=topics,
            difficulty=difficulty,
            learning_stage=stage,
            total_score=item.total,
            scores=item.scores,
            reason=item.reason,
            holdings_count=len(holdings),
            available_count=self._available_count(book),
            holdings=holdings,
        )

    @staticmethod
    def _available_count(book: Book) -> int:
        return sum(
            holding.book_status == "available" and holding.circulation_status == "lendable"
            for holding in book.holdings
        )

    @staticmethod
    def _terms(text: str) -> list[str]:
        lowered = text.casefold()
        known = [
            word
            for word in ("java", "python", "数据库", "算法", "人工智能", "机器学习")
            if word in lowered
        ]
        return list(
            dict.fromkeys(
                [*known, *re.findall(r"[a-z][a-z0-9+#.-]{1,20}|[\u4e00-\u9fff]{2,8}", lowered)]
            )
        )

    @staticmethod
    def _difficulty_score(preferred: str, actual: str) -> float:
        levels = {"beginner": 0, "progressive": 1, "intermediate": 1, "advanced": 2}
        return max(20.0, 100.0 - abs(levels.get(preferred, 1) - levels.get(actual, 1)) * 40.0)

    @staticmethod
    def _effective_preference(user: User, feedback: list[RecommendationFeedback], override) -> str:
        if override in {"beginner", "intermediate", "advanced"}:
            return str(override)
        too_hard = sum(value.type == FeedbackType.TOO_HARD for value in feedback)
        too_easy = sum(value.type == FeedbackType.TOO_EASY for value in feedback)
        if too_hard > too_easy:
            return "beginner"
        if too_easy > too_hard:
            return "advanced"
        return user.profile.difficulty_preference.value if user.profile else "progressive"

    @staticmethod
    def _template_reason(
        book: Book, difficulty: str, topics: list[str], availability: float
    ) -> str:
        topic_text = "、".join(topics[:2]) or "当前学习目标"
        availability_text = "目前有可借副本" if availability >= 100 else "馆藏信息完整，可到馆查阅"
        return f"内容聚焦{topic_text}，难度为 {difficulty}；{availability_text}。"

    @staticmethod
    def _profile_snapshot(user: User) -> dict:
        if not user.profile:
            return {}
        return {
            "grade": user.profile.grade,
            "major": user.profile.major,
            "foundation": user.profile.foundation,
            "learning_goals": user.profile.learning_goals,
            "interests": user.profile.interests,
            "difficulty_preference": user.profile.difficulty_preference.value,
        }
