"""Add module quizzes, immutable attempts, lesson progress and learning outbox."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def fk(
    name: str, target: str, *, action: str = "CASCADE", nullable: bool = False, unique: bool = False
) -> sa.Column:
    return sa.Column(
        name, sa.Integer(), sa.ForeignKey(target, ondelete=action), nullable=nullable, unique=unique
    )


def upgrade() -> None:
    op.create_table(
        "module_quizzes",
        *common(),
        fk("module_id", "course_modules.id", unique=True),
        sa.Column("question_count", sa.Integer(), server_default="10", nullable=False),
        sa.Column("passing_score", sa.Integer(), server_default="70", nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), server_default="600", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("question_count BETWEEN 1 AND 100", name="count_valid"),
        sa.CheckConstraint("passing_score BETWEEN 1 AND 100", name="score_valid"),
        sa.CheckConstraint("time_limit_seconds BETWEEN 60 AND 7200", name="time_valid"),
        sa.CheckConstraint("revision > 0", name="revision_valid"),
    )
    op.create_table(
        "quiz_questions",
        *common(),
        fk("module_id", "course_modules.id"),
        fk("lesson_id", "lessons.id"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", pg.JSONB(), nullable=False),
        sa.Column("correct_option", sa.String(1), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("length(trim(prompt)) > 0", name="prompt_valid"),
        sa.CheckConstraint("correct_option IN ('A', 'B', 'C', 'D')", name="answer_valid"),
        sa.CheckConstraint(
            "jsonb_typeof(options) = 'object' AND options ?& ARRAY['A','B','C','D'] "
            "AND options - ARRAY['A','B','C','D'] = '{}'::jsonb",
            name="options_valid",
        ),
        sa.CheckConstraint("length(trim(explanation)) > 0", name="explanation_valid"),
    )
    op.create_index("ix_quiz_questions_module_id", "quiz_questions", ["module_id"])
    op.create_index("ix_quiz_questions_lesson_id", "quiz_questions", ["lesson_id"])
    op.create_table(
        "quiz_attempts",
        *common(),
        sa.Column("attempt_key", sa.Uuid(), unique=True, nullable=False),
        fk("user_id", "users.id"),
        fk("course_id", "courses.id"),
        fk("module_id", "course_modules.id", action="SET NULL", nullable=True),
        fk("quiz_id", "module_quizzes.id", action="SET NULL", nullable=True),
        sa.Column("original_module_id", sa.Integer(), nullable=False),
        sa.Column("module_title", sa.String(200), nullable=False),
        sa.Column("quiz_revision", sa.Integer(), nullable=False),
        sa.Column("passing_score", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
        sa.Column("snapshot", pg.JSONB(), nullable=False),
        sa.Column("answers", pg.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("correct_count", sa.Integer()),
        sa.Column("score_percent", sa.Integer()),
        sa.Column("passed", sa.Boolean()),
        sa.CheckConstraint(
            "status IN ('in_progress', 'submitted', 'expired')", name="status_valid"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(snapshot) = 'array' AND jsonb_array_length(snapshot) BETWEEN 1 AND 100",
            name="snapshot_valid",
        ),
        sa.CheckConstraint("deadline_at > started_at", name="deadline_valid"),
        sa.CheckConstraint("passing_score BETWEEN 1 AND 100", name="passing_valid"),
        sa.CheckConstraint(
            "(status = 'submitted' AND submitted_at IS NOT NULL "
            "AND correct_count IS NOT NULL AND score_percent IS NOT NULL "
            "AND correct_count BETWEEN 0 AND jsonb_array_length(snapshot) "
            "AND score_percent BETWEEN 0 AND 100 AND passed IS NOT NULL) "
            "OR (status <> 'submitted' AND submitted_at IS NULL AND correct_count IS NULL "
            "AND score_percent IS NULL AND passed IS NULL)",
            name="result_valid",
        ),
    )
    op.create_index(
        "uq_quiz_attempts_open",
        "quiz_attempts",
        ["user_id", "module_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.create_index(
        "ix_quiz_attempts_daily", "quiz_attempts", ["user_id", "original_module_id", "started_at"]
    )
    op.create_table(
        "lesson_progress",
        *common(),
        fk("user_id", "users.id"),
        fk("course_id", "courses.id"),
        fk("lesson_id", "lessons.id"),
        sa.UniqueConstraint("user_id", "lesson_id"),
    )
    op.create_table(
        "learning_outbox",
        *common(),
        sa.Column("event_id", sa.Uuid(), unique=True, nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("failures", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("failures >= 0", name="failures_valid"),
    )
    op.create_index("ix_learning_outbox_next_attempt_at", "learning_outbox", ["next_attempt_at"])
    op.create_table(
        "learning_notifications",
        *common(),
        sa.Column("event_id", sa.Uuid(), unique=True, nullable=False),
        fk("user_id", "users.id"),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("link", sa.String(300), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_learning_notifications_user_id", "learning_notifications", ["user_id"])


def downgrade() -> None:
    for table in (
        "learning_notifications",
        "learning_outbox",
        "lesson_progress",
        "quiz_attempts",
        "quiz_questions",
        "module_quizzes",
    ):
        op.drop_table(table)
