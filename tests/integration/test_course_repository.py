from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.courses.models import CourseModel, LessonModel, ModuleModel
from src.courses.repositories.course import CourseRepo
from src.courses.seed_data import COURSES
from src.courses.service.course import CourseService
from src.courses.service.seed import SeedService

pytestmark = pytest.mark.integration


async def test_seed_is_repeatable_and_preserves_existing_content(session: AsyncSession) -> None:
    repository = CourseRepo(session)
    seeder = SeedService(session, repository)
    assert await seeder.seed(COURSES) == 2
    changed = replace(COURSES[0], title="Do not overwrite existing titles")
    assert await seeder.seed((changed, COURSES[1])) == 0
    page = await repository.list_courses(100, 0, "(demo)")
    assert len(page.items) == 2
    assert page.items[0].title == COURSES[0].title
    assert await session.scalar(select(func.count()).select_from(ModuleModel)) == 4
    assert await session.scalar(select(func.count()).select_from(LessonModel)) == 6


async def test_published_catalog_and_ordered_preview(session: AsyncSession) -> None:
    repository = CourseRepo(session)
    draft = replace(COURSES[0], slug="draft-course", is_published=False)
    await SeedService(session, repository).seed((*COURSES, draft))
    page = await repository.list_courses(1, 0, "foundations")
    assert page.total == 1
    assert len(page.items) == 1
    course_id = page.items[0].id
    modules = await CourseService(repository).list_modules(course_id)
    assert [module.position for module in modules] == [1, 2]
    assert [module.is_preview for module in modules] == [True, False]
    assert [lesson.position for lesson in modules[0].lessons] == [1, 2]
    lesson = await repository.get_lesson(course_id, modules[0].id, modules[0].lessons[0].id)
    assert lesson is not None
    assert lesson.summary == COURSES[0].modules[0].lessons[0].summary
    assert await repository.get_lesson(course_id, modules[1].id, lesson.id) is None
    draft_id = await session.scalar(
        select(CourseModel.id).where(CourseModel.slug == "draft-course")
    )
    assert draft_id is not None
    assert await repository.get(draft_id) is None
    assert await repository.list_modules(draft_id) == []


async def test_module_position_constraint(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        async with session.begin():
            course = CourseModel(slug="constraint-demo", title="Demo", description="Demo")
            session.add(course)
            await session.flush()
            session.add(
                ModuleModel(course_id=course.id, title="Invalid", description="Demo", position=0)
            )
            await session.flush()
