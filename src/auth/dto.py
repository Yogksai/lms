from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
)

UserName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: UserName
    email: EmailStr
    is_active: bool


class UserCredentialsDTO(UserDTO):
    password_hash: str | None


class AccessTokenDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayloadDTO(BaseModel):
    user_id: int
    session_id: UUID


class RegisterDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: UserName
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class RefreshDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: SecretStr = Field(min_length=43, max_length=43)


class ProfileUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: UserName


class TokenPairDTO(AccessTokenDTO):
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
