from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.auth.dto import UserDTO
from src.auth.models.user import UserModel
from src.config.db.session import ISession
from src.courses.dto import CourseDTO
from src.courses.models import CourseModel
from src.courses.models.assignment import TeacherAssignmentModel
from src.enrollment.dto import (
    EnrollmentDTO,
    EnrollmentPageDTO,
    GrantDTO,
    GrantPageDTO,
    GrantSource,
    ManagedGrantDTO,
    ManagedRequestDTO,
    RequestDTO,
    RequestPageDTO,
    RequestStatus,
)
from src.enrollment.models import AccessGrantModel, AccessRequestModel, EnrollmentModel


@dataclass(frozen=True)
class CourseState:
    id: int
    available: bool


@dataclass(frozen=True)
class GrantAccess:
    sources: list[GrantSource]
    expires_at: datetime | None


class EnrollmentRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def course(self, course_id: int, lock: bool = False) -> CourseState | None:
        query = (
            select(CourseModel)
            .where(CourseModel.id == course_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        course = await self.session.scalar(query)
        return (
            CourseState(course.id, course.is_published and not course.is_archived)
            if course
            else None
        )

    async def user(self, user_id: int) -> UserDTO | None:
        user = await self.session.scalar(
            select(UserModel)
            .where(UserModel.id == user_id)
            .execution_options(populate_existing=True)
        )
        return UserDTO.model_validate(user) if user else None

    async def assigned(self, course_id: int, user_id: int) -> bool:
        return (
            await self.session.scalar(
                select(TeacherAssignmentModel.id).where(
                    TeacherAssignmentModel.course_id == course_id,
                    TeacherAssignmentModel.user_id == user_id,
                )
            )
            is not None
        )

    async def enrolled(self, course_id: int, user_id: int) -> bool:
        return (
            await self.session.scalar(
                select(EnrollmentModel.id).where(
                    EnrollmentModel.course_id == course_id,
                    EnrollmentModel.user_id == user_id,
                    EnrollmentModel.left_at.is_(None),
                )
            )
            is not None
        )

    async def enroll(self, course_id: int, user_id: int) -> None:
        await self.session.execute(
            insert(EnrollmentModel)
            .values(course_id=course_id, user_id=user_id)
            .on_conflict_do_update(
                index_elements=[EnrollmentModel.course_id, EnrollmentModel.user_id],
                set_={"left_at": None, "updated_at": func.now()},
            )
        )

    async def leave(self, course_id: int, user_id: int, now: datetime) -> None:
        await self.session.execute(
            update(EnrollmentModel)
            .where(
                EnrollmentModel.course_id == course_id,
                EnrollmentModel.user_id == user_id,
                EnrollmentModel.left_at.is_(None),
            )
            .values(left_at=now, updated_at=now)
        )
        await self.session.execute(
            update(AccessRequestModel)
            .where(
                AccessRequestModel.course_id == course_id,
                AccessRequestModel.user_id == user_id,
                AccessRequestModel.status == "pending",
            )
            .values(status="cancelled", decided_at=now, decided_by=user_id)
        )
        await self.session.execute(
            update(AccessGrantModel)
            .where(
                AccessGrantModel.course_id == course_id,
                AccessGrantModel.user_id == user_id,
                AccessGrantModel.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoked_by=user_id)
        )

    async def list_enrollments(self, user_id: int, limit: int, offset: int) -> EnrollmentPageDTO:
        filters = [EnrollmentModel.user_id == user_id, EnrollmentModel.left_at.is_(None)]
        total = await self.session.scalar(
            select(func.count()).select_from(EnrollmentModel).where(*filters)
        )
        rows = await self.session.execute(
            select(EnrollmentModel, CourseModel)
            .join(CourseModel, CourseModel.id == EnrollmentModel.course_id)
            .where(*filters)
            .order_by(EnrollmentModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return EnrollmentPageDTO(
            items=[
                EnrollmentDTO(
                    course=CourseDTO.model_validate(course),
                    enrolled_at=enrollment.created_at,
                    available=course.is_published and not course.is_archived,
                )
                for enrollment, course in rows
            ],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def latest_request(self, course_id: int, user_id: int) -> RequestDTO | None:
        request = await self.session.scalar(
            select(AccessRequestModel)
            .where(AccessRequestModel.course_id == course_id, AccessRequestModel.user_id == user_id)
            .order_by(AccessRequestModel.id.desc())
            .limit(1)
        )
        return RequestDTO.model_validate(request) if request else None

    async def request(self, course_id: int, request_id: int) -> RequestDTO | None:
        request = await self.session.scalar(
            select(AccessRequestModel)
            .where(AccessRequestModel.course_id == course_id, AccessRequestModel.id == request_id)
            .execution_options(populate_existing=True)
        )
        return RequestDTO.model_validate(request) if request else None

    async def create_request(self, course_id: int, user_id: int, message: str) -> None:
        self.session.add(
            AccessRequestModel(
                course_id=course_id, user_id=user_id, message=message.strip(), status="pending"
            )
        )
        await self.session.flush()

    async def decide(
        self, request_id: int, status: RequestStatus, actor_id: int, now: datetime, note: str
    ) -> None:
        await self.session.execute(
            update(AccessRequestModel)
            .where(AccessRequestModel.id == request_id, AccessRequestModel.status == "pending")
            .values(status=status, decided_at=now, decided_by=actor_id, decision_note=note.strip())
        )

    async def grant_access(self, course_id: int, user_id: int, now: datetime) -> GrantAccess:
        rows = await self.session.execute(
            select(AccessGrantModel.source, func.max(AccessGrantModel.expires_at))
            .where(
                AccessGrantModel.course_id == course_id,
                AccessGrantModel.user_id == user_id,
                AccessGrantModel.revoked_at.is_(None),
                AccessGrantModel.expires_at > now,
            )
            .group_by(AccessGrantModel.source)
        )
        values = rows.all()
        return GrantAccess(
            sources=[cast(GrantSource, source) for source, _ in values],
            expires_at=max((expires for _, expires in values), default=None),
        )

    async def own_grants(self, course_id: int, user_id: int) -> list[GrantDTO]:
        grants = await self.session.scalars(
            select(AccessGrantModel)
            .where(AccessGrantModel.course_id == course_id, AccessGrantModel.user_id == user_id)
            .order_by(AccessGrantModel.id.desc())
            .limit(50)
        )
        return [GrantDTO.model_validate(grant) for grant in grants]

    async def grant(self, course_id: int, grant_id: int) -> GrantDTO | None:
        grant = await self.session.scalar(
            select(AccessGrantModel)
            .where(AccessGrantModel.course_id == course_id, AccessGrantModel.id == grant_id)
            .execution_options(populate_existing=True)
        )
        return GrantDTO.model_validate(grant) if grant else None

    async def create_grant(
        self,
        course_id: int,
        user_id: int,
        source: GrantSource,
        actor_id: int,
        now: datetime,
        expires_at: datetime,
        request_id: int | None = None,
    ) -> GrantDTO:
        instance = AccessGrantModel(
            course_id=course_id,
            user_id=user_id,
            source=source,
            granted_by=actor_id,
            created_at=now,
            expires_at=expires_at,
            request_id=request_id,
        )
        self.session.add(instance)
        await self.session.flush()
        return GrantDTO.model_validate(instance)

    async def revoke(self, grant_id: int, actor_id: int, now: datetime) -> None:
        await self.session.execute(
            update(AccessGrantModel)
            .where(AccessGrantModel.id == grant_id, AccessGrantModel.revoked_at.is_(None))
            .values(revoked_at=now, revoked_by=actor_id)
        )

    async def list_requests(
        self, course_id: int, status: RequestStatus | None, limit: int, offset: int
    ) -> RequestPageDTO:
        filters = [AccessRequestModel.course_id == course_id]
        if status:
            filters.append(AccessRequestModel.status == status)
        total = await self.session.scalar(
            select(func.count()).select_from(AccessRequestModel).where(*filters)
        )
        rows = await self.session.execute(
            select(AccessRequestModel, UserModel)
            .join(UserModel, UserModel.id == AccessRequestModel.user_id)
            .where(*filters)
            .order_by(AccessRequestModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return RequestPageDTO(
            items=[
                ManagedRequestDTO(
                    **RequestDTO.model_validate(request).model_dump(),
                    student=UserDTO.model_validate(user),
                )
                for request, user in rows
            ],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def list_grants(
        self, course_id: int, active_only: bool, limit: int, offset: int, now: datetime
    ) -> GrantPageDTO:
        filters = [AccessGrantModel.course_id == course_id]
        if active_only:
            filters.extend(
                [
                    AccessGrantModel.revoked_at.is_(None),
                    AccessGrantModel.expires_at > now,
                    UserModel.is_active.is_(True),
                    EnrollmentModel.left_at.is_(None),
                ]
            )
        query = (
            select(AccessGrantModel, UserModel, EnrollmentModel.left_at)
            .join(UserModel, UserModel.id == AccessGrantModel.user_id)
            .join(
                EnrollmentModel,
                (EnrollmentModel.course_id == AccessGrantModel.course_id)
                & (EnrollmentModel.user_id == AccessGrantModel.user_id),
            )
            .where(*filters)
        )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.session.execute(
            query.order_by(AccessGrantModel.id.desc()).limit(limit).offset(offset)
        )
        return GrantPageDTO(
            items=[
                ManagedGrantDTO(
                    **GrantDTO.model_validate(grant).model_dump(),
                    student=UserDTO.model_validate(user),
                    active=grant.revoked_at is None
                    and grant.expires_at > now
                    and user.is_active
                    and left_at is None,
                )
                for grant, user, left_at in rows
            ],
            total=total or 0,
            limit=limit,
            offset=offset,
        )
