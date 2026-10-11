from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.libs.base_model import Base

if TYPE_CHECKING:
    from src.courses.models.module import ModuleModel


class CourseModel(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
        CheckConstraint("NOT (is_published AND is_archived)", name="status_valid"),
        CheckConstraint("revision > 0", name="revision_positive"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(default=False, server_default=false(), index=True)
    is_archived: Mapped[bool] = mapped_column(default=False, server_default=false())
    revision: Mapped[int] = mapped_column(default=1, server_default="1")
    modules: Mapped[list[ModuleModel]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ModuleModel.position",
        lazy="raise",
    )
