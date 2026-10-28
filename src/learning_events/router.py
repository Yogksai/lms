from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.auth.dependencies.current_user import ICurrentUser
from src.config.db.session import ISession
from src.enrollment.dependencies_service import IEnrollmentService
from src.learning_events.dto import NotificationPageDTO
from src.learning_events.repository import LearningEventRepo
from src.quizzes.authoring_router import no_store

router = APIRouter(
    prefix="/me/notifications", tags=["Notifications"], dependencies=[Depends(no_store)]
)


@router.get("", response_model=NotificationPageDTO)
async def inbox(
    user: ICurrentUser,
    session: ISession,
    access: IEnrollmentService,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationPageDTO:
    async with session.begin():
        await access.actor(user)
        return await LearningEventRepo(session).inbox(user.id, limit, offset)


@router.post("/{notification_id}/read", status_code=204)
async def read(
    notification_id: Annotated[int, Path(gt=0)],
    user: ICurrentUser,
    session: ISession,
    access: IEnrollmentService,
) -> None:
    async with session.begin():
        await access.actor(user)
        if not await LearningEventRepo(session).read(user.id, notification_id, datetime.now(UTC)):
            raise HTTPException(404, "Notification not found")
