from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_student_no(self, student_no: str, *, with_profile: bool = False) -> User | None:
        statement = select(User).where(User.student_no == student_no)
        if with_profile:
            statement = statement.options(selectinload(User.profile))
        return self.session.scalar(statement)

    def get_by_id(self, user_id: UUID, *, with_profile: bool = False) -> User | None:
        statement = select(User).where(User.id == user_id)
        if with_profile:
            statement = statement.options(selectinload(User.profile))
        return self.session.scalar(statement)
