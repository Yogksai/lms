from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.libs.base_model import Base


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    session_id: Mapped[int] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
