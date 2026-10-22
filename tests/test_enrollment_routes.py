from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.app import get_app
from src.auth.dto import UserDTO
from src.auth.exceptions import CredentialsException
from src.auth.service.account import AccountService
from src.courses.dto import LessonDTO
from src.courses.service.course import CourseService
from src.enrollment.dto import AccessDTO
from src.enrollment.service import EnrollmentService


@pytest.fixture
def services() -> tuple[TestClient, AsyncMock, AsyncMock, AsyncMock]:
    app = get_app()
    student = UserDTO(id=1, name="Student", email="student@example.com", is_active=True)
    accounts = AsyncMock(spec=AccountService)
    accounts.current_user.return_value = student
    enrollment = AsyncMock(spec=EnrollmentService)
    enrollment.can_read.return_value = True
    enrollment.enroll.return_value = AccessDTO(
        course_id=10,
        available=True,
        enrolled=True,
        full_access=False,
        reasons=[],
        expires_at=None,
        request=None,
        grants=[],
    )
    courses = AsyncMock(spec=CourseService)
    courses.get_lesson.return_value = LessonDTO(
        id=30,
        module_id=20,
        title="Lesson",
        position=1,
        summary="Text",
        video_url="https://youtu.be/dQw4w9WgXcQ",
    )
    app.dependency_overrides[AccountService] = lambda: accounts
    app.dependency_overrides[EnrollmentService] = lambda: enrollment
    app.dependency_overrides[CourseService] = lambda: courses
    return TestClient(app), accounts, enrollment, courses


def test_guest_cannot_supply_full_access_flag(services: tuple) -> None:
    client, accounts, enrollment, courses = services
    response = client.get("/v1/courses/10/modules/20/lessons/30?full_access=true")
    assert response.status_code == 200
    courses.get_lesson.assert_awaited_once_with(10, 20, 30, full_access=False)
    accounts.current_user.assert_not_awaited()
    enrollment.can_read.assert_not_awaited()
    assert response.headers["cache-control"] == "no-store"


def test_bearer_lesson_uses_server_access_decision(services: tuple) -> None:
    client, accounts, enrollment, courses = services
    response = client.get(
        "/v1/courses/10/modules/20/lessons/30", headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 200
    accounts.current_user.assert_awaited_once_with("token")
    enrollment.can_read.assert_awaited_once_with(accounts.current_user.return_value, 10)
    courses.get_lesson.assert_awaited_once_with(10, 20, 30, full_access=True)
    assert response.headers["vary"] == "Authorization"


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer bad"])
def test_invalid_optional_credentials_never_degrade_to_guest(services: tuple, header: str) -> None:
    client, accounts, enrollment, courses = services
    accounts.current_user.side_effect = CredentialsException
    assert (
        client.get(
            "/v1/courses/10/modules/20/lessons/30", headers={"Authorization": header}
        ).status_code
        == 401
    )
    enrollment.can_read.assert_not_awaited()
    courses.get_lesson.assert_not_awaited()


def test_enrollment_uses_authenticated_identity_not_input(services: tuple) -> None:
    client, accounts, enrollment, _ = services
    response = client.post("/v1/courses/10/enrollment", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200 and not response.json()["full_access"]
    enrollment.enroll.assert_awaited_once_with(accounts.current_user.return_value, 10)


def test_access_requires_authentication(services: tuple) -> None:
    client, _, enrollment, _ = services
    assert client.get("/v1/courses/10/access").status_code == 401
    enrollment.status.assert_not_awaited()


def test_request_cannot_choose_grant_fields(services: tuple) -> None:
    client, _, enrollment, _ = services
    response = client.post(
        "/v1/courses/10/access-requests",
        headers={"Authorization": "Bearer token"},
        json={"message": "Please", "source": "admin_grant", "duration_days": 365},
    )
    assert response.status_code == 422
    enrollment.request_access.assert_not_awaited()
