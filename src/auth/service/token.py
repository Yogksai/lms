import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from src.auth.dto import AccessTokenDTO, TokenPayloadDTO
from src.auth.exceptions import CredentialsException
from src.config.jwt import Settings as JwtSettings
from src.config.security import Settings as SecuritySettings


class TokenService:
    """Issue and verify application access tokens with one payload contract."""

    def __init__(self, jwt_settings: JwtSettings, security_settings: SecuritySettings) -> None:
        self.settings = jwt_settings
        self.secret_key = security_settings.secret_key.get_secret_value()

    def create_access_token(self, user_id: int, session_id: UUID) -> AccessTokenDTO:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "token_type": "access",
                "iat": now,
                "exp": now + timedelta(seconds=self.settings.access_token_expire_seconds),
                "iss": self.settings.issuer,
                "aud": self.settings.audience,
            },
            self.secret_key,
            algorithm=self.settings.algorithm,
        )
        return AccessTokenDTO(access_token=token)

    def verify_access_token(self, token: str) -> TokenPayloadDTO:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.settings.algorithm],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                options={"require": ["sub", "sid", "iat", "exp", "iss", "aud", "token_type"]},
            )
            if payload["token_type"] != "access":
                raise CredentialsException
            if not isinstance(payload["sid"], str):
                raise CredentialsException
            user_id = int(payload["sub"])
            if user_id <= 0:
                raise CredentialsException
            return TokenPayloadDTO(user_id=user_id, session_id=UUID(payload["sid"]))
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise CredentialsException from error

    @staticmethod
    def create_refresh_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
