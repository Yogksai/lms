from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.auth.dto import UserDTO
from src.authoring.dependencies import IAuthoringRepo
from src.authoring.dto import (
    CourseWriteDTO,
    EditorCourseDTO,
    EditorCoursePageDTO,
    LessonWriteDTO,
    ModuleWriteDTO,
    OrderDTO,
    RoleDTO,
    Status,
    UserPageDTO,
)
from src.config.db.session import ISession
from src.courses.models import CourseModel, LessonModel, ModuleModel


class AuthoringService:
    def __init__(self, session: ISession, repository: IAuthoringRepo) -> None:
        self.session = session
        self.repository = repository

    async def actor(self, user: UserDTO, admin: bool = False) -> UserDTO:
        current = await self.repository.user(user.id)
        if current is None or not current.is_active:
            raise HTTPException(401, "Account unavailable")
        if current.role not in ({"admin"} if admin else {"teacher", "admin"}):
            raise HTTPException(403, "Authoring permission required")
        return current

    async def authorized_course(
        self, user: UserDTO, course_id: int, lock: bool = False
    ) -> CourseModel:
        actor = await self.actor(user)
        course = await self.repository.course(course_id, lock=lock)
        if course is None or (
            actor.role != "admin" and not await self.repository.assigned(course_id, actor.id)
        ):
            raise HTTPException(404, "Assigned course not found")
        return course

    async def list_courses(self, user: UserDTO, limit: int, offset: int) -> EditorCoursePageDTO:
        async with self.session.begin():
            return await self.repository.list_courses(await self.actor(user), limit, offset)

    async def get(self, user: UserDTO, course_id: int) -> EditorCourseDTO:
        async with self.session.begin():
            return await self.repository.detail(await self.authorized_course(user, course_id))

    async def create(self, user: UserDTO, data: CourseWriteDTO) -> EditorCourseDTO:
        try:
            async with self.session.begin():
                actor = await self.actor(user)
                course = CourseModel(
                    **data.model_dump(), is_published=False, is_archived=False, revision=1
                )
                self.session.add(course)
                await self.session.flush()
                if actor.role == "teacher":
                    await self.repository.assign(course.id, actor.id)
                loaded = await self.repository.course(course.id)
                assert loaded is not None
                return await self.repository.detail(loaded)
        except IntegrityError as error:
            self.conflict(error)
            raise

    @staticmethod
    def conflict(error: IntegrityError) -> None:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Slug or position already exists") from error

    async def edit(
        self,
        user: UserDTO,
        course_id: int,
        revision: int,
        action: Callable[[CourseModel], Awaitable[None]],
        *,
        draft: bool = True,
        admin: bool = False,
    ) -> EditorCourseDTO:
        try:
            async with self.session.begin():
                if admin:
                    await self.actor(user, admin=True)
                course = await self.authorized_course(user, course_id, lock=True)
                if course.revision != revision:
                    raise HTTPException(409, "Course changed; reload before saving")
                if draft and (course.is_published or course.is_archived):
                    raise HTTPException(409, "Return the course to draft before editing")
                await action(course)
                course.revision += 1
                await self.session.flush()
                loaded = await self.repository.course(course_id)
                assert loaded is not None
                return await self.repository.detail(loaded)
        except IntegrityError as error:
            self.conflict(error)
            raise

    async def update_course(
        self, user: UserDTO, course_id: int, revision: int, data: CourseWriteDTO
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            course.slug, course.title, course.description = data.slug, data.title, data.description

        return await self.edit(user, course_id, revision, action)

    @staticmethod
    def module(course: CourseModel, module_id: int) -> ModuleModel:
        module = next((item for item in course.modules if item.id == module_id), None)
        if module is None:
            raise HTTPException(404, "Module not found in this course")
        return module

    @staticmethod
    def lesson(module: ModuleModel, lesson_id: int) -> LessonModel:
        lesson = next((item for item in module.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise HTTPException(404, "Lesson not found in this module")
        return lesson

    @staticmethod
    def next_position(items: list[ModuleModel] | list[LessonModel]) -> int:
        position = max((item.position for item in items), default=0) + 1
        if len(items) >= 1000 or position > 2_147_480_000:
            raise HTTPException(409, "Content ordering limit reached")
        return position

    async def add_module(
        self, user: UserDTO, course_id: int, revision: int, data: ModuleWriteDTO
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            self.session.add(
                ModuleModel(
                    course_id=course.id,
                    position=self.next_position(course.modules),
                    **data.model_dump(),
                )
            )

        return await self.edit(user, course_id, revision, action)

    async def update_module(
        self, user: UserDTO, course_id: int, module_id: int, revision: int, data: ModuleWriteDTO
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            module = self.module(course, module_id)
            module.title, module.description = data.title, data.description

        return await self.edit(user, course_id, revision, action)

    async def delete_module(
        self, user: UserDTO, course_id: int, module_id: int, revision: int
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            await self.session.delete(self.module(course, module_id))

        return await self.edit(user, course_id, revision, action)

    async def add_lesson(
        self, user: UserDTO, course_id: int, module_id: int, revision: int, data: LessonWriteDTO
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            module = self.module(course, module_id)
            self.session.add(
                LessonModel(
                    module_id=module.id,
                    position=self.next_position(module.lessons),
                    **data.model_dump(),
                )
            )

        return await self.edit(user, course_id, revision, action)

    async def update_lesson(
        self,
        user: UserDTO,
        course_id: int,
        module_id: int,
        lesson_id: int,
        revision: int,
        data: LessonWriteDTO,
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            lesson = self.lesson(self.module(course, module_id), lesson_id)
            lesson.title, lesson.summary, lesson.video_url = (
                data.title,
                data.summary,
                data.video_url,
            )

        return await self.edit(user, course_id, revision, action)

    async def delete_lesson(
        self, user: UserDTO, course_id: int, module_id: int, lesson_id: int, revision: int
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            await self.session.delete(self.lesson(self.module(course, module_id), lesson_id))

        return await self.edit(user, course_id, revision, action)

    async def reorder(
        self,
        user: UserDTO,
        course_id: int,
        revision: int,
        data: OrderDTO,
        module_id: int | None = None,
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            items = (
                self.module(course, module_id).lessons if module_id is not None else course.modules
            )
            if set(data.ids) != {item.id for item in items}:
                raise HTTPException(422, "Order must include every child ID exactly once")
            if max((item.position for item in items), default=0) > 2_147_480_000:
                raise HTTPException(409, "Content ordering limit reached")
            await self.repository.reorder(items, data.ids)

        return await self.edit(user, course_id, revision, action)

    async def change_status(
        self, user: UserDTO, course_id: int, revision: int, status: Status
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            if status == "published":
                if course.is_archived:
                    raise HTTPException(409, "Restore archived courses to draft first")
                if not course.modules or any(not module.lessons for module in course.modules):
                    raise HTTPException(422, "Publishing requires a lesson in every module")
                for module in course.modules:
                    for lesson in module.lessons:
                        LessonWriteDTO.model_validate(lesson, from_attributes=True)
            course.is_published = status == "published"
            course.is_archived = status == "archived"

        return await self.edit(user, course_id, revision, action, draft=False)

    async def assign(
        self, user: UserDTO, course_id: int, revision: int, teacher_id: int, remove: bool = False
    ) -> EditorCourseDTO:
        async def action(course: CourseModel) -> None:
            if remove:
                await self.repository.unassign(course.id, teacher_id)
            else:
                teacher = await self.repository.user(teacher_id)
                if teacher is None:
                    raise HTTPException(404, "Teacher not found")
                if not teacher.is_active or teacher.role != "teacher":
                    raise HTTPException(422, "Assignment requires an active teacher")
                await self.repository.assign(course.id, teacher_id)

        return await self.edit(user, course_id, revision, action, draft=False, admin=True)

    async def list_users(
        self, user: UserDTO, limit: int, offset: int, search: str | None
    ) -> UserPageDTO:
        async with self.session.begin():
            await self.actor(user, admin=True)
            return await self.repository.list_users(limit, offset, search)

    async def change_role(self, user: UserDTO, user_id: int, data: RoleDTO) -> UserDTO:
        async with self.session.begin():
            await self.repository.role_lock()
            await self.actor(user, admin=True)
            if user.id == user_id:
                raise HTTPException(409, "Admins cannot change their own role")
            target = await self.repository.user(user_id)
            if target is None:
                raise HTTPException(404, "User not found")
            if not target.is_active and data.role != "student":
                raise HTTPException(422, "Privileged roles require an active account")
            return await self.repository.set_role(user_id, data.role)
