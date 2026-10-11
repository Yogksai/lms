from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.libs.base_model import Base

if TYPE_CHECKING:
    from src.courses.models.course import CourseModel
    from src.courses.models.lesson import LessonModel


class ModuleModel(Base):
    __tablename__ = "course_modules"
    __table_args__ = (
        UniqueConstraint("course_id", "position"),
        CheckConstraint("position > 0", name="position_positive"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
    )

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    course: Mapped[CourseModel] = relationship(back_populates="modules", lazy="raise")
    lessons: Mapped[list[LessonModel]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LessonModel.position",
        lazy="raise",
    )
