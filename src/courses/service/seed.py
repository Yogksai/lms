from src.config.db.session import ISession
from src.courses.dependencies.repository import ICourseRepository
from src.courses.dto import CourseDTO, LessonDTO, ModuleDTO
from src.courses.entities import CourseEntity


class SeedService:
    def __init__(self, session: ISession, repository: ICourseRepository) -> None:
        self.session = session
        self.repository = repository

    async def seed(self, courses: tuple[CourseEntity, ...]) -> int:
        for course in courses:
            self.validate(course)
        created = 0
        async with self.session.begin():
            for course in courses:
                created += int(await self.repository.create_if_missing(course))
        return created

    @staticmethod
    def validate(course: CourseEntity) -> None:
        CourseDTO(id=1, slug=course.slug, title=course.title, description=course.description)
        if not course.modules:
            raise ValueError("Seed courses must contain modules")
        if len({module.position for module in course.modules}) != len(course.modules):
            raise ValueError("Module positions must be unique within a course")
        for module in course.modules:
            ModuleDTO(
                id=1,
                course_id=1,
                title=module.title,
                description=module.description,
                position=module.position,
            )
            if not module.lessons:
                raise ValueError("Seed modules must contain lessons")
            if len({lesson.position for lesson in module.lessons}) != len(module.lessons):
                raise ValueError("Lesson positions must be unique within a module")
            for lesson in module.lessons:
                LessonDTO(
                    id=1,
                    module_id=1,
                    title=lesson.title,
                    position=lesson.position,
                    summary=lesson.summary,
                    video_url=lesson.video_url,
                )
