from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.dependencies.account import IAccountService
from src.auth.dto import UserDTO
from src.auth.exceptions import CredentialsException

bearer = HTTPBearer(auto_error=False)
IBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


async def get_current_user(credentials: IBearer, service: IAccountService) -> UserDTO:
    if credentials is None:
        raise CredentialsException
    return await service.current_user(credentials.credentials)


ICurrentUser = Annotated[UserDTO, Depends(get_current_user)]


async def get_optional_user(
    request: Request, credentials: IBearer, service: IAccountService
) -> UserDTO | None:
    if credentials is None:
        if request.headers.get("Authorization") is not None:
            raise CredentialsException
        return None
    return await service.current_user(credentials.credentials)


IOptionalUser = Annotated[UserDTO | None, Depends(get_optional_user)]
