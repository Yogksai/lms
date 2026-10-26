from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.libs.base_model import Base


class QuizModel(Base):
    __tablename__ = "module_quizzes"
    __table_args__ = (
        CheckConstraint("question_count BETWEEN 1 AND 100", name="count_valid"),
        CheckConstraint("passing_score BETWEEN 1 AND 100", name="score_valid"),
        CheckConstraint("time_limit_seconds BETWEEN 60 AND 7200", name="time_valid"),
        CheckConstraint("revision > 0", name="revision_valid"),
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("course_modules.id", ondelete="CASCADE"), unique=True
    )
    question_count: Mapped[int] = mapped_column(default=10, server_default="10")
    passing_score: Mapped[int] = mapped_column(default=70, server_default="70")
    time_limit_seconds: Mapped[int] = mapped_column(default=600, server_default="600")
    enabled: Mapped[bool] = mapped_column(default=False, server_default=false())
    revision: Mapped[int] = mapped_column(default=1, server_default="1")


class QuestionModel(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        CheckConstraint("length(trim(prompt)) > 0", name="prompt_valid"),
        CheckConstraint("correct_option IN ('A', 'B', 'C', 'D')", name="answer_valid"),
        CheckConstraint(
            "jsonb_typeof(options) = 'object' AND options ?& ARRAY['A','B','C','D'] "
            "AND options - ARRAY['A','B','C','D'] = '{}'::jsonb",
            name="options_valid",
        ),
        CheckConstraint("length(trim(explanation)) > 0", name="explanation_valid"),
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("course_modules.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[dict[str, str]] = mapped_column(JSONB)
    correct_option: Mapped[str] = mapped_column(String(1))
    explanation: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class AttemptModel(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'submitted', 'expired')", name="status_valid"),
        CheckConstraint(
            "jsonb_typeof(snapshot) = 'array' AND jsonb_array_length(snapshot) BETWEEN 1 AND 100",
            name="snapshot_valid",
        ),
        CheckConstraint("deadline_at > started_at", name="deadline_valid"),
        CheckConstraint("passing_score BETWEEN 1 AND 100", name="passing_valid"),
        CheckConstraint(
            "(status = 'submitted' AND submitted_at IS NOT NULL "
            "AND correct_count IS NOT NULL AND score_percent IS NOT NULL "
            "AND correct_count BETWEEN 0 AND jsonb_array_length(snapshot) "
            "AND score_percent BETWEEN 0 AND 100 AND passed IS NOT NULL) "
            "OR (status <> 'submitted' AND submitted_at IS NULL AND correct_count IS NULL "
            "AND score_percent IS NULL AND passed IS NULL)",
            name="result_valid",
        ),
        Index(
            "uq_quiz_attempts_open",
            "user_id",
            "module_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
        Index("ix_quiz_attempts_daily", "user_id", "original_module_id", "started_at"),
    )
    attempt_key: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_modules.id", ondelete="SET NULL"), nullable=True
    )
    quiz_id: Mapped[int | None] = mapped_column(
        ForeignKey("module_quizzes.id", ondelete="SET NULL"), nullable=True
    )
    original_module_id: Mapped[int]
    module_title: Mapped[str] = mapped_column(String(200))
    quiz_revision: Mapped[int]
    passing_score: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", server_default="in_progress"
    )
    snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
    answers: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correct_count: Mapped[int | None] = mapped_column(nullable=True)
    score_percent: Mapped[int | None] = mapped_column(nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)


class LessonProgressModel(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
