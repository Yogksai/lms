from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

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
