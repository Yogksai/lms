from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.auth.models.user import UserModel
from src.config.db.session import ISession
from src.learning_events.dto import NotificationDTO, NotificationPageDTO, QuizSubmitted
from src.learning_events.models import LearningNotificationModel, LearningOutboxModel


class LearningEventRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def enqueue(self, event: QuizSubmitted) -> None:
        self.session.add(
            LearningOutboxModel(event_id=event.event_id, payload=event.model_dump(mode="json"))
        )
        await self.session.flush()

    async def deliver(self, event: QuizSubmitted) -> None:
        # Lock the recipient until insert completes; account deletion can run concurrently.
        user = await self.session.scalar(
            select(UserModel.id).where(UserModel.id == event.user_id).with_for_update()
        )
        if user is None:
            return
        await self.session.execute(
            insert(LearningNotificationModel)
            .values(
                event_id=event.event_id,
                user_id=event.user_id,
                title="Результат теста",
                message=f"{event.module_title}: {event.score_percent}% — "
                + ("тест пройден" if event.passed else "стоит повторить материал"),
                link=f"/courses/{event.course_id}/attempts/{event.attempt_id}",
            )
            .on_conflict_do_nothing(index_elements=[LearningNotificationModel.event_id])
        )

    async def inbox(self, user_id: int, limit: int, offset: int) -> NotificationPageDTO:
        filters = [LearningNotificationModel.user_id == user_id]
        total = await self.session.scalar(
            select(func.count()).select_from(LearningNotificationModel).where(*filters)
        )
        rows = await self.session.scalars(
            select(LearningNotificationModel)
            .where(*filters)
            .order_by(LearningNotificationModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return NotificationPageDTO(
            items=[NotificationDTO.model_validate(row) for row in rows],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def read(self, user_id: int, notification_id: int, now: datetime) -> bool:
        result = await self.session.scalar(
            update(LearningNotificationModel)
            .where(
                LearningNotificationModel.id == notification_id,
                LearningNotificationModel.user_id == user_id,
            )
            .values(read_at=func.coalesce(LearningNotificationModel.read_at, now))
            .returning(LearningNotificationModel.id)
        )
        return result is not None
