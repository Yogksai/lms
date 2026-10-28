from typing import Annotated

from fastapi import Depends, HTTPException

from src.auth.dto import UserDTO
from src.config.db.session import ISession
from src.enrollment.dependencies_service import IEnrollmentService
from src.quizzes.dependencies import IQuizRepo
from src.quizzes.dto import BankDTO, QuestionDTO, QuestionWriteDTO, QuizDTO, QuizWriteDTO
from src.quizzes.repository import ModuleScope


class QuizAuthoringService:
    def __init__(
        self, session: ISession, repository: IQuizRepo, access: IEnrollmentService
    ) -> None:
        self.session = session
        self.repository = repository
        self.access = access

    async def scope(
        self, user: UserDTO, course_id: int, module_id: int, *, write: bool = False
    ) -> ModuleScope:
        await self.access.manage(user, course_id, lock=write)
        scope = await self.repository.scope(course_id, module_id)
        if scope is None:
            raise HTTPException(404, "Module not found in this course")
        if write and scope.status != "draft":
            raise HTTPException(409, "Return the course to draft before editing quizzes")
        return scope

    async def revision(self, module_id: int, expected: int) -> QuizDTO | None:
        quiz = await self.repository.config(module_id)
        if (quiz.revision if quiz else 0) != expected:
            raise HTTPException(409, "Quiz bank changed; reload before saving")
        return quiz

    async def bank(
        self, user: UserDTO, course_id: int, module_id: int, limit: int, offset: int
    ) -> BankDTO:
        async with self.session.begin():
            return await self.repository.bank(
                await self.scope(user, course_id, module_id), limit, offset
            )

    async def configure(
        self, user: UserDTO, course_id: int, module_id: int, expected: int, data: QuizWriteDTO
    ) -> QuizDTO:
        async with self.session.begin():
            await self.scope(user, course_id, module_id, write=True)
            await self.revision(module_id, expected)
            if data.enabled and await self.repository.active_count(module_id) < data.question_count:
                raise HTTPException(422, "Not enough active questions to enable the quiz")
            return await self.repository.save_config(module_id, data)

    async def question(
        self,
        user: UserDTO,
        course_id: int,
        module_id: int,
        expected: int,
        data: QuestionWriteDTO,
        question_id: int | None = None,
    ) -> QuestionDTO:
        async with self.session.begin():
            scope = await self.scope(user, course_id, module_id, write=True)
            quiz = await self.revision(module_id, expected)
            if quiz is None:
                raise HTTPException(409, "Configure the quiz before adding questions")
            if data.lesson_id not in {lesson.id for lesson in scope.lessons}:
                raise HTTPException(422, "Question lesson must belong to this module")
            if (
                question_id is not None
                and await self.repository.question(module_id, question_id) is None
            ):
                raise HTTPException(404, "Question not found in this module")
            if question_id is None and (await self.repository.bank(scope, 1, 0)).total >= 1000:
                raise HTTPException(409, "Question bank limit reached")
            saved_id = await self.repository.save_question(module_id, data, question_id)
            await self.repository.bump(quiz.id)
            saved = await self.repository.question(module_id, saved_id)
            assert saved is not None
            return saved

    async def archive(
        self, user: UserDTO, course_id: int, module_id: int, question_id: int, expected: int
    ) -> None:
        async with self.session.begin():
            await self.scope(user, course_id, module_id, write=True)
            quiz = await self.revision(module_id, expected)
            if quiz is None or await self.repository.question(module_id, question_id) is None:
                raise HTTPException(404, "Question not found")
            await self.repository.archive_question(module_id, question_id)
            await self.repository.bump(quiz.id)


IQuizAuthoring = Annotated[QuizAuthoringService, Depends()]
