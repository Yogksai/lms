from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from src.courses.dto import LessonOutlineDTO

Choice = Literal["A", "B", "C", "D"]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Option = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class WriteDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuizWriteDTO(WriteDTO):
    question_count: int = Field(10, ge=1, le=100)
    passing_score: int = Field(70, ge=1, le=100)
    time_limit_seconds: int = Field(600, ge=60, le=7200)
    enabled: bool = False


class QuizDTO(QuizWriteDTO):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module_id: int
    revision: int


class QuestionWriteDTO(WriteDTO):
    lesson_id: int = Field(gt=0)
    prompt: NonEmpty
    options: dict[Choice, Option]
    correct_option: Choice
    explanation: NonEmpty
    is_active: bool = True

    @field_validator("options")
    @classmethod
    def four_options(cls, value: dict[Choice, str]) -> dict[Choice, str]:
        if set(value) != {"A", "B", "C", "D"}:
            raise ValueError("Exactly four options A, B, C, D are required")
        return value


class QuestionDTO(QuestionWriteDTO):
    id: int
    module_id: int
    lesson_title: str


class BankDTO(BaseModel):
    module_id: int
    title: str
    course_status: Literal["draft", "published", "archived"]
    lessons: list[LessonOutlineDTO]
    config: QuizDTO | None
    active_questions: int
    items: list[QuestionDTO]
    total: int
    limit: int
    offset: int


class SnapshotQuestion(BaseModel):
    question_id: int
    lesson_id: int
    lesson_title: str
    prompt: str
    options: dict[Choice, str]
    correct_option: Choice
    explanation: str


class PublicQuestionDTO(BaseModel):
    question_id: int
    lesson_id: int
    lesson_title: str
    prompt: str
    options: dict[Choice, str]


class QuestionResultDTO(PublicQuestionDTO):
    selected_option: Choice | None
    correct_option: Choice
    explanation: str
    is_correct: bool


class ReviewDTO(BaseModel):
    lesson_id: int | None
    title: str
    wrong_answers: int


class ResultDTO(BaseModel):
    correct_count: int
    total: int
    score_percent: int
    passed: bool
    questions: list[QuestionResultDTO]
    review_lessons: list[ReviewDTO]


class SubmitDTO(WriteDTO):
    answers: dict[int, Choice] = Field(max_length=100)


class AttemptRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    attempt_key: UUID
    user_id: int
    course_id: int
    module_id: int | None
    quiz_id: int | None
    original_module_id: int
    module_title: str
    quiz_revision: int
    passing_score: int
    started_at: datetime
    deadline_at: datetime
    status: Literal["in_progress", "submitted", "expired"]
    snapshot: list[SnapshotQuestion]
    answers: dict[int, Choice]
    submitted_at: datetime | None
    correct_count: int | None
    score_percent: int | None
    passed: bool | None


class AttemptDTO(BaseModel):
    attempt_id: UUID
    course_id: int
    module_id: int | None
    module_title: str
    quiz_revision: int
    passing_score: int
    started_at: datetime
    deadline_at: datetime
    server_time: datetime
    status: Literal["in_progress", "submitted", "expired"]
    questions: list[PublicQuestionDTO]
    answers: dict[int, Choice]
    result: ResultDTO | None


class QuizInfoDTO(BaseModel):
    module_id: int
    available: bool
    question_count: int
    passing_score: int
    time_limit_seconds: int
    remaining_today: int
    daily_limit: int
    reset_at: datetime
    timezone: str
    open_attempt: UUID | None


class AttemptSummaryDTO(BaseModel):
    attempt_id: UUID
    status: str
    started_at: datetime
    score_percent: int | None
    passed: bool | None


class AttemptPageDTO(BaseModel):
    items: list[AttemptSummaryDTO]
    total: int
    limit: int
    offset: int


class ModuleProgressDTO(BaseModel):
    module_id: int
    title: str
    lesson_count: int
    completed_lessons: int
    completed_lesson_ids: list[int]
    quiz_enabled: bool
    quiz_passed: bool
    best_score: int | None


class ProgressDTO(BaseModel):
    course_id: int
    modules: list[ModuleProgressDTO]
    lesson_count: int
    completed_lessons: int
    lesson_percent: int
    passed_modules: int
    module_count: int
    quiz_percent: int
    complete: bool
