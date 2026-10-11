from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from src.auth.models.refresh import RefreshTokenModel
from src.auth.models.session import AuthSessionModel
from src.config.db.session import ISession


@dataclass(frozen=True)
class SessionRecord:
    id: int
    user_id: int
    session_key: UUID
    expires_at: datetime
    revoked_at: datetime | None
    consumed_at: datetime | None


class SessionRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def create(
        self, user_id: int, session_key: UUID, expires_at: datetime, token_hash: str
    ) -> None:
        instance = AuthSessionModel(user_id=user_id, session_key=session_key, expires_at=expires_at)
        self.session.add(instance)
        await self.session.flush()
        await self.add_refresh(instance.id, token_hash)

    async def add_refresh(self, session_id: int, token_hash: str) -> None:
        self.session.add(RefreshTokenModel(session_id=session_id, token_hash=token_hash))
        await self.session.flush()

    async def find_refresh(self, token_hash: str) -> SessionRecord | None:
        result = await self.session.execute(
            select(AuthSessionModel)
            .join(RefreshTokenModel, RefreshTokenModel.session_id == AuthSessionModel.id)
            .where(RefreshTokenModel.token_hash == token_hash)
            .with_for_update(of=AuthSessionModel)
            .execution_options(populate_existing=True)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return None
        # Read consumption after acquiring the parent lock to see completed rotations.
        consumed_at = await self.session.scalar(
            select(RefreshTokenModel.consumed_at).where(RefreshTokenModel.token_hash == token_hash)
        )
        return SessionRecord(
            id=session.id,
            user_id=session.user_id,
            session_key=session.session_key,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            consumed_at=consumed_at,
        )

    async def consume(self, token_hash: str, now: datetime) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(consumed_at=now)
        )

    async def revoke(self, session_id: int, now: datetime) -> None:
        await self.session.execute(
            update(AuthSessionModel)
            .where(AuthSessionModel.id == session_id, AuthSessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def is_active(self, session_key: UUID, user_id: int, now: datetime) -> bool:
        return (
            await self.session.scalar(
                select(AuthSessionModel.id).where(
                    AuthSessionModel.session_key == session_key,
                    AuthSessionModel.user_id == user_id,
                    AuthSessionModel.revoked_at.is_(None),
                    AuthSessionModel.expires_at > now,
                )
            )
            is not None
        )
