from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    BookUserState,
    Conversation,
    EvaluationRecord,
    LearningPath,
    Notification,
    ProfileMemory,
    RecommendationFeedback,
    Reservation,
    User,
    UserProfile,
    UserRole,
)

DEMO_ACCOUNTS = (
    {
        "student_no": "demo_java",
        "display_name": "Java 零基础演示生",
        "profile": {
            "grade": "大一",
            "major": "计算机科学与技术",
            "foundation": "没有编程基础，希望从概念和案例开始",
            "learning_goals": ["掌握编程入门", "完成课程项目"],
            "interests": ["项目案例", "Web 开发"],
            "difficulty_preference": "beginner",
            "courses": ["程序设计基础"],
            "read_books": [],
            "career_direction": "后端开发",
        },
    },
    {
        "student_no": "demo_data",
        "display_name": "数据库课程演示生",
        "profile": {
            "grade": "大二",
            "major": "软件工程",
            "foundation": "了解基本编程概念，需要通过练习巩固",
            "learning_goals": ["课程预习与复习", "提升工程实践"],
            "interests": ["数据分析", "理论原理"],
            "difficulty_preference": "progressive",
            "courses": ["数据库原理", "数据结构"],
            "read_books": [],
            "career_direction": "数据分析",
        },
    },
)


@dataclass(frozen=True)
class DemoSeedResult:
    created: list[str]
    existing: list[str]


def seed_demo_accounts(session: Session, password: str) -> DemoSeedResult:
    created: list[str] = []
    existing: list[str] = []
    for account in DEMO_ACCOUNTS:
        user = session.scalar(select(User).where(User.student_no == account["student_no"]))
        if user is not None:
            existing.append(account["student_no"])
            continue
        user = User(
            student_no=account["student_no"],
            display_name=account["display_name"],
            password_hash=hash_password(password),
            role=UserRole.STUDENT,
            is_active=True,
        )
        user.profile = UserProfile(**account["profile"])
        session.add(user)
        created.append(account["student_no"])
    session.commit()
    return DemoSeedResult(created=created, existing=existing)


def reset_demo_activity(session: Session) -> int:
    student_numbers = [account["student_no"] for account in DEMO_ACCOUNTS]
    user_ids = list(
        session.scalars(select(User.id).where(User.student_no.in_(student_numbers)))
    )
    if not user_ids:
        return 0
    session.execute(delete(EvaluationRecord).where(EvaluationRecord.tester_code.like("demo_%")))
    for model in (
        Reservation,
        Notification,
        ProfileMemory,
        BookUserState,
        RecommendationFeedback,
        LearningPath,
        Conversation,
    ):
        session.execute(delete(model).where(model.user_id.in_(user_ids)))
    session.commit()
    return len(user_ids)
