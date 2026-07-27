from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.db.models import Book, BookTag, ReviewStatus

TOPIC_RULES = {
    "Java": ("java", "javase", "javaee", "jdk"),
    "数据库": ("数据库", "database", "sql", "mysql", "postgresql", "oracle"),
    "算法": ("算法", "algorithm", "数据结构"),
    "Python": ("python",),
    "人工智能": ("人工智能", "机器学习", "深度学习", "ai ", "神经网络"),
    "计算机网络": ("计算机网络", "网络技术", "tcp/ip"),
    "操作系统": ("操作系统", "linux", "unix"),
}


@dataclass(frozen=True)
class RuleTag:
    tag_type: str
    tag_value: str
    confidence: float


class RuleTagger:
    def tags_for(self, book: Book) -> list[RuleTag]:
        text = " ".join(
            value for value in (book.title, book.description, book.responsible_person) if value
        ).casefold()
        tags: list[RuleTag] = []
        for topic, keywords in TOPIC_RULES.items():
            if any(keyword in text for keyword in keywords):
                tags.append(RuleTag("topic", topic, 0.95))
        beginner = any(word in text for word in ("入门", "基础", "初学", "从零", "零基础"))
        advanced = any(word in text for word in ("高级", "深入", "进阶", "架构", "内核"))
        difficulty = "beginner" if beginner else "advanced" if advanced else "intermediate"
        tags.append(RuleTag("difficulty", difficulty, 0.82 if beginner or advanced else 0.65))
        stage = "入门" if beginner else "进阶" if advanced else "核心"
        tags.append(RuleTag("learning_stage", stage, 0.78))
        for label, words in {
            "项目": ("项目", "实战", "开发"),
            "案例": ("案例", "实例"),
            "题解": ("题解", "习题"),
            "理论": ("原理", "理论"),
        }.items():
            if any(word in text for word in words):
                tags.append(RuleTag("content_style", label, 0.8))
        return tags


class RuleTaggingService:
    def __init__(self, session: Session, tagger: RuleTagger | None = None) -> None:
        self.session = session
        self.tagger = tagger or RuleTagger()

    def run(self, data_version_id: UUID, *, limit: int | None = None) -> int:
        statement = select(Book).where(Book.data_version_id == data_version_id).order_by(Book.id)
        if limit:
            statement = statement.limit(limit)
        books = list(self.session.scalars(statement))
        book_ids = [book.id for book in books]
        if book_ids:
            self.session.execute(
                delete(BookTag).where(BookTag.book_id.in_(book_ids), BookTag.source == "rule")
            )
        rows = []
        for book in books:
            for tag in self.tagger.tags_for(book):
                rows.append(
                    {
                        "id": uuid4(),
                        "book_id": book.id,
                        "tag_type": tag.tag_type,
                        "tag_value": tag.tag_value,
                        "confidence": tag.confidence,
                        "source": "rule",
                        "model_name": "bookpath-rules-v1",
                        "prompt_version": None,
                        "review_status": ReviewStatus.APPROVED.value,
                    }
                )
        if rows:
            self.session.execute(insert(BookTag), rows)
        self.session.commit()
        return len(rows)
