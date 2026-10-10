from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.auth.exceptions import CredentialsException, UserAlreadyExists, UserNotFound


async def already_exists_handler(request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "Account exists"})


async def not_found_handler(request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Account not found"}
    )


async def credentials_handler(request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def init_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(UserAlreadyExists, already_exists_handler)
    app.add_exception_handler(UserNotFound, not_found_handler)
    app.add_exception_handler(CredentialsException, credentials_handler)
