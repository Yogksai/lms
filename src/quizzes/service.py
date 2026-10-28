from datetime import UTC, datetime, timedelta
from secrets import SystemRandom
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException

from src.auth.dto import UserDTO
from src.config.db.session import ISession
from src.config.learning import get_settings
from src.enrollment.dependencies_service import IEnrollmentService
from src.learning_events.dto import QuizSubmitted
from src.learning_events.repository import LearningEventRepo
from src.quizzes.cache import IQuizCache
from src.quizzes.dependencies import IQuizRepo
from src.quizzes.dto import (
    AttemptDTO,
    AttemptPageDTO,
    AttemptRecord,
    ProgressDTO,
    QuizInfoDTO,
    SubmitDTO,
)
from src.quizzes.grading import daily_window, grade, public_question
from src.quizzes.repository import ModuleScope


class QuizService:
    def __init__(
        self,
        session: ISession,
        repository: IQuizRepo,
        access: IEnrollmentService,
        cache: IQuizCache,
    ) -> None:
        self.session = session
        self.repository = repository
        self.access = access
        self.cache = cache

    async def scope(self, user: UserDTO, course_id: int, module_id: int) -> ModuleScope:
        await self.access.course(course_id, lock=True, published=True)
        actor = await self.access.actor(user)
        scope = await self.repository.scope(course_id, module_id)
        if scope is None:
            raise HTTPException(404, "Module not found")
        await self.require_access(actor, course_id, preview=scope.is_preview)
        return scope

    async def require_access(self, actor: UserDTO, course_id: int, *, preview: bool) -> None:
        if preview or await self.access.staff_reason(actor, course_id):
            return
        if await self.access.repository.enrolled(course_id, actor.id):
            grants = await self.access.repository.grant_access(
                course_id, actor.id, datetime.now(UTC)
            )
            if grants.sources:
                return
        raise HTTPException(403, "Course access required")

    async def expire(self, attempt: AttemptRecord, now: datetime) -> AttemptRecord:
        if attempt.status == "in_progress" and now >= attempt.deadline_at:
            await self.repository.expire(attempt.id)
            return attempt.model_copy(update={"status": "expired"})
        return attempt

    def view(self, attempt: AttemptRecord, scope: ModuleScope | None, now: datetime) -> AttemptDTO:
        result = None
        if attempt.status == "submitted":
            result = grade(
                attempt.snapshot,
                attempt.answers,
                attempt.passing_score,
                {lesson.id for lesson in scope.lessons} if scope else set(),
            )
        return AttemptDTO(
            attempt_id=attempt.attempt_key,
            course_id=attempt.course_id,
            module_id=attempt.module_id,
            module_title=attempt.module_title,
            quiz_revision=attempt.quiz_revision,
            passing_score=attempt.passing_score,
            started_at=attempt.started_at,
            deadline_at=attempt.deadline_at,
            server_time=now,
            status=attempt.status,
            questions=[public_question(question) for question in attempt.snapshot],
            answers=attempt.answers,
            result=result,
        )

    async def info(self, user: UserDTO, course_id: int, module_id: int) -> QuizInfoDTO:
        async with self.session.begin():
            await self.scope(user, course_id, module_id)
            config = await self.repository.config(module_id)
            settings = get_settings()
            now = datetime.now(UTC)
            start, end = daily_window(now, settings.timezone)
            used = await self.repository.count_daily(user.id, module_id, start, end)
            opened = await self.repository.open_attempt(user.id, module_id)
            if opened:
                opened = await self.expire(opened, now)
            return QuizInfoDTO(
                module_id=module_id,
                available=bool(
                    config
                    and config.enabled
                    and await self.repository.active_count(module_id) >= config.question_count
                ),
                question_count=config.question_count if config else 10,
                passing_score=config.passing_score if config else 70,
                time_limit_seconds=config.time_limit_seconds if config else 600,
                remaining_today=max(0, settings.daily_attempts - used),
                daily_limit=settings.daily_attempts,
                reset_at=end,
                timezone=settings.timezone,
                open_attempt=opened.attempt_key
                if opened and opened.status == "in_progress"
                else None,
            )

    async def start(self, user: UserDTO, course_id: int, module_id: int) -> AttemptDTO:
        if not await self.cache.allow_start(user.id):
            raise HTTPException(429, "Too many start requests; retry in a minute")
        async with self.session.begin():
            scope = await self.scope(user, course_id, module_id)
            now = datetime.now(UTC)
            opened = await self.repository.open_attempt(user.id, module_id)
            if opened:
                opened = await self.expire(opened, now)
                if opened.status == "in_progress":
                    return self.view(opened, scope, now)
            config = await self.repository.config(module_id)
            if not config or not config.enabled:
                raise HTTPException(409, "Quiz is not available")
            settings = get_settings()
            start, end = daily_window(now, settings.timezone)
            if (
                await self.repository.count_daily(user.id, module_id, start, end)
                >= settings.daily_attempts
            ):
                raise HTTPException(429, "Daily attempt limit reached")
            key = self.cache.key(config.id, config.revision, scope.course_revision)
            pool = await self.cache.load(key)
            if pool is None:
                pool = await self.repository.pool(module_id)
                await self.cache.save(key, pool)
            if len(pool) < config.question_count:
                raise HTTPException(409, "Not enough active questions")
            selected = SystemRandom().sample(pool, config.question_count)
            attempt = await self.repository.create_attempt(
                user.id,
                course_id,
                scope,
                config,
                selected,
                now,
                now + timedelta(seconds=config.time_limit_seconds),
            )
            return self.view(attempt, scope, now)

    async def owned(
        self, user: UserDTO, course_id: int, key: UUID
    ) -> tuple[AttemptRecord, ModuleScope | None]:
        await self.access.course(course_id, lock=True, published=True)
        actor = await self.access.actor(user)
        attempt = await self.repository.attempt(actor.id, course_id, key)
        if attempt is None:
            raise HTTPException(404, "Attempt not found")
        scope = (
            await self.repository.scope(course_id, attempt.module_id) if attempt.module_id else None
        )
        await self.require_access(actor, course_id, preview=bool(scope and scope.is_preview))
        return attempt, scope

    async def get(self, user: UserDTO, course_id: int, key: UUID) -> AttemptDTO:
        async with self.session.begin():
            attempt, scope = await self.owned(user, course_id, key)
            now = datetime.now(UTC)
            return self.view(await self.expire(attempt, now), scope, now)

    async def submit(self, user: UserDTO, course_id: int, key: UUID, data: SubmitDTO) -> AttemptDTO:
        async with self.session.begin():
            attempt, scope = await self.owned(user, course_id, key)
            now = datetime.now(UTC)
            attempt = await self.expire(attempt, now)
            if attempt.status == "submitted":
                if attempt.answers != data.answers:
                    raise HTTPException(409, "Attempt already submitted with different answers")
                return self.view(attempt, scope, now)
            if attempt.status == "expired":
                return self.view(attempt, scope, now)
            if scope is None:
                raise HTTPException(409, "Module no longer exists")
            try:
                result = grade(
                    attempt.snapshot,
                    data.answers,
                    attempt.passing_score,
                    {lesson.id for lesson in scope.lessons},
                )
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            await self.repository.submit(
                attempt.id,
                data.answers,
                result.correct_count,
                result.score_percent,
                result.passed,
                now,
            )
            await LearningEventRepo(self.session).enqueue(
                QuizSubmitted(
                    user_id=user.id,
                    course_id=course_id,
                    attempt_id=attempt.attempt_key,
                    module_title=attempt.module_title,
                    score_percent=result.score_percent,
                    passed=result.passed,
                )
            )
            updated = attempt.model_copy(
                update={
                    "status": "submitted",
                    "answers": data.answers,
                    "submitted_at": now,
                    "correct_count": result.correct_count,
                    "score_percent": result.score_percent,
                    "passed": result.passed,
                }
            )
            return self.view(updated, scope, now)

    async def history(
        self, user: UserDTO, course_id: int, module_id: int, limit: int, offset: int
    ) -> AttemptPageDTO:
        async with self.session.begin():
            await self.scope(user, course_id, module_id)
            return await self.repository.history(user.id, module_id, limit, offset)

    async def progress(self, user: UserDTO, course_id: int) -> ProgressDTO:
        async with self.session.begin():
            await self.access.course(course_id, published=True)
            await self.access.actor(user)
            return await self.repository.progress(user.id, course_id)

    async def lesson(
        self, user: UserDTO, course_id: int, module_id: int, lesson_id: int, completed: bool
    ) -> ProgressDTO:
        async with self.session.begin():
            scope = await self.scope(user, course_id, module_id)
            if lesson_id not in {lesson.id for lesson in scope.lessons}:
                raise HTTPException(404, "Lesson not found")
            await self.repository.mark_lesson(user.id, course_id, lesson_id, completed)
            return await self.repository.progress(user.id, course_id)


IQuizService = Annotated[QuizService, Depends()]
