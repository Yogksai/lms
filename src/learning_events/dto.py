from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class QuizSubmitted(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    type: Literal["quiz.submitted"] = "quiz.submitted"
    event_id: UUID = Field(default_factory=uuid4)
    user_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    attempt_id: UUID
    module_title: str = Field(max_length=200)
    score_percent: int = Field(ge=0, le=100)
    passed: bool


class NotificationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    message: str
    link: str
    created_at: datetime
    read_at: datetime | None


class NotificationPageDTO(BaseModel):
    items: list[NotificationDTO]
    total: int
    limit: int
    offset: int
