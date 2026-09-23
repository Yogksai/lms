from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.dependencies.token.service import ITokenService
from src.auth.dependencies.user.repository import IUserRepository
from src.auth.dto import UserDTO
from src.auth.exceptions import CredentialsException

bearer = HTTPBearer(auto_error=False)
IBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


async def get_current_user(
    credentials: IBearer, token_service: ITokenService, user_repo: IUserRepository
) -> UserDTO:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error
    try:
        payload = token_service.verify_access_token(credentials.credentials)
    except CredentialsException as exception:
        raise error from exception
    user = await user_repo.get(payload.user_id)
    if user is None or not user.is_active:
        raise error
    return user


ICurrentUser = Annotated[UserDTO, Depends(get_current_user)]
