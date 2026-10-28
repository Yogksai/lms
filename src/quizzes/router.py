from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict

from src.auth.dependencies.current_user import ICurrentUser
from src.quizzes.authoring_router import no_store
from src.quizzes.dto import AttemptDTO, AttemptPageDTO, ProgressDTO, QuizInfoDTO, SubmitDTO
from src.quizzes.service import IQuizService

router = APIRouter(
    prefix="/courses/{course_id}", tags=["Learning"], dependencies=[Depends(no_store)]
)
Id = Annotated[int, Path(gt=0)]


class LessonCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool


@router.get("/modules/{module_id}/quiz", response_model=QuizInfoDTO)
async def info(
    course_id: Id, module_id: Id, user: ICurrentUser, service: IQuizService
) -> QuizInfoDTO:
    return await service.info(user, course_id, module_id)


@router.post("/modules/{module_id}/attempts", response_model=AttemptDTO)
async def start(
    course_id: Id, module_id: Id, user: ICurrentUser, service: IQuizService
) -> AttemptDTO:
    return await service.start(user, course_id, module_id)


@router.get("/modules/{module_id}/attempts", response_model=AttemptPageDTO)
async def history(
    course_id: Id,
    module_id: Id,
    user: ICurrentUser,
    service: IQuizService,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AttemptPageDTO:
    return await service.history(user, course_id, module_id, limit, offset)


@router.get("/attempts/{attempt_id}", response_model=AttemptDTO)
async def attempt(
    course_id: Id, attempt_id: UUID, user: ICurrentUser, service: IQuizService
) -> AttemptDTO:
    return await service.get(user, course_id, attempt_id)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptDTO)
async def submit(
    course_id: Id, attempt_id: UUID, data: SubmitDTO, user: ICurrentUser, service: IQuizService
) -> AttemptDTO:
    return await service.submit(user, course_id, attempt_id, data)


@router.get("/progress", response_model=ProgressDTO)
async def progress(course_id: Id, user: ICurrentUser, service: IQuizService) -> ProgressDTO:
    return await service.progress(user, course_id)


@router.put("/modules/{module_id}/lessons/{lesson_id}/completion", response_model=ProgressDTO)
async def lesson(
    course_id: Id,
    module_id: Id,
    lesson_id: Id,
    data: LessonCompletion,
    user: ICurrentUser,
    service: IQuizService,
) -> ProgressDTO:
    return await service.lesson(user, course_id, module_id, lesson_id, data.completed)
