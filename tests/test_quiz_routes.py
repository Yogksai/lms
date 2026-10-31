from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.app import get_app
from src.auth.dto import UserDTO
from src.auth.service.account import AccountService
from src.quizzes.dto import QuizInfoDTO
from src.quizzes.service import QuizService


@pytest.fixture
def quiz_api() -> tuple[TestClient, AsyncMock]:
    app = get_app()
    accounts = AsyncMock(spec=AccountService)
    accounts.current_user.return_value = UserDTO(
        id=1, name="Student", email="student@example.com", is_active=True
    )
    service = AsyncMock(spec=QuizService)
    app.dependency_overrides[AccountService] = lambda: accounts
    app.dependency_overrides[QuizService] = lambda: service
    return TestClient(app), service


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/v1/courses/10/modules/20/quiz"),
        ("post", "/v1/courses/10/modules/20/attempts"),
        ("get", "/v1/courses/10/progress"),
    ],
)
def test_learning_requires_identity(quiz_api: tuple, method: str, path: str) -> None:
    client, _ = quiz_api
    assert client.request(method, path).status_code == 401


def test_quiz_metadata_is_private(quiz_api: tuple) -> None:
    client, service = quiz_api
    service.info.return_value = QuizInfoDTO(
        module_id=20,
        available=True,
        question_count=10,
        passing_score=70,
        time_limit_seconds=600,
        remaining_today=5,
        daily_limit=5,
        reset_at="2026-10-22T19:00:00Z",
        timezone="Asia/Almaty",
        open_attempt=None,
    )
    response = client.get(
        "/v1/courses/10/modules/20/quiz", headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["vary"] == "Authorization"


@pytest.mark.parametrize(
    "body",
    [{"answers": {}, "score_percent": 100}, {"answers": {"1": "E"}}, {"answers": {}, "user_id": 2}],
)
def test_submission_cannot_choose_score_or_identity(quiz_api: tuple, body: dict) -> None:
    client, service = quiz_api
    response = client.post(
        "/v1/courses/10/attempts/00000000-0000-4000-8000-000000000001/submit",
        json=body,
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 422
    service.submit.assert_not_awaited()
