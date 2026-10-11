from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.libs.base_model import Base


class TeacherAssignmentModel(Base):
    __tablename__ = "teacher_assignments"
    __table_args__ = (UniqueConstraint("course_id", "user_id"),)

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
