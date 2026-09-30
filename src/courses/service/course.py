from src.courses.dependencies.repository import ICourseRepository
from src.courses.dto import (
    CourseDetailDTO,
    CourseDTO,
    CoursePageDTO,
    LessonDTO,
    LessonOutlineDTO,
    ModuleDTO,
)
from src.courses.exceptions import ContentNotFound, LessonAccessDenied


class CourseService:
    def __init__(self, repository: ICourseRepository) -> None:
        self.repository = repository

    async def list_courses(self, limit: int, offset: int, search: str | None) -> CoursePageDTO:
        return await self.repository.list_courses(limit, offset, search)

    async def get(self, course_id: int) -> CourseDTO:
        course = await self.repository.get(course_id)
        if course is None:
            raise ContentNotFound
        return course

    async def list_modules(self, course_id: int) -> list[ModuleDTO]:
        await self.get(course_id)
        modules = await self.repository.list_modules(course_id)
        return self.preview_modules(modules)

    @staticmethod
    def preview_modules(modules: list[ModuleDTO]) -> list[ModuleDTO]:
        return [
            module.model_copy(update={"is_preview": index == 0})
            for index, module in enumerate(modules)
        ]

    async def get_detail(self, course_id: int) -> CourseDetailDTO:
        course = await self.get(course_id)
        modules = self.preview_modules(await self.repository.list_modules(course_id))
        return CourseDetailDTO(**course.model_dump(), modules=modules)

    async def list_lessons(self, course_id: int, module_id: int) -> list[LessonOutlineDTO]:
        modules = await self.list_modules(course_id)
        for module in modules:
            if module.id == module_id:
                return module.lessons
        raise ContentNotFound

    async def get_lesson(self, course_id: int, module_id: int, lesson_id: int) -> LessonDTO:
        modules = await self.list_modules(course_id)
        module = next((item for item in modules if item.id == module_id), None)
        if module is None or not await self.repository.lesson_exists(module_id, lesson_id):
            raise ContentNotFound
        # TODO: extend preview access with enrollment grants when that domain is implemented.
        if not module.is_preview:
            raise LessonAccessDenied
        lesson = await self.repository.get_lesson(course_id, module_id, lesson_id)
        if lesson is None:
            raise ContentNotFound
        return lesson
