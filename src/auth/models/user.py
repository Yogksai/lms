from sqlalchemy import CheckConstraint, Index, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from src.libs.base_model import Base


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'teacher', 'admin')", name="role_valid"),)

    name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False, server_default=false())
    role: Mapped[str] = mapped_column(String(20), default="student", server_default="student")


Index("ix_users_email_normalized", func.lower(UserModel.email), unique=True)
