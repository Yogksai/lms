from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.libs.base_model import Base


class LearningOutboxModel(Base):
    __tablename__ = "learning_outbox"
    __table_args__ = (CheckConstraint("failures >= 0", name="failures_valid"),)
    event_id: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    failures: Mapped[int] = mapped_column(default=0, server_default="0")


class LearningNotificationModel(Base):
    __tablename__ = "learning_notifications"
    event_id: Mapped[UUID] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
