from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.auth.dependencies.password import IPasswordService
from src.auth.dependencies.session import ISessionRepository
from src.auth.dependencies.token.service import ITokenService
from src.auth.dependencies.user.repository import IUserRepository
from src.auth.dto import LoginDTO, ProfileUpdateDTO, RegisterDTO, TokenPairDTO, UserDTO
from src.auth.entities import UserEntity
from src.auth.exceptions import CredentialsException
from src.config.db.session import ISession

# Fixed bcrypt work factor for unknown/passwordless accounts, without plaintext credentials.
DUMMY_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxxThgMHLuFQqKCwvCRVcyw1nO2"


class AccountService:
    def __init__(
        self,
        session: ISession,
        users: IUserRepository,
        sessions: ISessionRepository,
        tokens: ITokenService,
        passwords: IPasswordService,
    ) -> None:
        self.session = session
        self.users = users
        self.sessions = sessions
        self.tokens = tokens
        self.passwords = passwords

    async def register(self, data: RegisterDTO) -> UserDTO:
        password_hash = await self.passwords.get_password_hash(data.password.get_secret_value())
        async with self.session.begin():
            return await self.users.create(
                UserEntity(
                    name=data.name,
                    email=str(data.email),
                    password_hash=password_hash,
                    is_active=True,
                )
            )

    async def login(self, data: LoginDTO) -> TokenPairDTO:
        async with self.session.begin():
            user = await self.users.find_credentials(str(data.email))
            password_hash = (
                user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
            )
            valid = await self.passwords.verify_password(
                data.password.get_secret_value(), password_hash
            )
            if user is None or not user.password_hash or not valid or not user.is_active:
                raise CredentialsException
            session_key = uuid4()
            expires_at = datetime.now(UTC) + timedelta(
                seconds=self.tokens.settings.refresh_token_expire_seconds
            )
            refresh = self.tokens.create_refresh_token()
            await self.sessions.create(
                user.id, session_key, expires_at, self.tokens.hash_refresh_token(refresh)
            )
            return TokenPairDTO(
                access_token=self.tokens.create_access_token(user.id, session_key).access_token,
                refresh_token=refresh,
                expires_in=self.tokens.settings.access_token_expire_seconds,
                refresh_expires_in=self.tokens.settings.refresh_token_expire_seconds,
            )

    async def refresh(self, refresh_token: str) -> TokenPairDTO:
        token_hash = self.tokens.hash_refresh_token(refresh_token)
        pair: TokenPairDTO | None = None
        async with self.session.begin():
            record = await self.sessions.find_refresh(token_hash)
            if record is not None:
                # Measure expiration after the lock is acquired, including time spent waiting.
                now = datetime.now(UTC)
                user = await self.users.get(record.user_id)
                if (
                    record.consumed_at is not None
                    or record.revoked_at is not None
                    or record.expires_at <= now
                    or user is None
                    or not user.is_active
                ):
                    await self.sessions.revoke(record.id, now)
                else:
                    replacement = self.tokens.create_refresh_token()
                    await self.sessions.consume(token_hash, now)
                    await self.sessions.add_refresh(
                        record.id, self.tokens.hash_refresh_token(replacement)
                    )
                    pair = TokenPairDTO(
                        access_token=self.tokens.create_access_token(
                            user.id, record.session_key
                        ).access_token,
                        refresh_token=replacement,
                        expires_in=self.tokens.settings.access_token_expire_seconds,
                        refresh_expires_in=max(0, int((record.expires_at - now).total_seconds())),
                    )
        # Reuse revocation must commit before returning the authentication failure.
        if pair is None:
            raise CredentialsException
        return pair

    async def logout(self, refresh_token: str) -> None:
        async with self.session.begin():
            record = await self.sessions.find_refresh(self.tokens.hash_refresh_token(refresh_token))
            if record is not None:
                await self.sessions.revoke(record.id, datetime.now(UTC))

    async def current_user(self, access_token: str) -> UserDTO:
        payload = self.tokens.verify_access_token(access_token)
        async with self.session.begin():
            if not await self.sessions.is_active(
                payload.session_id, payload.user_id, datetime.now(UTC)
            ):
                raise CredentialsException
            user = await self.users.get(payload.user_id)
            if user is None or not user.is_active:
                raise CredentialsException
            return user

    async def update_profile(self, user_id: int, data: ProfileUpdateDTO) -> UserDTO:
        async with self.session.begin():
            user = await self.users.update_name(user_id, data.name)
            if user is None:
                raise CredentialsException
            return user
