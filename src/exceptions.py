from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.auth.exceptions import CredentialsException, UserAlreadyExists, UserNotFound
from src.courses.exceptions import ContentNotFound, LessonAccessDenied


async def validation_handler(request: Request, exception: Exception) -> JSONResponse:
    assert isinstance(exception, RequestValidationError)
    # Request inputs can contain passwords or tokens; never echo them in validation errors.
    errors = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        for error in exception.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


async def content_not_found_handler(request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Content not found"}
    )


async def lesson_access_handler(request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Course access required"}
    )


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
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(ContentNotFound, content_not_found_handler)
    app.add_exception_handler(LessonAccessDenied, lesson_access_handler)
    app.add_exception_handler(UserAlreadyExists, already_exists_handler)
    app.add_exception_handler(UserNotFound, not_found_handler)
    app.add_exception_handler(CredentialsException, credentials_handler)
