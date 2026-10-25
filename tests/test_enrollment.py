from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dto import UserDTO
from src.enrollment.dto import DecisionDTO, GrantDTO, GrantInputDTO, RequestDTO, RequestInputDTO
from src.enrollment.repository import CourseState, EnrollmentRepo, GrantAccess
from src.enrollment.service import EnrollmentService


@pytest.fixture
def student() -> UserDTO:
    return UserDTO(id=1, name="Student", email="student@example.com", is_active=True)


@pytest.fixture
def enrollment(student: UserDTO) -> EnrollmentService:
    session = MagicMock(spec=AsyncSession)
    repository = AsyncMock(spec=EnrollmentRepo)
    repository.course.return_value = CourseState(10, True)
    repository.user.return_value = student
    repository.enrolled.return_value = True
    repository.assigned.return_value = False
    repository.grant_access.return_value = GrantAccess([], None)
    repository.latest_request.return_value = None
    repository.own_grants.return_value = []
    now = datetime.now(UTC)
    repository.request.return_value = RequestDTO(
        id=20,
        course_id=10,
        user_id=1,
        message="Please",
        status="pending",
        created_at=now,
        decided_at=None,
        decided_by=None,
        decision_note="",
    )
    repository.grant.return_value = GrantDTO(
        id=30,
        course_id=10,
        user_id=1,
        source="teacher_approval",
        request_id=20,
        granted_by=2,
        created_at=now,
        expires_at=now + timedelta(days=90),
        revoked_at=None,
        revoked_by=None,
    )
    return EnrollmentService(session, repository)


async def test_enrollment_does_not_unlock_content(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    result = await enrollment.enroll(student, 10)
    assert result.enrolled and not result.full_access
    enrollment.repository.enroll.assert_awaited_once_with(10, 1)
    enrollment.repository.course.assert_awaited_once_with(10, lock=True)
    enrollment.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.parametrize(
    "reason", ["not-enrolled", "no-grant", "inactive", "missing-user", "unpublished"]
)
async def test_denied_full_access(
    enrollment: EnrollmentService, student: UserDTO, reason: str
) -> None:
    if reason == "not-enrolled":
        enrollment.repository.enrolled.return_value = False
        enrollment.repository.grant_access.return_value = GrantAccess(
            ["admin_grant"], datetime.now(UTC) + timedelta(days=1)
        )
    elif reason == "inactive":
        enrollment.repository.user.return_value = student.model_copy(update={"is_active": False})
    elif reason == "missing-user":
        enrollment.repository.user.return_value = None
    elif reason == "unpublished":
        enrollment.repository.course.return_value = CourseState(10, False)
    if reason in {"inactive", "missing-user", "unpublished"}:
        with pytest.raises(HTTPException) as error:
            await enrollment.can_read(student, 10)
        assert error.value.status_code == (404 if reason == "unpublished" else 401)
    else:
        assert not await enrollment.can_read(student, 10)


@pytest.mark.parametrize(
    "role,assigned,expected",
    [
        ("student", True, False),
        ("teacher", False, False),
        ("teacher", True, True),
        ("admin", False, True),
    ],
)
async def test_staff_access_is_scoped_and_does_not_require_enrollment(
    enrollment: EnrollmentService, student: UserDTO, role: str, assigned: bool, expected: bool
) -> None:
    enrollment.repository.user.return_value = student.model_copy(update={"role": role})
    enrollment.repository.assigned.return_value = assigned
    enrollment.repository.enrolled.return_value = False
    assert await enrollment.can_read(student, 10) == expected


async def test_independent_access_sources_and_effective_expiry(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    expires = datetime.now(UTC) + timedelta(days=100)
    enrollment.repository.grant_access.return_value = GrantAccess(
        ["teacher_approval", "admin_grant"], expires
    )
    status = await enrollment.status(student, 10)
    assert status.full_access and set(status.reasons) == {"teacher_approval", "admin_grant"}
    assert status.expires_at == expires
    enrollment.repository.grant_access.return_value = GrantAccess(["admin_grant"], expires)
    assert await enrollment.can_read(student, 10)


async def test_expired_or_revoked_history_does_not_unlock(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    grant = enrollment.repository.grant.return_value.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    enrollment.repository.own_grants.return_value = [grant]
    result = await enrollment.status(student, 10)
    assert result.grants and not result.full_access and result.expires_at is None


async def test_unpublished_enrolled_course_reports_unavailable(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    enrollment.repository.course.return_value = CourseState(10, False)
    enrollment.repository.grant_access.return_value = GrantAccess(
        ["teacher_approval"], datetime.now(UTC) + timedelta(days=1)
    )
    result = await enrollment.status(student, 10)
    assert not result.available and not result.full_access and result.reasons == []
    enrollment.repository.enrolled.return_value = False
    with pytest.raises(HTTPException) as error:
        await enrollment.status(student, 10)
    assert error.value.status_code == 404


async def test_pending_request_retry_is_idempotent(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    enrollment.repository.latest_request.return_value = enrollment.repository.request.return_value
    status = await enrollment.request_access(student, 10, RequestInputDTO(message="Duplicate"))
    assert status.request.status == "pending"
    enrollment.repository.create_request.assert_not_awaited()


async def test_request_requires_enrollment(enrollment: EnrollmentService, student: UserDTO) -> None:
    enrollment.repository.enrolled.return_value = False
    with pytest.raises(HTTPException) as error:
        await enrollment.request_access(student, 10, RequestInputDTO())
    assert error.value.status_code == 409


async def test_request_with_active_access_is_rejected(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    enrollment.repository.grant_access.return_value = GrantAccess(
        ["admin_grant"], datetime.now(UTC) + timedelta(days=1)
    )
    with pytest.raises(HTTPException) as error:
        await enrollment.request_access(student, 10, RequestInputDTO())
    assert error.value.status_code == 409


async def test_rejected_request_can_be_resubmitted(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    enrollment.repository.latest_request.return_value = (
        enrollment.repository.request.return_value.model_copy(update={"status": "rejected"})
    )
    await enrollment.request_access(student, 10, RequestInputDTO(message="New request"))
    enrollment.repository.create_request.assert_awaited_once_with(10, 1, "New request")


@pytest.mark.parametrize("reason", ["other-user", "missing", "already-decided"])
async def test_cancel_is_owned_and_pending_only(
    enrollment: EnrollmentService, student: UserDTO, reason: str
) -> None:
    if reason == "missing":
        enrollment.repository.request.return_value = None
    else:
        enrollment.repository.request.return_value = (
            enrollment.repository.request.return_value.model_copy(
                update={"user_id": 2} if reason == "other-user" else {"status": "approved"}
            )
        )
    with pytest.raises(HTTPException) as error:
        await enrollment.cancel(student, 10, 20)
    assert error.value.status_code == (409 if reason == "already-decided" else 404)
    enrollment.repository.decide.assert_not_awaited()


async def test_leave_revokes_learner_grants_without_deleting_history(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    await enrollment.leave(student, 10)
    args = enrollment.repository.leave.call_args.args
    assert args[:2] == (10, 1) and args[2].tzinfo is not None
    enrollment.repository.course.assert_awaited_once_with(10, lock=True)


@pytest.mark.parametrize("role,assigned,code", [("student", False, 403), ("teacher", False, 404)])
async def test_unrelated_users_cannot_approve(
    enrollment: EnrollmentService, student: UserDTO, role: str, assigned: bool, code: int
) -> None:
    enrollment.repository.user.return_value = student.model_copy(update={"role": role})
    enrollment.repository.assigned.return_value = assigned
    with pytest.raises(HTTPException) as error:
        await enrollment.decide(student, 10, 20, DecisionDTO(decision="approve"))
    assert error.value.status_code == code
    enrollment.repository.create_grant.assert_not_awaited()


async def test_approval_creates_expiring_grant_and_decision_atomically(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    teacher = student.model_copy(update={"id": 2, "role": "teacher"})
    enrollment.repository.user.side_effect = [teacher, student]
    enrollment.repository.assigned.return_value = True
    await enrollment.decide(teacher, 10, 20, DecisionDTO(decision="approve", duration_days=30))
    args = enrollment.repository.create_grant.call_args.args
    assert args[:4] == (10, 1, "teacher_approval", 2)
    assert args[5] - args[4] == timedelta(days=30) and args[6] == 20
    enrollment.repository.decide.assert_awaited_once_with(20, "approved", 2, args[4], "")
    enrollment.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.parametrize("reason", ["disabled", "left", "unpublished", "decided"])
async def test_invalid_approvals_create_no_grant(
    enrollment: EnrollmentService, student: UserDTO, reason: str
) -> None:
    admin = student.model_copy(update={"id": 2, "role": "admin"})
    enrollment.repository.user.side_effect = [
        admin,
        student.model_copy(update={"is_active": reason != "disabled"}),
    ]
    if reason == "left":
        enrollment.repository.enrolled.return_value = False
    elif reason == "unpublished":
        enrollment.repository.course.return_value = CourseState(10, False)
    elif reason == "decided":
        enrollment.repository.request.return_value = (
            enrollment.repository.request.return_value.model_copy(update={"status": "approved"})
        )
    with pytest.raises(HTTPException) as error:
        await enrollment.decide(admin, 10, 20, DecisionDTO(decision="approve"))
    assert error.value.status_code == (422 if reason == "disabled" else 409)
    enrollment.repository.create_grant.assert_not_awaited()


async def test_rejection_never_creates_grant(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    admin = student.model_copy(update={"role": "admin"})
    enrollment.repository.user.return_value = admin
    await enrollment.decide(admin, 10, 20, DecisionDTO(decision="reject", note="Try later"))
    enrollment.repository.create_grant.assert_not_awaited()
    assert enrollment.repository.decide.call_args.args[1] == "rejected"


async def test_teachers_cannot_create_or_revoke_admin_grants(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    teacher = student.model_copy(update={"role": "teacher"})
    enrollment.repository.user.return_value = teacher
    enrollment.repository.assigned.return_value = True
    with pytest.raises(HTTPException) as error:
        await enrollment.grant(teacher, 10, GrantInputDTO(user_id=1))
    assert error.value.status_code == 403
    enrollment.repository.grant.return_value = enrollment.repository.grant.return_value.model_copy(
        update={"source": "admin_grant", "request_id": None}
    )
    with pytest.raises(HTTPException) as error:
        await enrollment.revoke(teacher, 10, 30)
    assert error.value.status_code == 403


async def test_revoke_is_scoped_and_idempotent(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    admin = student.model_copy(update={"role": "admin"})
    enrollment.repository.user.return_value = admin
    await enrollment.revoke(admin, 10, 30)
    enrollment.repository.revoke.assert_awaited_once()
    enrollment.repository.grant.return_value = enrollment.repository.grant.return_value.model_copy(
        update={"revoked_at": datetime.now(UTC)}
    )
    await enrollment.revoke(admin, 10, 30)
    assert enrollment.repository.revoke.await_count == 1
    enrollment.repository.grant.return_value = None
    with pytest.raises(HTTPException) as error:
        await enrollment.revoke(admin, 10, 999)
    assert error.value.status_code == 404


async def test_repository_expiry_filter_is_strict_and_course_user_scoped() -> None:
    session = MagicMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.execute.return_value.all.return_value = []
    now = datetime.now(UTC)
    result = await EnrollmentRepo(session).grant_access(10, 1, now)
    query = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "access_grants.revoked_at IS NULL" in str(query)
    assert "access_grants.expires_at >" in str(query)
    assert query.params["course_id_1"] == 10 and query.params["user_id_1"] == 1
    assert query.params["expires_at_1"] == now and not result.sources


async def test_admin_grant_is_independent_from_a_request(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    admin = student.model_copy(update={"id": 2, "role": "admin"})
    enrollment.repository.user.side_effect = [admin, student]
    await enrollment.grant(admin, 10, GrantInputDTO(user_id=1, duration_days=10))
    args = enrollment.repository.create_grant.call_args.args
    assert args[:4] == (10, 1, "admin_grant", 2)
    assert args[5] - args[4] == timedelta(days=10) and len(args) == 6


async def test_failed_decision_rolls_back_its_grant(
    enrollment: EnrollmentService, student: UserDTO
) -> None:
    admin = student.model_copy(update={"id": 2, "role": "admin"})
    enrollment.repository.user.side_effect = [admin, student]
    enrollment.repository.decide.side_effect = RuntimeError("Write failed")
    with pytest.raises(RuntimeError):
        await enrollment.decide(admin, 10, 20, DecisionDTO(decision="approve"))
    enrollment.repository.create_grant.assert_awaited_once()
    assert enrollment.session.begin.return_value.__aexit__.call_args.args[0] is RuntimeError


@pytest.mark.parametrize("days", [0, -1, 366])
def test_duration_and_escalation_input_validation(days: int) -> None:
    with pytest.raises(ValidationError):
        DecisionDTO(decision="approve", duration_days=days)
    with pytest.raises(ValidationError):
        RequestInputDTO(message="Please", full_access=True)
