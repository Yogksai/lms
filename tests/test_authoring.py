from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dto import RegisterDTO, UserDTO
from src.authoring.dto import CourseWriteDTO, LessonWriteDTO, OrderDTO, RoleDTO
from src.authoring.repository import AuthoringRepo
from src.authoring.service import AuthoringService
from src.courses.models import CourseModel, LessonModel, ModuleModel


@pytest.fixture
def teacher() -> UserDTO:
    return UserDTO(
        id=1, name="Teacher", email="teacher@example.com", is_active=True, role="teacher"
    )


@pytest.fixture
def authoring(teacher: UserDTO) -> AuthoringService:
    session = MagicMock(spec=AsyncSession)
    repository = AsyncMock(spec=AuthoringRepo)
    repository.user.return_value = teacher
    repository.assigned.return_value = True
    lesson = LessonModel(
        id=30,
        module_id=20,
        title="Lesson",
        summary="Summary",
        video_url="https://youtu.be/dQw4w9WgXcQ",
        position=1,
    )
    module = ModuleModel(
        id=20, course_id=10, title="Module", description="", position=1, lessons=[lesson]
    )
    repository.course.return_value = CourseModel(
        id=10,
        slug="test",
        title="Test",
        description="",
        is_published=False,
        is_archived=False,
        revision=1,
        modules=[module],
    )
    return AuthoringService(session, repository)


@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
async def test_roles_gate_authoring(
    authoring: AuthoringService, teacher: UserDTO, role: str
) -> None:
    authoring.repository.user.return_value = teacher.model_copy(update={"role": role})
    if role == "student":
        with pytest.raises(HTTPException) as error:
            await authoring.get(teacher, 10)
        assert error.value.status_code == 403
        authoring.repository.course.assert_not_awaited()
    else:
        await authoring.get(teacher, 10)
        authoring.repository.detail.assert_awaited_once()


async def test_live_role_is_read_instead_of_trusting_caller(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    authoring.repository.user.return_value = teacher.model_copy(update={"role": "student"})
    with pytest.raises(HTTPException) as error:
        await authoring.get(teacher, 10)
    assert error.value.status_code == 403


@pytest.mark.parametrize("missing", ["user", "inactive", "course", "assignment"])
async def test_authoring_denies_missing_or_unassigned_content(
    authoring: AuthoringService, teacher: UserDTO, missing: str
) -> None:
    if missing == "user":
        authoring.repository.user.return_value = None
    elif missing == "inactive":
        authoring.repository.user.return_value = teacher.model_copy(update={"is_active": False})
    elif missing == "course":
        authoring.repository.course.return_value = None
    else:
        authoring.repository.assigned.return_value = False
    with pytest.raises(HTTPException) as error:
        await authoring.get(teacher, 10)
    assert error.value.status_code == (401 if missing in {"user", "inactive"} else 404)


async def test_admin_can_access_unassigned_course(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    authoring.repository.user.return_value = teacher.model_copy(update={"role": "admin"})
    authoring.repository.assigned.return_value = False
    await authoring.get(teacher, 10)
    authoring.repository.assigned.assert_not_awaited()


@pytest.mark.parametrize("state", ["stale", "published", "archived"])
async def test_mutations_reject_stale_and_non_draft_courses(
    authoring: AuthoringService, teacher: UserDTO, state: str
) -> None:
    course = authoring.repository.course.return_value
    course.is_published = state == "published"
    course.is_archived = state == "archived"
    action = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await authoring.edit(teacher, 10, 2 if state == "stale" else 1, action)
    assert error.value.status_code == 409
    action.assert_not_awaited()
    authoring.repository.course.assert_awaited_once_with(10, lock=True)


async def test_draft_edit_increments_revision_and_commits(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    await authoring.update_course(teacher, 10, 1, CourseWriteDTO(slug="new", title="New"))
    course = authoring.repository.course.return_value
    assert course.title == "New" and course.slug == "new" and course.revision == 2
    authoring.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.parametrize("status", ["draft", "published", "archived"])
async def test_course_status_transitions(
    authoring: AuthoringService, teacher: UserDTO, status: str
) -> None:
    await authoring.change_status(teacher, 10, 1, status)
    course = authoring.repository.course.return_value
    assert course.is_published == (status == "published")
    assert course.is_archived == (status == "archived")


@pytest.mark.parametrize("reason", ["archived", "no-modules", "empty-module"])
async def test_publish_requires_restored_complete_course(
    authoring: AuthoringService, teacher: UserDTO, reason: str
) -> None:
    course = authoring.repository.course.return_value
    if reason == "archived":
        course.is_archived = True
    elif reason == "no-modules":
        course.modules = []
    else:
        course.modules[0].lessons = []
    with pytest.raises(HTTPException) as error:
        await authoring.change_status(teacher, 10, 1, "published")
    assert error.value.status_code == (409 if reason == "archived" else 422)


@pytest.mark.parametrize("ids", [[], [999], [20, 999]])
async def test_order_must_be_exact_child_set(
    authoring: AuthoringService, teacher: UserDTO, ids: list[int]
) -> None:
    with pytest.raises(HTTPException) as error:
        await authoring.reorder(teacher, 10, 1, OrderDTO(ids=ids))
    assert error.value.status_code == 422
    authoring.repository.reorder.assert_not_awaited()


async def test_order_uses_transactional_repository(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    await authoring.reorder(teacher, 10, 1, OrderDTO(ids=[30]), module_id=20)
    authoring.repository.reorder.assert_awaited_once_with(
        authoring.repository.course.return_value.modules[0].lessons, [30]
    )


async def test_nested_lesson_cannot_be_edited_through_another_parent(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    with pytest.raises(HTTPException) as error:
        await authoring.delete_lesson(teacher, 10, 999, 30, 1)
    assert error.value.status_code == 404
    authoring.session.delete.assert_not_awaited()


async def test_teacher_cannot_manage_assignments_or_roles(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    for action in [
        authoring.assign(teacher, 10, 1, 2),
        authoring.change_role(teacher, 2, RoleDTO(role="admin")),
    ]:
        with pytest.raises(HTTPException) as error:
            await action
        assert error.value.status_code == 403
    authoring.repository.set_role.assert_not_awaited()
    authoring.repository.assign.assert_not_awaited()


async def test_admin_cannot_change_own_role(authoring: AuthoringService, teacher: UserDTO) -> None:
    authoring.repository.user.return_value = teacher.model_copy(update={"role": "admin"})
    with pytest.raises(HTTPException) as error:
        await authoring.change_role(teacher, teacher.id, RoleDTO(role="student"))
    assert error.value.status_code == 409
    authoring.repository.role_lock.assert_awaited_once()


async def test_admin_role_change_rereads_authority_after_lock(
    authoring: AuthoringService, teacher: UserDTO
) -> None:
    admin = teacher.model_copy(update={"role": "admin"})
    target = teacher.model_copy(update={"id": 2, "role": "student"})
    authoring.repository.user.side_effect = [admin, target]
    await authoring.change_role(admin, 2, RoleDTO(role="teacher"))
    authoring.repository.set_role.assert_awaited_once_with(2, "teacher")
    assert [call[0] for call in authoring.repository.mock_calls][:3] == [
        "role_lock",
        "user",
        "user",
    ]


async def test_teacher_creation_assigns_self(authoring: AuthoringService, teacher: UserDTO) -> None:
    async def flush() -> None:
        authoring.session.add.call_args.args[0].id = 10

    authoring.session.flush.side_effect = flush
    await authoring.create(teacher, CourseWriteDTO(slug="test", title="Test"))
    authoring.repository.assign.assert_awaited_once_with(10, teacher.id)


async def test_reordering_flushes_temporary_positions_before_final_positions() -> None:
    session = MagicMock(spec=AsyncSession)
    modules = [ModuleModel(id=1, position=1), ModuleModel(id=2, position=2)]
    snapshots = []

    async def flush() -> None:
        snapshots.append([module.position for module in modules])

    session.flush.side_effect = flush
    await AuthoringRepo(session).reorder(modules, [2, 1])
    assert snapshots == [[5, 6], [2, 1]]


@pytest.mark.parametrize("ids", [[1, 1], [-1], [0]])
def test_order_input_rejects_duplicate_and_non_positive_ids(ids: list[int]) -> None:
    with pytest.raises(ValidationError):
        OrderDTO(ids=ids)


def test_authoring_inputs_reject_role_escalation_and_unsafe_video() -> None:
    with pytest.raises(ValidationError):
        RegisterDTO(name="Name", email="test@example.com", password="password1", role="admin")
    with pytest.raises(ValidationError):
        LessonWriteDTO(title="Test", summary="Text", video_url="https://evil.example/video")
    with pytest.raises(ValidationError):
        CourseWriteDTO(slug="bad slug", title="Test")
