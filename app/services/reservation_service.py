from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import (
    Book,
    DataVersion,
    DataVersionStatus,
    Holding,
    Notification,
    Reservation,
    ReservationStatus,
)
from app.schemas.reservation import ReservationRead
from app.services.system_config_service import SystemConfigService


class ReservationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: UUID, holding_id: UUID) -> ReservationRead:
        row = self.session.execute(
            select(Holding, Book)
            .join(Book, Book.id == Holding.book_id)
            .join(DataVersion, DataVersion.id == Book.data_version_id)
            .where(
                Holding.id == holding_id,
                DataVersion.status == DataVersionStatus.PUBLISHED,
            )
        ).one_or_none()
        if row is None:
            raise AppError(status_code=404, code="HOLDING_NOT_FOUND", message="馆藏副本不存在")
        holding, book = row
        if holding.book_status != "available" or holding.circulation_status != "lendable":
            raise AppError(
                status_code=409, code="HOLDING_NOT_AVAILABLE", message="该副本当前不可预约"
            )
        existing = self.session.scalar(
            select(Reservation).where(
                Reservation.user_id == user_id,
                Reservation.holding_id == holding_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
        )
        if existing is not None:
            raise AppError(status_code=409, code="RESERVATION_EXISTS", message="你已预约该副本")
        expiry_days = int(SystemConfigService(self.session).get("reservation_expiry_days"))
        reservation = Reservation(
            user_id=user_id,
            holding_id=holding_id,
            status=ReservationStatus.ACTIVE,
            expires_at=datetime.now(UTC) + timedelta(days=expiry_days),
            is_mock=True,
        )
        self.session.add(reservation)
        self.session.flush()
        self.session.add(
            Notification(
                user_id=user_id,
                type="reservation_created",
                title="模拟预约已创建",
                content=f"《{book.title}》已加入模拟预约。该操作未同步学校图书馆系统。",
                payload={"reservation_id": str(reservation.id), "book_id": str(book.id)},
            )
        )
        self.session.commit()
        return self._read(reservation, holding, book)

    def cancel(self, user_id: UUID, reservation_id: UUID) -> ReservationRead:
        row = self.session.execute(
            select(Reservation, Holding, Book)
            .join(Holding, Holding.id == Reservation.holding_id)
            .join(Book, Book.id == Holding.book_id)
            .where(Reservation.id == reservation_id, Reservation.user_id == user_id)
        ).one_or_none()
        if row is None:
            raise AppError(status_code=404, code="RESERVATION_NOT_FOUND", message="预约不存在")
        reservation, holding, book = row
        if reservation.status != ReservationStatus.ACTIVE:
            raise AppError(status_code=409, code="RESERVATION_NOT_ACTIVE", message="预约已结束")
        reservation.status = ReservationStatus.CANCELLED
        self.session.add(
            Notification(
                user_id=user_id,
                type="reservation_cancelled",
                title="模拟预约已取消",
                content=f"《{book.title}》的模拟预约已取消。",
                payload={"reservation_id": str(reservation.id), "book_id": str(book.id)},
            )
        )
        self.session.commit()
        return self._read(reservation, holding, book)

    def list_for_user(self, user_id: UUID) -> list[ReservationRead]:
        rows = self.session.execute(
            select(Reservation, Holding, Book)
            .join(Holding, Holding.id == Reservation.holding_id)
            .join(Book, Book.id == Holding.book_id)
            .where(Reservation.user_id == user_id)
            .order_by(desc(Reservation.created_at))
        ).all()
        return [self._read(reservation, holding, book) for reservation, holding, book in rows]

    @staticmethod
    def _read(reservation: Reservation, holding: Holding, book: Book) -> ReservationRead:
        return ReservationRead(
            id=reservation.id,
            holding_id=holding.id,
            book_id=book.id,
            book_title=book.title,
            collection_location=holding.collection_location,
            call_number=holding.call_number,
            status=reservation.status,
            expires_at=reservation.expires_at,
            is_mock=reservation.is_mock,
            created_at=reservation.created_at,
        )


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: UUID, unread_only: bool) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.read_at.is_(None))
        return list(
            self.session.scalars(statement.order_by(desc(Notification.created_at)).limit(100))
        )

    def unread_count(self, user_id: UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id, Notification.read_at.is_(None)
                )
            )
            or 0
        )

    def mark_read(self, user_id: UUID, notification_id: UUID) -> Notification:
        value = self.session.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        if value is None:
            raise AppError(status_code=404, code="NOTIFICATION_NOT_FOUND", message="通知不存在")
        value.read_at = value.read_at or datetime.now(UTC)
        self.session.commit()
        return value

    def mark_all_read(self, user_id: UUID) -> int:
        values = self.list_for_user(user_id, unread_only=True)
        now = datetime.now(UTC)
        for value in values:
            value.read_at = now
        self.session.commit()
        return len(values)
