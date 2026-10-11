from typing import Annotated

from fastapi import Depends
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
