from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from src.auth.dto import UserDTO
from src.config.db.session import ISession
from src.enrollment.dependencies import IEnrollmentRepo
from src.enrollment.dto import (
    AccessDTO,
    AccessReason,
    DecisionDTO,
    EnrollmentPageDTO,
    GrantDTO,
    GrantInputDTO,
    GrantPageDTO,
    RequestInputDTO,
    RequestPageDTO,
    RequestStatus,
)
from src.enrollment.repository import CourseState


class EnrollmentService:
    def __init__(self, session: ISession, repository: IEnrollmentRepo) -> None:
        self.session = session
        self.repository = repository

    async def actor(self, user: UserDTO) -> UserDTO:
        current = await self.repository.user(user.id)
        if current is None or not current.is_active:
            raise HTTPException(401, "Account unavailable")
        return current

    async def course(
        self, course_id: int, *, lock: bool = False, published: bool = False
    ) -> CourseState:
        course = await self.repository.course(course_id, lock=lock)
        if course is None or (published and not course.available):
            raise HTTPException(404, "Course not found")
        return course

    async def staff_reason(self, actor: UserDTO, course_id: int) -> AccessReason | None:
        if actor.role == "admin":
            return "admin"
        if actor.role == "teacher" and await self.repository.assigned(course_id, actor.id):
            return "assigned_teacher"
        return None

    async def manage(
        self, user: UserDTO, course_id: int, *, lock: bool = False, admin: bool = False
    ) -> tuple[CourseState, UserDTO]:
        course = await self.course(course_id, lock=lock)
        actor = await self.actor(user)
        if admin and actor.role != "admin":
            raise HTTPException(403, "Admin permission required")
        if actor.role not in {"admin", "teacher"}:
            raise HTTPException(403, "Teacher permission required")
        if not await self.staff_reason(actor, course_id):
            raise HTTPException(404, "Assigned course not found")
        return course, actor

    async def status_in_transaction(self, actor: UserDTO, course: CourseState) -> AccessDTO:
        enrolled = await self.repository.enrolled(course.id, actor.id)
        staff = await self.staff_reason(actor, course.id)
        if not course.available and not enrolled and staff is None:
            raise HTTPException(404, "Course not found")
        now = datetime.now(UTC)
        access = await self.repository.grant_access(course.id, actor.id, now)
        reasons: list[AccessReason] = []
        if course.available:
            if staff:
                reasons.append(staff)
            if enrolled:
                reasons.extend(access.sources)
        return AccessDTO(
            course_id=course.id,
            available=course.available,
            enrolled=enrolled,
            full_access=bool(reasons),
            reasons=reasons,
            expires_at=access.expires_at if enrolled and reasons and not staff else None,
            request=await self.repository.latest_request(course.id, actor.id),
            grants=await self.repository.own_grants(course.id, actor.id),
        )

    async def status(self, user: UserDTO, course_id: int) -> AccessDTO:
        async with self.session.begin():
            course = await self.course(course_id)
            return await self.status_in_transaction(await self.actor(user), course)

    async def can_read(self, user: UserDTO, course_id: int) -> bool:
        async with self.session.begin():
            course = await self.course(course_id, published=True)
            actor = await self.actor(user)
            if await self.staff_reason(actor, course.id):
                return True
            if not await self.repository.enrolled(course.id, actor.id):
                return False
            return bool(
                (await self.repository.grant_access(course.id, actor.id, datetime.now(UTC))).sources
            )

    async def enroll(self, user: UserDTO, course_id: int) -> AccessDTO:
        async with self.session.begin():
            course = await self.course(course_id, lock=True, published=True)
            actor = await self.actor(user)
            await self.repository.enroll(course_id, actor.id)
            return await self.status_in_transaction(actor, course)

    async def leave(self, user: UserDTO, course_id: int) -> None:
        async with self.session.begin():
            await self.course(course_id, lock=True)
            actor = await self.actor(user)
            await self.repository.leave(course_id, actor.id, datetime.now(UTC))

    async def mine(self, user: UserDTO, limit: int, offset: int) -> EnrollmentPageDTO:
        async with self.session.begin():
            actor = await self.actor(user)
            return await self.repository.list_enrollments(actor.id, limit, offset)

    async def request_access(
        self, user: UserDTO, course_id: int, data: RequestInputDTO
    ) -> AccessDTO:
        async with self.session.begin():
            course = await self.course(course_id, lock=True, published=True)
            actor = await self.actor(user)
            if not await self.repository.enrolled(course_id, actor.id):
                raise HTTPException(409, "Enroll before requesting access")
            previous = await self.repository.latest_request(course_id, actor.id)
            if previous is not None and previous.status == "pending":
                return await self.status_in_transaction(actor, course)
            status = await self.status_in_transaction(actor, course)
            if status.full_access:
                raise HTTPException(409, "Full course access is already active")
            await self.repository.create_request(course_id, actor.id, data.message)
            return await self.status_in_transaction(actor, course)

    async def cancel(self, user: UserDTO, course_id: int, request_id: int) -> AccessDTO:
        async with self.session.begin():
            course = await self.course(course_id, lock=True)
            actor = await self.actor(user)
            request = await self.repository.request(course_id, request_id)
            if request is None or request.user_id != actor.id:
                raise HTTPException(404, "Access request not found")
            if request.status != "pending":
                raise HTTPException(409, "Only pending requests can be cancelled")
            await self.repository.decide(request.id, "cancelled", actor.id, datetime.now(UTC), "")
            return await self.status_in_transaction(actor, course)

    async def requests(
        self, user: UserDTO, course_id: int, status: RequestStatus | None, limit: int, offset: int
    ) -> RequestPageDTO:
        async with self.session.begin():
            await self.manage(user, course_id)
            return await self.repository.list_requests(course_id, status, limit, offset)

    async def decide(
        self, user: UserDTO, course_id: int, request_id: int, data: DecisionDTO
    ) -> None:
        async with self.session.begin():
            course, actor = await self.manage(user, course_id, lock=True)
            request = await self.repository.request(course_id, request_id)
            if request is None:
                raise HTTPException(404, "Access request not found")
            if request.status != "pending":
                raise HTTPException(409, "Access request has already been decided")
            now = datetime.now(UTC)
            if data.decision == "approve":
                if not course.available:
                    raise HTTPException(409, "Publish the course before granting learner access")
                target = await self.repository.user(request.user_id)
                if target is None or not target.is_active:
                    raise HTTPException(422, "Access requires an active account")
                if not await self.repository.enrolled(course_id, request.user_id):
                    raise HTTPException(409, "Student is no longer enrolled")
                await self.repository.create_grant(
                    course_id,
                    request.user_id,
                    "teacher_approval",
                    actor.id,
                    now,
                    now + timedelta(days=data.duration_days),
                    request.id,
                )
            await self.repository.decide(
                request.id,
                "approved" if data.decision == "approve" else "rejected",
                actor.id,
                now,
                data.note,
            )

    async def grants(
        self, user: UserDTO, course_id: int, active_only: bool, limit: int, offset: int
    ) -> GrantPageDTO:
        async with self.session.begin():
            await self.manage(user, course_id)
            return await self.repository.list_grants(
                course_id, active_only, limit, offset, datetime.now(UTC)
            )

    async def grant(self, user: UserDTO, course_id: int, data: GrantInputDTO) -> GrantDTO:
        async with self.session.begin():
            course, actor = await self.manage(user, course_id, lock=True, admin=True)
            if not course.available:
                raise HTTPException(409, "Publish the course before granting learner access")
            target = await self.repository.user(data.user_id)
            if target is None or not target.is_active:
                raise HTTPException(422, "Access requires an active account")
            if not await self.repository.enrolled(course_id, data.user_id):
                raise HTTPException(409, "Student must enroll before receiving access")
            now = datetime.now(UTC)
            return await self.repository.create_grant(
                course_id,
                data.user_id,
                "admin_grant",
                actor.id,
                now,
                now + timedelta(days=data.duration_days),
            )

    async def revoke(self, user: UserDTO, course_id: int, grant_id: int) -> None:
        async with self.session.begin():
            _, actor = await self.manage(user, course_id, lock=True)
            grant = await self.repository.grant(course_id, grant_id)
            if grant is None:
                raise HTTPException(404, "Access grant not found")
            if grant.source == "admin_grant" and actor.role != "admin":
                raise HTTPException(403, "Only admins can revoke admin grants")
            if grant.revoked_at is None:
                await self.repository.revoke(grant.id, actor.id, datetime.now(UTC))
