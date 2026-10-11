from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.libs.base_model import Base

if TYPE_CHECKING:
    from src.courses.models.module import ModuleModel


class LessonModel(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("module_id", "position"),
        CheckConstraint("position > 0", name="position_positive"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
        CheckConstraint("length(trim(summary)) > 0", name="summary_not_empty"),
    )

    module_id: Mapped[int] = mapped_column(ForeignKey("course_modules.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int]
    summary: Mapped[str] = mapped_column(Text)
    video_url: Mapped[str] = mapped_column(String(2048))
    module: Mapped[ModuleModel] = relationship(back_populates="lessons", lazy="raise")
