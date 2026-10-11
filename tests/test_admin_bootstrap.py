from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bin.bootstrap_admin import bootstrap
from src.auth.dto import UserDTO
from src.authoring.repository import AuthoringRepo


@pytest.mark.parametrize("reason", ["valid", "existing-admin", "missing-user", "inactive"])
async def test_admin_bootstrap_is_explicit_and_first_admin_only(reason: str) -> None:
    session = MagicMock(spec=AsyncSession)
    database = MagicMock()
    database.dispose = AsyncMock()
    database.get_db_session.return_value.__aenter__.return_value = session
    repository = AsyncMock(spec=AuthoringRepo)
    repository.has_admin.return_value = reason == "existing-admin"
    repository.user_by_email.return_value = (
        None
        if reason == "missing-user"
        else UserDTO(id=1, name="Admin", email="admin@example.com", is_active=reason != "inactive")
    )
    with (
        patch("bin.bootstrap_admin.DatabaseHelper", return_value=database),
        patch("bin.bootstrap_admin.AuthoringRepo", return_value=repository),
    ):
        if reason == "valid":
            await bootstrap(" admin@example.com ")
            repository.set_role.assert_awaited_once_with(1, "admin")
            repository.user_by_email.assert_awaited_once_with("admin@example.com")
        else:
            with pytest.raises(ValueError):
                await bootstrap("admin@example.com")
            repository.set_role.assert_not_awaited()
    repository.role_lock.assert_awaited_once()
    database.dispose.assert_awaited_once()
