from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from src.auth.dependencies.current_user import ICurrentUser
from src.quizzes.authoring import IQuizAuthoring
from src.quizzes.dto import BankDTO, QuestionDTO, QuestionWriteDTO, QuizDTO, QuizWriteDTO


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Authorization"


router = APIRouter(
    prefix="/authoring/courses/{course_id}/modules/{module_id}/quiz",
    tags=["Quiz authoring"],
    dependencies=[Depends(no_store)],
)
Id = Annotated[int, Path(gt=0)]
Revision = Annotated[int, Query(ge=0)]


@router.get("", response_model=BankDTO)
async def bank(
    course_id: Id,
    module_id: Id,
    user: ICurrentUser,
    service: IQuizAuthoring,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BankDTO:
    return await service.bank(user, course_id, module_id, limit, offset)


@router.put("", response_model=QuizDTO)
async def configure(
    course_id: Id,
    module_id: Id,
    revision: Revision,
    data: QuizWriteDTO,
    user: ICurrentUser,
    service: IQuizAuthoring,
) -> QuizDTO:
    return await service.configure(user, course_id, module_id, revision, data)


@router.post("/questions", response_model=QuestionDTO, status_code=201)
async def create_question(
    course_id: Id,
    module_id: Id,
    revision: Revision,
    data: QuestionWriteDTO,
    user: ICurrentUser,
    service: IQuizAuthoring,
) -> QuestionDTO:
    return await service.question(user, course_id, module_id, revision, data)


@router.put("/questions/{question_id}", response_model=QuestionDTO)
async def update_question(
    course_id: Id,
    module_id: Id,
    question_id: Id,
    revision: Revision,
    data: QuestionWriteDTO,
    user: ICurrentUser,
    service: IQuizAuthoring,
) -> QuestionDTO:
    return await service.question(user, course_id, module_id, revision, data, question_id)


@router.delete("/questions/{question_id}", status_code=204)
async def archive_question(
    course_id: Id,
    module_id: Id,
    question_id: Id,
    revision: Revision,
    user: ICurrentUser,
    service: IQuizAuthoring,
) -> None:
    await service.archive(user, course_id, module_id, question_id, revision)
