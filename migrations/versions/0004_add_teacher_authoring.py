"""Add account roles, course lifecycle and teacher assignments."""

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("role", sa.String(20), server_default="student", nullable=False)
    )
    op.create_check_constraint("role_valid", "users", "role IN ('student', 'teacher', 'admin')")
    op.add_column(
        "courses", sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(
        "courses", sa.Column("revision", sa.Integer(), server_default="1", nullable=False)
    )
    op.create_check_constraint("status_valid", "courses", "NOT (is_published AND is_archived)")
    op.create_check_constraint("revision_positive", "courses", "revision > 0")
    op.create_table(
        "teacher_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("course_id", "user_id"),
    )
    op.create_index(op.f("ix_teacher_assignments_user_id"), "teacher_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_table("teacher_assignments")
    op.drop_constraint(op.f("ck_courses_revision_positive"), "courses", type_="check")
    op.drop_constraint(op.f("ck_courses_status_valid"), "courses", type_="check")
    op.drop_column("courses", "revision")
    op.drop_column("courses", "is_archived")
    op.drop_constraint(op.f("ck_users_role_valid"), "users", type_="check")
    op.drop_column("users", "role")
