from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.auth.dto import Role, UserDTO
from src.courses.dto import Description, LessonDTO, Position, Slug, Summary, Title

Status = Literal["draft", "published", "archived"]


class WriteDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseWriteDTO(WriteDTO):
    slug: Slug
    title: Title
    description: Description = ""


class ModuleWriteDTO(WriteDTO):
    title: Title
    description: Description = ""


class LessonWriteDTO(WriteDTO):
    title: Title
    summary: Summary
    video_url: str = Field(max_length=2048)

    @field_validator("video_url")
    @classmethod
    def validate_video(cls, value: str) -> str:
        return LessonDTO.validate_youtube_url(value)


class OrderDTO(WriteDTO):
    ids: list[int] = Field(max_length=1000)

    @field_validator("ids")
    @classmethod
    def unique_positive(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)) or any(value <= 0 for value in values):
            raise ValueError("IDs must be unique positive integers")
        return values


class StatusDTO(WriteDTO):
    status: Status


class RoleDTO(WriteDTO):
    role: Role


class AssignmentDTO(WriteDTO):
    user_id: int = Field(gt=0)


class EditorLessonDTO(LessonWriteDTO):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    position: Position


class EditorModuleDTO(ModuleWriteDTO):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    position: Position
    lessons: list[EditorLessonDTO]


class EditorCourseDTO(CourseWriteDTO):
    id: int
    status: Status
    revision: int
    modules: list[EditorModuleDTO]
    teachers: list[UserDTO]


class EditorCourseSummaryDTO(CourseWriteDTO):
    id: int
    status: Status
    revision: int


class EditorCoursePageDTO(BaseModel):
    items: list[EditorCourseSummaryDTO]
    total: int
    limit: int
    offset: int


class UserPageDTO(BaseModel):
    items: list[UserDTO]
    total: int
    limit: int
    offset: int
