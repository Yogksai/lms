from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from src.config.db.session import ISession
from src.courses.dto import LessonOutlineDTO
from src.courses.models import CourseModel, LessonModel, ModuleModel
from src.quizzes.dto import (
    AttemptPageDTO,
    AttemptRecord,
    AttemptSummaryDTO,
    BankDTO,
    Choice,
    ModuleProgressDTO,
    ProgressDTO,
    QuestionDTO,
    QuestionWriteDTO,
    QuizDTO,
    QuizWriteDTO,
    SnapshotQuestion,
)
from src.quizzes.models import AttemptModel, LessonProgressModel, QuestionModel, QuizModel


@dataclass(frozen=True)
class ModuleScope:
    id: int
    title: str
    is_preview: bool
    course_revision: int
    lessons: list[LessonOutlineDTO]
    status: Literal["draft", "published", "archived"] = "draft"


class QuizRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def scope(self, course_id: int, module_id: int) -> ModuleScope | None:
        module = await self.session.scalar(
            select(ModuleModel)
            .where(ModuleModel.course_id == course_id, ModuleModel.id == module_id)
            .options(
                selectinload(ModuleModel.lessons).load_only(
                    LessonModel.id,
                    LessonModel.module_id,
                    LessonModel.title,
                    LessonModel.position,
                    raiseload=True,
                )
            )
        )
        if module is None:
            return None
        first = await self.session.scalar(
            select(func.min(ModuleModel.position)).where(ModuleModel.course_id == course_id)
        )
        course = (
            await self.session.execute(
                select(
                    CourseModel.revision, CourseModel.is_published, CourseModel.is_archived
                ).where(CourseModel.id == course_id)
            )
        ).one()
        return ModuleScope(
            module.id,
            module.title,
            module.position == first,
            course[0],
            [LessonOutlineDTO.model_validate(lesson) for lesson in module.lessons],
            "archived" if course[2] else "published" if course[1] else "draft",
        )

    async def config(self, module_id: int) -> QuizDTO | None:
        quiz = await self.session.scalar(
            select(QuizModel)
            .where(QuizModel.module_id == module_id)
            .execution_options(populate_existing=True)
        )
        return QuizDTO.model_validate(quiz) if quiz else None

    async def save_config(self, module_id: int, data: QuizWriteDTO) -> QuizDTO:
        quiz = await self.session.scalar(select(QuizModel).where(QuizModel.module_id == module_id))
        if quiz is None:
            quiz = QuizModel(module_id=module_id, **data.model_dump(), revision=1)
            self.session.add(quiz)
        else:
            quiz.question_count, quiz.passing_score = data.question_count, data.passing_score
            quiz.time_limit_seconds, quiz.enabled = data.time_limit_seconds, data.enabled
            quiz.revision += 1
        await self.session.flush()
        return QuizDTO.model_validate(quiz)

    async def bump(self, quiz_id: int) -> None:
        await self.session.execute(
            update(QuizModel).where(QuizModel.id == quiz_id).values(revision=QuizModel.revision + 1)
        )

    async def active_count(self, module_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(QuestionModel)
                .join(LessonModel, LessonModel.id == QuestionModel.lesson_id)
                .where(
                    QuestionModel.module_id == module_id,
                    LessonModel.module_id == module_id,
                    QuestionModel.is_active.is_(True),
                )
            )
            or 0
        )

    @staticmethod
    def question_dto(question: QuestionModel, lesson_title: str) -> QuestionDTO:
        return QuestionDTO(
            id=question.id,
            module_id=question.module_id,
            lesson_title=lesson_title,
            **QuestionWriteDTO.model_validate(question, from_attributes=True).model_dump(),
        )

    async def question(self, module_id: int, question_id: int) -> QuestionDTO | None:
        row = (
            await self.session.execute(
                select(QuestionModel, LessonModel.title)
                .join(LessonModel, LessonModel.id == QuestionModel.lesson_id)
                .where(QuestionModel.id == question_id, QuestionModel.module_id == module_id)
            )
        ).first()
        return self.question_dto(row[0], row[1]) if row else None

    async def save_question(
        self, module_id: int, data: QuestionWriteDTO, question_id: int | None = None
    ) -> int:
        if question_id is None:
            question = QuestionModel(module_id=module_id, **data.model_dump())
            self.session.add(question)
            await self.session.flush()
            return question.id
        await self.session.execute(
            update(QuestionModel)
            .where(QuestionModel.id == question_id, QuestionModel.module_id == module_id)
            .values(**data.model_dump())
        )
        return question_id

    async def archive_question(self, module_id: int, question_id: int) -> None:
        await self.session.execute(
            update(QuestionModel)
            .where(QuestionModel.module_id == module_id, QuestionModel.id == question_id)
            .values(is_active=False)
        )

    async def bank(self, scope: ModuleScope, limit: int, offset: int) -> BankDTO:
        total = await self.session.scalar(
            select(func.count())
            .select_from(QuestionModel)
            .where(QuestionModel.module_id == scope.id)
        )
        rows = await self.session.execute(
            select(QuestionModel, LessonModel.title)
            .join(LessonModel, LessonModel.id == QuestionModel.lesson_id)
            .where(QuestionModel.module_id == scope.id)
            .order_by(QuestionModel.id)
            .limit(limit)
            .offset(offset)
        )
        return BankDTO(
            module_id=scope.id,
            title=scope.title,
            course_status=scope.status,
            lessons=scope.lessons,
            config=await self.config(scope.id),
            active_questions=await self.active_count(scope.id),
            items=[self.question_dto(question, title) for question, title in rows],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def pool(self, module_id: int) -> list[SnapshotQuestion]:
        rows = await self.session.execute(
            select(QuestionModel, LessonModel.title)
            .join(LessonModel, LessonModel.id == QuestionModel.lesson_id)
            .where(
                QuestionModel.module_id == module_id,
                LessonModel.module_id == module_id,
                QuestionModel.is_active.is_(True),
            )
            .order_by(QuestionModel.id)
        )
        return [
            SnapshotQuestion(
                question_id=question.id,
                lesson_id=question.lesson_id,
                lesson_title=title,
                prompt=question.prompt,
                options=question.options,
                correct_option=question.correct_option,
                explanation=question.explanation,
            )
            for question, title in rows
        ]

    async def open_attempt(self, user_id: int, module_id: int) -> AttemptRecord | None:
        attempt = await self.session.scalar(
            select(AttemptModel)
            .where(
                AttemptModel.user_id == user_id,
                AttemptModel.module_id == module_id,
                AttemptModel.status == "in_progress",
            )
            .with_for_update()
        )
        return AttemptRecord.model_validate(attempt) if attempt else None

    async def attempt(self, user_id: int, course_id: int, key: UUID) -> AttemptRecord | None:
        attempt = await self.session.scalar(
            select(AttemptModel)
            .where(
                AttemptModel.user_id == user_id,
                AttemptModel.course_id == course_id,
                AttemptModel.attempt_key == key,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return AttemptRecord.model_validate(attempt) if attempt else None

    async def count_daily(
        self, user_id: int, module_id: int, start: datetime, end: datetime
    ) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(AttemptModel)
                .where(
                    AttemptModel.user_id == user_id,
                    AttemptModel.original_module_id == module_id,
                    AttemptModel.started_at >= start,
                    AttemptModel.started_at < end,
                )
            )
            or 0
        )

    async def create_attempt(
        self,
        user_id: int,
        course_id: int,
        scope: ModuleScope,
        quiz: QuizDTO,
        questions: list[SnapshotQuestion],
        now: datetime,
        deadline: datetime,
    ) -> AttemptRecord:
        instance = AttemptModel(
            user_id=user_id,
            course_id=course_id,
            module_id=scope.id,
            original_module_id=scope.id,
            module_title=scope.title,
            quiz_id=quiz.id,
            quiz_revision=quiz.revision,
            passing_score=quiz.passing_score,
            started_at=now,
            deadline_at=deadline,
            status="in_progress",
            snapshot=[question.model_dump(mode="json") for question in questions],
            answers={},
        )
        self.session.add(instance)
        await self.session.flush()
        return AttemptRecord.model_validate(instance)

    async def expire(self, attempt_id: int) -> None:
        await self.session.execute(
            update(AttemptModel)
            .where(AttemptModel.id == attempt_id, AttemptModel.status == "in_progress")
            .values(status="expired")
        )

    async def submit(
        self,
        attempt_id: int,
        answers: dict[int, Choice],
        correct_count: int,
        score: int,
        passed: bool,
        now: datetime,
    ) -> None:
        await self.session.execute(
            update(AttemptModel)
            .where(AttemptModel.id == attempt_id, AttemptModel.status == "in_progress")
            .values(
                answers={str(key): value for key, value in answers.items()},
                status="submitted",
                correct_count=correct_count,
                score_percent=score,
                passed=passed,
                submitted_at=now,
            )
        )

    async def history(
        self, user_id: int, module_id: int, limit: int, offset: int
    ) -> AttemptPageDTO:
        filters = [AttemptModel.user_id == user_id, AttemptModel.original_module_id == module_id]
        total = await self.session.scalar(
            select(func.count()).select_from(AttemptModel).where(*filters)
        )
        attempts = await self.session.scalars(
            select(AttemptModel)
            .where(*filters)
            .order_by(AttemptModel.started_at.desc(), AttemptModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return AttemptPageDTO(
            items=[
                AttemptSummaryDTO(
                    attempt_id=attempt.attempt_key,
                    status=attempt.status,
                    started_at=attempt.started_at,
                    score_percent=attempt.score_percent,
                    passed=attempt.passed,
                )
                for attempt in attempts
            ],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def mark_lesson(
        self, user_id: int, course_id: int, lesson_id: int, completed: bool
    ) -> None:
        if completed:
            await self.session.execute(
                insert(LessonProgressModel)
                .values(user_id=user_id, course_id=course_id, lesson_id=lesson_id)
                .on_conflict_do_nothing(
                    index_elements=[LessonProgressModel.user_id, LessonProgressModel.lesson_id]
                )
            )
        else:
            await self.session.execute(
                delete(LessonProgressModel).where(
                    LessonProgressModel.user_id == user_id,
                    LessonProgressModel.lesson_id == lesson_id,
                )
            )

    async def progress(self, user_id: int, course_id: int) -> ProgressDTO:
        modules = list(
            await self.session.scalars(
                select(ModuleModel)
                .where(ModuleModel.course_id == course_id)
                .options(
                    selectinload(ModuleModel.lessons).load_only(
                        LessonModel.id,
                        LessonModel.module_id,
                        LessonModel.title,
                        LessonModel.position,
                        raiseload=True,
                    )
                )
                .order_by(ModuleModel.position)
            )
        )
        done = set(
            await self.session.scalars(
                select(LessonProgressModel.lesson_id).where(
                    LessonProgressModel.user_id == user_id,
                    LessonProgressModel.course_id == course_id,
                )
            )
        )
        enabled = set(
            await self.session.scalars(
                select(QuizModel.module_id)
                .join(ModuleModel, ModuleModel.id == QuizModel.module_id)
                .where(ModuleModel.course_id == course_id, QuizModel.enabled.is_(True))
            )
        )
        scores = await self.session.execute(
            select(
                AttemptModel.module_id,
                func.bool_or(AttemptModel.passed),
                func.max(AttemptModel.score_percent),
            )
            .where(
                AttemptModel.user_id == user_id,
                AttemptModel.course_id == course_id,
                AttemptModel.status == "submitted",
                AttemptModel.module_id.is_not(None),
            )
            .group_by(AttemptModel.module_id)
        )
        results = {module_id: (passed, score) for module_id, passed, score in scores}
        items = []
        for module in modules:
            lesson_ids = [lesson.id for lesson in module.lessons if lesson.id in done]
            passed, score = results.get(module.id, (False, None))
            items.append(
                ModuleProgressDTO(
                    module_id=module.id,
                    title=module.title,
                    lesson_count=len(module.lessons),
                    completed_lessons=len(lesson_ids),
                    completed_lesson_ids=lesson_ids,
                    quiz_enabled=module.id in enabled,
                    quiz_passed=bool(passed),
                    best_score=score,
                )
            )
        lessons = sum(item.lesson_count for item in items)
        completed = sum(item.completed_lessons for item in items)
        passed_count = sum(item.quiz_enabled and item.quiz_passed for item in items)
        return ProgressDTO(
            course_id=course_id,
            modules=items,
            lesson_count=lessons,
            completed_lessons=completed,
            lesson_percent=completed * 100 // lessons if lessons else 0,
            passed_modules=passed_count,
            module_count=len(items),
            quiz_percent=passed_count * 100 // len(items) if items else 0,
            complete=bool(items) and passed_count == len(items),
        )
