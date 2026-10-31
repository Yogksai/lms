from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dto import UserDTO
from src.courses.dto import LessonOutlineDTO
from src.enrollment.repository import GrantAccess
from src.quizzes.authoring import QuizAuthoringService
from src.quizzes.cache import QuizCache
from src.quizzes.dto import (
    AttemptRecord,
    QuestionWriteDTO,
    QuizDTO,
    QuizWriteDTO,
    SnapshotQuestion,
    SubmitDTO,
)
from src.quizzes.grading import daily_window, grade, public_question
from src.quizzes.repository import ModuleScope, QuizRepo
from src.quizzes.service import QuizService


def question(number: int = 1) -> SnapshotQuestion:
    return SnapshotQuestion(
        question_id=number,
        lesson_id=2,
        lesson_title="Fractions",
        prompt="1 + 1?",
        options={"A": "2", "B": "3", "C": "4", "D": "5"},
        correct_option="A",
        explanation="Add one and one.",
    )


def record() -> AttemptRecord:
    now = datetime.now(UTC)
    return AttemptRecord(
        id=1,
        attempt_key=uuid4(),
        user_id=1,
        course_id=10,
        module_id=20,
        quiz_id=30,
        original_module_id=20,
        module_title="Math",
        quiz_revision=1,
        passing_score=70,
        started_at=now,
        deadline_at=now + timedelta(minutes=10),
        status="in_progress",
        snapshot=[question()],
        answers={},
        submitted_at=None,
        correct_count=None,
        score_percent=None,
        passed=None,
    )


@pytest.fixture
def learner() -> UserDTO:
    return UserDTO(id=1, name="Student", email="student@example.com", is_active=True)


@pytest.fixture
def service(learner: UserDTO) -> QuizService:
    session = MagicMock(spec=AsyncSession)
    repo = AsyncMock(spec=QuizRepo)
    repo.scope.return_value = ModuleScope(
        id=20,
        title="Math",
        is_preview=True,
        course_revision=1,
        lessons=[LessonOutlineDTO(id=2, module_id=20, title="Fractions", position=1)],
    )
    repo.config.return_value = QuizDTO(
        id=30, module_id=20, revision=1, question_count=1, enabled=True
    )
    repo.open_attempt.return_value = None
    repo.count_daily.return_value = 0
    repo.pool.return_value = [question()]
    repo.attempt.return_value = record()
    repo.create_attempt.return_value = record()
    access = MagicMock()
    access.course = AsyncMock()
    access.actor = AsyncMock(return_value=learner)
    access.staff_reason = AsyncMock(return_value=None)
    access.repository = AsyncMock()
    access.repository.enrolled.return_value = False
    access.repository.grant_access.return_value = GrantAccess([], None)
    cache = AsyncMock(spec=QuizCache)
    cache.load.return_value = None
    cache.allow_start.return_value = True
    return QuizService(session, repo, access, cache)


@pytest.mark.parametrize(
    "correct,total,threshold,passed",
    [
        (7, 10, 70, True),
        (6, 10, 70, False),
        (2, 3, 67, False),
        (2, 3, 66, True),
        (0, 1, 70, False),
        (1, 1, 100, True),
    ],
)
def test_grading_threshold(correct: int, total: int, threshold: int, passed: bool) -> None:
    result = grade(
        [question(i) for i in range(total)], {i: "A" for i in range(correct)}, threshold, {2}
    )
    assert result.passed is passed
    assert result.correct_count == correct
    assert result.score_percent == correct * 100 // total
    assert len(result.questions) == total


def test_snapshot_answers_are_private_and_result_only_contains_selected_questions() -> None:
    item = question()
    assert "correct_option" not in public_question(item).model_dump()
    assert "explanation" not in public_question(item).model_dump()
    result = grade([item], {}, 70, set())
    assert result.questions[0].selected_option is None
    assert result.questions[0].explanation == item.explanation
    assert result.review_lessons[0].lesson_id is None


def test_foreign_question_is_rejected() -> None:
    with pytest.raises(ValueError):
        grade([question()], {999: "A"}, 70, {2})


@pytest.mark.parametrize(
    "now,day",
    [
        (datetime(2026, 10, 22, 18, 59, tzinfo=UTC), 22),
        (datetime(2026, 10, 22, 19, 0, tzinfo=UTC), 23),
    ],
)
def test_daily_window_uses_almaty_calendar_day(now: datetime, day: int) -> None:
    start, end = daily_window(now, "Asia/Almaty")
    assert start.hour == end.hour == 19
    assert start <= now < end
    assert (start + timedelta(hours=5)).day == day


@pytest.mark.parametrize(
    "data",
    [
        {"options": {"A": "x"}},
        {"correct_option": "E"},
        {"explanation": " "},
        {"lesson_id": 0},
        {"score": 100},
    ],
)
def test_question_validation(data: dict[str, object]) -> None:
    payload = {
        "lesson_id": 2,
        "prompt": "Question",
        "options": question().options,
        "correct_option": "A",
        "explanation": "Reason",
    } | data
    with pytest.raises(ValidationError):
        QuestionWriteDTO.model_validate(payload)


async def test_start_snapshots_random_pool_and_never_exposes_answers(
    service: QuizService, learner: UserDTO
) -> None:
    result = await service.start(learner, 10, 20)
    assert result.result is None
    assert "correct_option" not in result.model_dump_json()
    service.access.course.assert_awaited_once_with(10, lock=True, published=True)
    args = service.repository.create_attempt.await_args.args
    assert args[4] == [question()]
    assert args[6] - args[5] == timedelta(minutes=10)


async def test_resume_does_not_consume_daily_limit(service: QuizService, learner: UserDTO) -> None:
    opened = record()
    service.repository.open_attempt.return_value = opened
    service.repository.count_daily.return_value = 5
    result = await service.start(learner, 10, 20)
    assert result.attempt_id == opened.attempt_key
    service.repository.create_attempt.assert_not_awaited()
    service.repository.count_daily.assert_not_awaited()


@pytest.mark.parametrize(
    "kind,status",
    [
        ("daily", 429),
        ("burst", 429),
        ("disabled", 409),
        ("pool", 409),
        ("locked", 403),
        ("missing", 404),
    ],
)
async def test_start_guards(service: QuizService, learner: UserDTO, kind: str, status: int) -> None:
    if kind == "daily":
        service.repository.count_daily.return_value = 5
    elif kind == "burst":
        service.cache.allow_start.return_value = False
    elif kind == "disabled":
        service.repository.config.return_value = None
    elif kind == "pool":
        service.repository.pool.return_value = []
    elif kind == "locked":
        service.repository.scope.return_value = service.repository.scope.return_value.__class__(
            20, "Math", False, 1, []
        )
    else:
        service.repository.scope.return_value = None
    with pytest.raises(HTTPException) as error:
        await service.start(learner, 10, 20)
    assert error.value.status_code == status
    service.repository.create_attempt.assert_not_awaited()


async def test_submit_is_atomic_and_duplicate_safe(service: QuizService, learner: UserDTO) -> None:
    attempt = service.repository.attempt.return_value
    with patch("src.quizzes.service.LearningEventRepo") as repo:
        repo.return_value.enqueue = AsyncMock()
        result = await service.submit(learner, 10, attempt.attempt_key, SubmitDTO(answers={1: "A"}))
        assert result.result and result.result.passed
        repo.return_value.enqueue.assert_awaited_once()
        service.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)
    service.repository.attempt.return_value = attempt.model_copy(
        update={"status": "submitted", "answers": {1: "A"}}
    )
    service.repository.submit.reset_mock()
    with patch("src.quizzes.service.LearningEventRepo") as repo:
        await service.submit(learner, 10, attempt.attempt_key, SubmitDTO(answers={1: "A"}))
        repo.assert_not_called()
    service.repository.submit.assert_not_awaited()
    with pytest.raises(HTTPException) as error:
        await service.submit(learner, 10, attempt.attempt_key, SubmitDTO(answers={1: "B"}))
    assert error.value.status_code == 409


async def test_expired_attempt_commits_expiry_without_result(
    service: QuizService, learner: UserDTO
) -> None:
    service.repository.attempt.return_value = record().model_copy(
        update={"deadline_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    result = await service.submit(learner, 10, uuid4(), SubmitDTO(answers={1: "A"}))
    assert result.status == "expired" and result.result is None
    service.repository.expire.assert_awaited_once()
    service.repository.submit.assert_not_awaited()


async def test_attempt_is_owner_and_course_scoped(service: QuizService, learner: UserDTO) -> None:
    service.repository.attempt.return_value = None
    key = uuid4()
    with pytest.raises(HTTPException) as error:
        await service.get(learner, 10, key)
    assert error.value.status_code == 404
    service.repository.attempt.assert_awaited_once_with(1, 10, key)


async def test_foreign_answers_do_not_persist(service: QuizService, learner: UserDTO) -> None:
    with pytest.raises(HTTPException) as error:
        await service.submit(learner, 10, uuid4(), SubmitDTO(answers={999: "A"}))
    assert error.value.status_code == 422
    service.repository.submit.assert_not_awaited()


async def test_authoring_revision_and_published_guards(
    service: QuizService, learner: UserDTO
) -> None:
    author = QuizAuthoringService(service.session, service.repository, service.access)
    service.access.manage = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await author.configure(learner, 10, 20, 0, QuizWriteDTO())
    assert error.value.status_code == 409
    service.repository.scope.return_value = ModuleScope(20, "Math", True, 1, [], "published")
    with pytest.raises(HTTPException) as error:
        await author.configure(learner, 10, 20, 1, QuizWriteDTO())
    assert error.value.status_code == 409
    service.repository.save_config.assert_not_awaited()


async def test_redis_failure_is_non_authoritative() -> None:
    redis = AsyncMock()
    redis.eval.side_effect = RedisConnectionError()
    redis.get.side_effect = RedisConnectionError()
    redis.set.side_effect = RedisConnectionError()
    cache = QuizCache(redis)
    assert await cache.allow_start(1)
    assert await cache.load("key") is None
    await cache.save("key", [question()])
    assert cache.key(1, 2, 3) != cache.key(1, 2, 4)
    assert cache.key(1, 2, 3) != cache.key(1, 3, 3)


@pytest.mark.parametrize(
    "enrolled,grants,staff,allowed",
    [
        (False, [], None, False),
        (True, [], None, False),
        (False, ["admin_grant"], None, False),
        (True, ["admin_grant"], None, True),
        (False, [], "assigned_teacher", True),
        (False, [], "admin", True),
    ],
)
async def test_non_preview_quiz_access(
    service: QuizService,
    learner: UserDTO,
    enrolled: bool,
    grants: list,
    staff: str | None,
    allowed: bool,
) -> None:
    service.access.staff_reason.return_value = staff
    service.access.repository.enrolled.return_value = enrolled
    service.access.repository.grant_access.return_value = GrantAccess(grants, None)
    if allowed:
        await service.require_access(learner, 10, preview=False)
    else:
        with pytest.raises(HTTPException) as error:
            await service.require_access(learner, 10, preview=False)
        assert error.value.status_code == 403


async def test_outbox_failure_rolls_back_submission(service: QuizService, learner: UserDTO) -> None:
    with patch("src.quizzes.service.LearningEventRepo") as repo:
        repo.return_value.enqueue = AsyncMock(side_effect=RuntimeError("storage failure"))
        with pytest.raises(RuntimeError):
            await service.submit(learner, 10, uuid4(), SubmitDTO(answers={1: "A"}))
    args = service.session.begin.return_value.__aexit__.await_args.args
    assert args[0] is RuntimeError


@pytest.mark.parametrize(
    "enabled,passed,done,complete",
    [
        (True, True, False, True),
        (True, False, True, False),
        (False, True, True, False),
        (False, False, False, False),
    ],
)
async def test_progress_separates_reading_from_quiz_pass(
    enabled: bool, passed: bool, done: bool, complete: bool
) -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalars.side_effect = [
        [SimpleNamespace(id=20, title="Math", lessons=[SimpleNamespace(id=2)])],
        [2] if done else [],
        [20] if enabled else [],
    ]
    session.execute.return_value = [(20, passed, 100 if passed else 0)]
    progress = await QuizRepo(session).progress(1, 10)
    assert progress.complete is complete
    assert progress.lesson_percent == (100 if done else 0)
    assert progress.passed_modules == int(enabled and passed)


async def test_empty_course_is_not_completed() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalars.side_effect = [[], [], []]
    session.execute.return_value = []
    progress = await QuizRepo(session).progress(1, 10)
    assert not progress.complete and progress.quiz_percent == 0


async def test_lesson_mark_is_idempotent_and_unmark_is_owned() -> None:
    session = MagicMock(spec=AsyncSession)
    repo = QuizRepo(session)
    await repo.mark_lesson(1, 10, 2, True)
    sql = str(session.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (user_id, lesson_id) DO NOTHING" in sql
    await repo.mark_lesson(1, 10, 2, False)
    statement = session.execute.await_args.args[0]
    assert statement.compile().params == {"user_id_1": 1, "lesson_id_1": 2}


async def test_teacher_cannot_attach_question_to_foreign_lesson(
    service: QuizService, learner: UserDTO
) -> None:
    author = QuizAuthoringService(service.session, service.repository, service.access)
    service.access.manage = AsyncMock()
    data = QuestionWriteDTO(
        lesson_id=999, prompt="Q", options=question().options, correct_option="A", explanation="Why"
    )
    with pytest.raises(HTTPException) as error:
        await author.question(learner, 10, 20, 1, data)
    assert error.value.status_code == 422
    service.repository.save_question.assert_not_awaited()


async def test_quiz_enabling_requires_enough_active_questions(
    service: QuizService, learner: UserDTO
) -> None:
    author = QuizAuthoringService(service.session, service.repository, service.access)
    service.access.manage = AsyncMock()
    service.repository.active_count.return_value = 2
    with pytest.raises(HTTPException) as error:
        await author.configure(learner, 10, 20, 1, QuizWriteDTO(enabled=True))
    assert error.value.status_code == 422
    service.repository.save_config.assert_not_awaited()
