import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app import get_app
from src.auth.dependencies.current_user import ICurrentUser
from src.auth.dependencies.token.service import get_token_service
from src.auth.dto import UserDTO
from src.auth.repositories.user import UserRepo
from src.auth.service.token import TokenService
from src.config.jwt import Settings as JwtSettings
from src.config.security import Settings as SecuritySettings
from src.health.service import HealthService


class FakeHealthService:
    def __init__(self, available: bool) -> None:
        self.available = available

    async def is_ready(self) -> bool:
        return self.available


@pytest.mark.parametrize("available,code", [(True, 200), (False, 503)])
def test_readiness_status_and_resource_lifecycle(available: bool, code: int) -> None:
    app = get_app()
    app.dependency_overrides[HealthService] = lambda: FakeHealthService(available)
    with TestClient(app) as client:
        assert app.state.database is not None
        assert app.state.redis is not None
        assert client.get("/health/live").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == code
        assert response.json() == {"status": "ok" if available else "unavailable"}


@pytest.mark.parametrize("active,exists", [(True, True), (False, True), (False, False)])
def test_current_user_dependency(active: bool, exists: bool) -> None:
    app = get_app()
    service = TokenService(
        JwtSettings(_env_file=None),
        SecuritySettings(_env_file=None, SECRET_KEY="test-only-key-" * 4),
    )

    class FakeUserRepo:
        async def get(self, pk: int) -> UserDTO | None:
            if not exists:
                return None
            return UserDTO(id=pk, name="Student", email="student@example.com", is_active=active)

    @app.get("/test/me", response_model=UserDTO)
    async def me(user: ICurrentUser) -> UserDTO:
        return user

    app.dependency_overrides[get_token_service] = lambda: service
    app.dependency_overrides[UserRepo] = FakeUserRepo
    with TestClient(app) as client:
        assert client.get("/test/me").status_code == 401
        token = service.create_access_token(1).access_token
        response = client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == (200 if active and exists else 401)
        if response.status_code == 200:
            assert "password_hash" not in response.json()


def test_exception_contract() -> None:
    from src.auth.exceptions import UserAlreadyExists

    app = get_app()

    @app.get("/test/conflict")
    async def conflict() -> None:
        raise UserAlreadyExists

    @app.get("/test/forbidden")
    async def forbidden() -> None:
        raise HTTPException(status_code=403, detail="Forbidden")

    with TestClient(app) as client:
        response = client.get("/test/conflict")
        assert response.status_code == 409
        assert response.json() == {"detail": "Account exists"}
        assert client.get("/test/forbidden").json() == {"detail": "Forbidden"}
