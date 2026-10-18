from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import selectinload

from src.auth.dto import UserDTO
from src.auth.models.user import UserModel
from src.authoring.dto import (
    EditorCourseDTO,
    EditorCoursePageDTO,
    EditorCourseSummaryDTO,
    EditorModuleDTO,
    UserPageDTO,
)
from src.config.db.session import ISession
from src.courses.models import CourseModel, LessonModel, ModuleModel
from src.courses.models.assignment import TeacherAssignmentModel

ROLE_LOCK = 54237204


class AuthoringRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    @staticmethod
    def summary(course: CourseModel) -> EditorCourseSummaryDTO:
        return EditorCourseSummaryDTO(
            id=course.id,
            slug=course.slug,
            title=course.title,
            description=course.description,
            status="archived"
            if course.is_archived
            else "published"
            if course.is_published
            else "draft",
            revision=course.revision,
        )

    async def user(self, user_id: int) -> UserDTO | None:
        user = await self.session.scalar(
            select(UserModel)
            .where(UserModel.id == user_id)
            .execution_options(populate_existing=True)
        )
        return UserDTO.model_validate(user) if user else None

    async def list_courses(self, actor: UserDTO, limit: int, offset: int) -> EditorCoursePageDTO:
        filters = (
            []
            if actor.role == "admin"
            else [
                CourseModel.id.in_(
                    select(TeacherAssignmentModel.course_id).where(
                        TeacherAssignmentModel.user_id == actor.id
                    )
                )
            ]
        )
        total = await self.session.scalar(
            select(func.count()).select_from(CourseModel).where(*filters)
        )
        courses = await self.session.scalars(
            select(CourseModel).where(*filters).order_by(CourseModel.id).limit(limit).offset(offset)
        )
        return EditorCoursePageDTO(
            items=[self.summary(course) for course in courses],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def course(self, course_id: int, lock: bool = False) -> CourseModel | None:
        query = (
            select(CourseModel)
            .where(CourseModel.id == course_id)
            .options(selectinload(CourseModel.modules).selectinload(ModuleModel.lessons))
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

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

    async def detail(self, course: CourseModel) -> EditorCourseDTO:
        teachers = await self.session.scalars(
            select(UserModel)
            .join(TeacherAssignmentModel, TeacherAssignmentModel.user_id == UserModel.id)
            .where(TeacherAssignmentModel.course_id == course.id)
            .order_by(UserModel.id)
        )
        return EditorCourseDTO(
            **self.summary(course).model_dump(),
            modules=[EditorModuleDTO.model_validate(module) for module in course.modules],
            teachers=[UserDTO.model_validate(user) for user in teachers],
        )

    async def assign(self, course_id: int, user_id: int) -> None:
        if not await self.assigned(course_id, user_id):
            self.session.add(TeacherAssignmentModel(course_id=course_id, user_id=user_id))
            await self.session.flush()

    async def unassign(self, course_id: int, user_id: int) -> None:
        await self.session.execute(
            delete(TeacherAssignmentModel).where(
                TeacherAssignmentModel.course_id == course_id,
                TeacherAssignmentModel.user_id == user_id,
            )
        )

    async def reorder(self, items: list[ModuleModel] | list[LessonModel], ids: list[int]) -> None:
        by_id = {item.id: item for item in items}
        # Two flushes avoid immediate unique-position conflicts during swaps.
        temporary = max((item.position for item in items), default=0) + len(items) + 1
        for index, item in enumerate(items):
            item.position = temporary + index
        await self.session.flush()
        for position, item_id in enumerate(ids, start=1):
            by_id[item_id].position = position
        await self.session.flush()

    async def role_lock(self) -> None:
        # Serialize bootstrap and role changes so concurrent demotions cannot remove all admins.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ROLE_LOCK})

    async def set_role(self, user_id: int, role: str) -> UserDTO:
        user = await self.session.scalar(
            select(UserModel)
            .where(UserModel.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert user is not None
        user.role = role
        await self.session.flush()
        return UserDTO.model_validate(user)

    async def has_admin(self) -> bool:
        return (
            await self.session.scalar(
                select(UserModel.id)
                .where(UserModel.role == "admin", UserModel.is_active.is_(True))
                .limit(1)
            )
            is not None
        )

    async def list_users(self, limit: int, offset: int, search: str | None) -> UserPageDTO:
        filters = [UserModel.email.icontains(search, autoescape=True)] if search else []
        total = await self.session.scalar(
            select(func.count()).select_from(UserModel).where(*filters)
        )
        users = await self.session.scalars(
            select(UserModel).where(*filters).order_by(UserModel.id).limit(limit).offset(offset)
        )
        return UserPageDTO(
            items=[UserDTO.model_validate(user) for user in users],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def user_by_email(self, email: str) -> UserDTO | None:
        user = await self.session.scalar(
            select(UserModel).where(func.lower(UserModel.email) == email.lower())
        )
        return UserDTO.model_validate(user) if user else None
