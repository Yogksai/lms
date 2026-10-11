"""Create courses, ordered modules, and ordered lessons."""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("slug", name=op.f("uq_courses_slug")),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_courses_title_not_empty")),
    )
    op.create_index(op.f("ix_courses_is_published"), "courses", ["is_published"])
    op.create_table(
        "course_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_modules")),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            ondelete="CASCADE",
            name=op.f("fk_course_modules_course_id_courses"),
        ),
        sa.UniqueConstraint("course_id", "position", name=op.f("uq_course_modules_course_id")),
        sa.CheckConstraint("position > 0", name=op.f("ck_course_modules_position_positive")),
        sa.CheckConstraint(
            "length(trim(title)) > 0", name=op.f("ck_course_modules_title_not_empty")
        ),
    )
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("video_url", sa.String(2048), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lessons")),
        sa.ForeignKeyConstraint(
            ["module_id"],
            ["course_modules.id"],
            ondelete="CASCADE",
            name=op.f("fk_lessons_module_id_course_modules"),
        ),
        sa.UniqueConstraint("module_id", "position", name=op.f("uq_lessons_module_id")),
        sa.CheckConstraint("position > 0", name=op.f("ck_lessons_position_positive")),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_lessons_title_not_empty")),
        sa.CheckConstraint("length(trim(summary)) > 0", name=op.f("ck_lessons_summary_not_empty")),
    )


def downgrade() -> None:
    op.drop_table("lessons")
    op.drop_table("course_modules")
    op.drop_index(op.f("ix_courses_is_published"), table_name="courses")
    op.drop_table("courses")
