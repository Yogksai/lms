from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import configure_mappers

from migrations.models import Base
from src.app import get_app
from src.auth.dependencies.current_user import get_optional_user
from src.courses.dto import CourseDTO, CoursePageDTO, LessonDTO, LessonOutlineDTO, ModuleDTO
from src.courses.exceptions import ContentNotFound, LessonAccessDenied
from src.courses.models import CourseModel, LessonModel, ModuleModel
from src.courses.repositories.course import CourseRepo
from src.courses.seed_data import COURSES, PYTHON_VIDEO
from src.courses.service.course import CourseService
from src.courses.service.seed import SeedService
from src.enrollment.service import EnrollmentService


@pytest.fixture
def repository() -> AsyncMock:
    repo = AsyncMock(spec=CourseRepo)
    repo.get.return_value = CourseDTO(id=1, slug="python", title="Python", description="Demo")
    repo.list_courses.return_value = CoursePageDTO(
        items=[repo.get.return_value], total=1, limit=20, offset=0
    )
    repo.list_modules.return_value = [
        ModuleDTO(
            id=10,
            course_id=1,
            title="Preview",
            description="Demo",
            position=3,
            lessons=[LessonOutlineDTO(id=100, module_id=10, title="Values", position=1)],
        ),
        ModuleDTO(
            id=20,
            course_id=1,
            title="Restricted",
            description="Demo",
            position=7,
            lessons=[LessonOutlineDTO(id=200, module_id=20, title="Functions", position=1)],
        ),
    ]
    repo.lesson_exists.return_value = True
    repo.get_lesson.return_value = LessonDTO(
        id=100,
        module_id=10,
        title="Values",
        position=1,
        summary="Python values.",
        video_url=PYTHON_VIDEO,
    )
    return repo


@pytest.fixture
def client(repository: AsyncMock) -> TestClient:
    app = get_app()
    app.dependency_overrides[CourseRepo] = lambda: repository
    app.dependency_overrides[get_optional_user] = lambda: None
    app.dependency_overrides[EnrollmentService] = lambda: AsyncMock(spec=EnrollmentService)
    # No lifespan or external connections: this exercises routes with an in-memory repository.
    return TestClient(app)


def test_catalog_pagination_and_search(client: TestClient, repository: AsyncMock) -> None:
    response = client.get("/v1/courses?search=%20Python%20")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["slug"] == "python"
    repository.list_courses.assert_awaited_once_with(20, 0, "Python")


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "search="])
def test_catalog_rejects_invalid_input(client: TestClient, query: str) -> None:
    assert client.get(f"/v1/courses?{query}").status_code == 422


@pytest.mark.parametrize("path", ["/v1/courses/0", "/v1/courses/-1/modules", "/v1/courses/a"])
def test_content_ids_must_be_positive(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 422


def test_detail_exposes_only_outlines(client: TestClient, repository: AsyncMock) -> None:
    response = client.get("/v1/courses/1")
    assert response.status_code == 200
    modules = response.json()["modules"]
    assert [module["is_preview"] for module in modules] == [True, False]
    for module in modules:
        for lesson in module["lessons"]:
            assert "summary" not in lesson
            assert "video_url" not in lesson
    repository.get_lesson.assert_not_awaited()
    assert not repository.list_modules.return_value[0].is_preview


def test_preview_lesson_content(client: TestClient) -> None:
    response = client.get("/v1/courses/1/modules/10/lessons/100")
    assert response.status_code == 200
    assert response.json()["summary"] == "Python values."
    assert response.json()["video_url"] == PYTHON_VIDEO


def test_restricted_lesson_is_not_loaded(client: TestClient, repository: AsyncMock) -> None:
    response = client.get("/v1/courses/1/modules/20/lessons/200")
    assert response.status_code == 403
    assert response.json() == {"detail": "Course access required"}
    repository.get_lesson.assert_not_awaited()


def test_missing_course_including_drafts_returns_404(
    client: TestClient, repository: AsyncMock
) -> None:
    repository.get.return_value = None
    assert client.get("/v1/courses/999").json() == {"detail": "Content not found"}
    assert client.get("/v1/courses/999/modules").status_code == 404
    repository.list_modules.assert_not_awaited()


def test_module_must_belong_to_requested_course(client: TestClient, repository: AsyncMock) -> None:
    assert client.get("/v1/courses/1/modules/999/lessons").status_code == 404
    assert client.get("/v1/courses/1/modules/999/lessons/100").status_code == 404
    repository.lesson_exists.assert_not_awaited()


def test_lesson_must_belong_to_module(client: TestClient, repository: AsyncMock) -> None:
    repository.lesson_exists.return_value = False
    assert client.get("/v1/courses/1/modules/10/lessons/999").status_code == 404
    assert client.get("/v1/courses/1/modules/20/lessons/999").status_code == 404
    repository.get_lesson.assert_not_awaited()


def test_empty_modules_and_lesson_outlines(client: TestClient, repository: AsyncMock) -> None:
    assert client.get("/v1/courses/1/modules/10/lessons").json() == [
        {"id": 100, "module_id": 10, "title": "Values", "position": 1}
    ]
    repository.list_modules.return_value = []
    assert client.get("/v1/courses/1/modules").json() == []


async def test_preview_lookup_handles_removed_lesson(repository: AsyncMock) -> None:
    repository.get_lesson.return_value = None
    with pytest.raises(ContentNotFound):
        await CourseService(repository).get_lesson(1, 10, 100)


async def test_service_protects_later_modules(repository: AsyncMock) -> None:
    with pytest.raises(LessonAccessDenied):
        await CourseService(repository).get_lesson(1, 20, 200)


@pytest.mark.parametrize(
    "url",
    [
        PYTHON_VIDEO,
        "https://youtu.be/rfscVS0vtbw",
        "https://www.youtube.com/embed/rfscVS0vtbw",
        "https://youtube.com/shorts/rfscVS0vtbw",
    ],
)
def test_youtube_urls(url: str) -> None:
    assert (
        LessonDTO(
            id=1, module_id=1, title="Video", position=1, summary="Text", video_url=url
        ).video_url
        == url
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://youtube.com/watch?v=rfscVS0vtbw",
        "https://example.com/watch?v=rfscVS0vtbw",
        "https://youtube.com.evil.test/watch?v=rfscVS0vtbw",
        "https://youtube.com/watch",
        "https://youtu.be/",
        "https://user@youtube.com/watch?v=rfscVS0vtbw",
        "https://youtube.com:443/watch?v=rfscVS0vtbw",
        "https://youtu.be/rfscVS0vtbw/extra",
    ],
)
def test_video_validation_rejects_unsupported_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        LessonDTO(id=1, module_id=1, title="Video", position=1, summary="Text", video_url=url)


@pytest.mark.parametrize("changes", [{"title": " "}, {"summary": " "}, {"position": 0}])
def test_lesson_validation(changes: dict[str, object]) -> None:
    values = {
        "id": 1,
        "module_id": 1,
        "title": "Title",
        "summary": "Summary",
        "position": 1,
        "video_url": PYTHON_VIDEO,
    }
    with pytest.raises(ValidationError):
        LessonDTO.model_validate(values | changes)


def test_seed_data_is_valid_and_positions_are_unique() -> None:
    for course in COURSES:
        SeedService.validate(course)
    with pytest.raises(ValueError, match="Module positions"):
        SeedService.validate(replace(COURSES[0], modules=(COURSES[0].modules[0],) * 2))
    module = COURSES[0].modules[0]
    with pytest.raises(ValueError, match="Lesson positions"):
        SeedService.validate(
            replace(COURSES[0], modules=(replace(module, lessons=(module.lessons[0],) * 2),))
        )


async def test_seed_service_owns_transaction_and_skips_existing(repository: AsyncMock) -> None:
    session = MagicMock()
    session.begin.return_value = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    repository.create_if_missing.side_effect = [True, False]
    assert await SeedService(session, repository).seed(COURSES) == 1
    session.begin.assert_called_once()
    session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)
    assert repository.create_if_missing.await_count == 2


async def test_invalid_seed_is_rejected_before_transaction(repository: AsyncMock) -> None:
    session = MagicMock()
    with pytest.raises(ValueError):
        await SeedService(session, repository).seed((replace(COURSES[0], modules=()),))
    session.begin.assert_not_called()
    repository.create_if_missing.assert_not_awaited()


def test_course_model_constraints_and_relationships() -> None:
    configure_mappers()
    assert {"courses", "course_modules", "lessons"} <= set(Base.metadata.tables)
    assert CourseModel.modules.property.lazy == "raise"
    assert ModuleModel.lessons.property.lazy == "raise"
    for model, column in [(ModuleModel, "course_id"), (LessonModel, "module_id")]:
        foreign_key = next(iter(model.__table__.c[column].foreign_keys))
        assert foreign_key.ondelete == "CASCADE"
        assert any(
            constraint.name and constraint.name.startswith("uq_")
            for constraint in model.__table__.constraints
        )


async def test_repository_catalog_filters_drafts_and_escapes_search() -> None:
    session = AsyncMock()
    session.scalar.return_value = 0
    session.scalars.return_value = []
    page = await CourseRepo(session).list_courses(10, 5, "100%_Python")
    assert page.total == 0
    query = session.scalars.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "courses.is_published IS true" in str(query)
    assert "ORDER BY courses.id" in str(query)
    assert "100/%/_Python" in query.params.values()


async def test_repository_lesson_query_checks_full_hierarchy() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    assert await CourseRepo(session).get_lesson(1, 2, 3) is None
    query = str(session.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "course_modules.course_id =" in query
    assert "lessons.module_id =" in query
    assert "lessons.id =" in query
    assert "courses.is_published IS true" in query


async def test_seed_repository_skips_without_overwriting_or_committing() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    assert not await CourseRepo(session).create_if_missing(COURSES[0])
    query = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (slug) DO NOTHING" in query
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_seed_repository_creates_ordered_children_without_committing() -> None:
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = 42
    session.execute.return_value = result

    async def assign_module_ids() -> None:
        for index, call in enumerate(session.add.call_args_list, start=1):
            call.args[0].id = index

    session.flush.side_effect = assign_module_ids
    assert await CourseRepo(session).create_if_missing(COURSES[0])
    modules = [call.args[0] for call in session.add.call_args_list]
    assert [module.course_id for module in modules] == [42, 42]
    assert [module.position for module in modules] == [1, 2]
    lessons = [lesson for call in session.add_all.call_args_list for lesson in call.args[0]]
    assert [lesson.module_id for lesson in lessons] == [1, 1, 2, 2]
    assert [lesson.position for lesson in lessons] == [1, 2, 1, 2]
    assert session.flush.await_count == 3
    session.commit.assert_not_awaited()


async def test_seed_failure_exits_transaction_with_error(repository: AsyncMock) -> None:
    session = MagicMock(spec=AsyncSession)
    session.begin.return_value.__aexit__.return_value = False
    repository.create_if_missing.side_effect = RuntimeError("Seed write failed")
    with pytest.raises(RuntimeError, match="Seed write failed"):
        await SeedService(session, repository).seed(COURSES)
    exit_args = session.begin.return_value.__aexit__.call_args.args
    assert exit_args[0] is RuntimeError
    assert str(exit_args[1]) == "Seed write failed"
