"""Add enrollment, access requests, and expiring independent grants."""

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def common_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "enrollments",
        *common_columns(),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("course_id", "user_id"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])
    op.create_table(
        "access_requests",
        *common_columns(),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decision_note", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')", name="status_valid"
        ),
        sa.CheckConstraint("(status = 'pending') = (decided_at IS NULL)", name="decision_valid"),
    )
    op.create_index("ix_access_requests_user_id", "access_requests", ["user_id"])
    op.create_index(
        "uq_access_requests_pending",
        "access_requests",
        ["course_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "access_grants",
        *common_columns(),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column(
            "request_id",
            sa.Integer(),
            sa.ForeignKey("access_requests.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("granted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint("source IN ('teacher_approval', 'admin_grant')", name="source_valid"),
        sa.CheckConstraint("expires_at > created_at", name="expiry_valid"),
        sa.CheckConstraint(
            "(source = 'teacher_approval') = (request_id IS NOT NULL)", name="request_valid"
        ),
    )
    op.create_index("ix_access_grants_course_user", "access_grants", ["course_id", "user_id"])


def downgrade() -> None:
    op.drop_table("access_grants")
    op.drop_table("access_requests")
    op.drop_table("enrollments")
