from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.auth.dto import UserDTO
from src.courses.dto import CourseDTO

RequestStatus = Literal["pending", "approved", "rejected", "cancelled"]
GrantSource = Literal["teacher_approval", "admin_grant"]
AccessReason = Literal["admin", "assigned_teacher", "teacher_approval", "admin_grant"]


class RequestInputDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(default="", max_length=2000)


class DecisionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    duration_days: int = Field(default=90, ge=1, le=365)
    note: str = Field(default="", max_length=1000)


class GrantInputDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(gt=0)
    duration_days: int = Field(default=90, ge=1, le=365)


class RequestDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    user_id: int
    message: str
    status: RequestStatus
    created_at: datetime
    decided_at: datetime | None
    decided_by: int | None
    decision_note: str


class GrantDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    user_id: int
    source: GrantSource
    request_id: int | None
    granted_by: int | None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    revoked_by: int | None


class AccessDTO(BaseModel):
    course_id: int
    available: bool
    enrolled: bool
    full_access: bool
    reasons: list[AccessReason]
    expires_at: datetime | None
    request: RequestDTO | None
    grants: list[GrantDTO]


class EnrollmentDTO(BaseModel):
    course: CourseDTO
    enrolled_at: datetime
    available: bool


class EnrollmentPageDTO(BaseModel):
    items: list[EnrollmentDTO]
    total: int
    limit: int
    offset: int


class ManagedRequestDTO(RequestDTO):
    student: UserDTO


class RequestPageDTO(BaseModel):
    items: list[ManagedRequestDTO]
    total: int
    limit: int
    offset: int


class ManagedGrantDTO(GrantDTO):
    student: UserDTO
    active: bool


class GrantPageDTO(BaseModel):
    items: list[ManagedGrantDTO]
    total: int
    limit: int
    offset: int
