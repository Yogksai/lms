from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from src.config.db.session import ISession
from src.courses.dto import CourseDTO, CoursePageDTO, LessonDTO, ModuleDTO
from src.courses.entities import CourseEntity
from src.courses.models import CourseModel, LessonModel, ModuleModel


class CourseRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def list_courses(self, limit: int, offset: int, search: str | None) -> CoursePageDTO:
        filters: list[ColumnElement[bool]] = [CourseModel.is_published.is_(True)]
        if search:
            filters.append(CourseModel.title.icontains(search, autoescape=True))
        total = await self.session.scalar(
            select(func.count()).select_from(CourseModel).where(*filters)
        )
        result = await self.session.scalars(
            select(CourseModel).where(*filters).order_by(CourseModel.id).limit(limit).offset(offset)
        )
        return CoursePageDTO(
            items=[CourseDTO.model_validate(course) for course in result],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def get(self, course_id: int) -> CourseDTO | None:
        instance = await self.session.scalar(
            select(CourseModel).where(
                CourseModel.id == course_id, CourseModel.is_published.is_(True)
            )
        )
        return CourseDTO.model_validate(instance) if instance is not None else None

    async def list_modules(self, course_id: int) -> list[ModuleDTO]:
        result = await self.session.scalars(
            select(ModuleModel)
            .join(CourseModel)
            .where(ModuleModel.course_id == course_id, CourseModel.is_published.is_(True))
            .options(
                selectinload(ModuleModel.lessons).load_only(
                    LessonModel.id,
                    LessonModel.module_id,
                    LessonModel.title,
                    LessonModel.position,
                    raiseload=True,
                )
            )
            .order_by(ModuleModel.position, ModuleModel.id)
        )
        return [ModuleDTO.model_validate(module) for module in result]

    async def get_lesson(self, course_id: int, module_id: int, lesson_id: int) -> LessonDTO | None:
        instance = await self.session.scalar(
            select(LessonModel)
            .join(ModuleModel)
            .join(CourseModel)
            .where(
                LessonModel.id == lesson_id,
                LessonModel.module_id == module_id,
                ModuleModel.course_id == course_id,
                CourseModel.is_published.is_(True),
            )
        )
        return LessonDTO.model_validate(instance) if instance is not None else None

    async def lesson_exists(self, module_id: int, lesson_id: int) -> bool:
        return (
            await self.session.scalar(
                select(LessonModel.id).where(
                    LessonModel.id == lesson_id, LessonModel.module_id == module_id
                )
            )
            is not None
        )

    async def create_if_missing(self, course: CourseEntity) -> bool:
        result = await self.session.execute(
            insert(CourseModel)
            .values(
                slug=course.slug,
                title=course.title,
                description=course.description,
                is_published=course.is_published,
            )
            .on_conflict_do_nothing(index_elements=[CourseModel.slug])
            .returning(CourseModel.id)
        )
        course_id = result.scalar_one_or_none()
        if course_id is None:
            return False
        for module in course.modules:
            instance = ModuleModel(
                course_id=course_id,
                title=module.title,
                description=module.description,
                position=module.position,
            )
            self.session.add(instance)
            await self.session.flush()
            self.session.add_all(
                [
                    LessonModel(
                        module_id=instance.id,
                        title=lesson.title,
                        position=lesson.position,
                        summary=lesson.summary,
                        video_url=lesson.video_url,
                    )
                    for lesson in module.lessons
                ]
            )
        await self.session.flush()
        return True
