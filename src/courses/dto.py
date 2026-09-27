from typing import Annotated
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Slug = Annotated[
    str, StringConstraints(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
Position = Annotated[int, Field(gt=0)]


class LessonOutlineDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    title: Title
    position: Position


class LessonDTO(LessonOutlineDTO):
    summary: Summary
    video_url: Annotated[str, StringConstraints(max_length=2048)]

    @field_validator("video_url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        url = urlparse(value)
        if url.scheme != "https" or url.username or url.password or url.netloc != url.hostname:
            raise ValueError("Video must be an HTTPS YouTube URL")
        if url.hostname == "youtu.be":
            video_id = url.path.removeprefix("/")
        elif url.hostname in {"youtube.com", "www.youtube.com"}:
            if url.path == "/watch":
                video_id = parse_qs(url.query).get("v", [""])[0]
            elif url.path.startswith(("/embed/", "/shorts/")):
                video_id = url.path.split("/")[-1]
            else:
                video_id = ""
        else:
            video_id = ""
        if len(video_id) != 11 or not all(
            c.isascii() and (c.isalnum() or c in "-_") for c in video_id
        ):
            raise ValueError("Video must include a valid YouTube video ID")
        return value


class ModuleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: Title
    description: Description
    position: Position
    lessons: list[LessonOutlineDTO] = Field(default_factory=list)
    is_preview: bool = False


class CourseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: Slug
    title: Title
    description: Description


class CourseDetailDTO(CourseDTO):
    modules: list[ModuleDTO]


class CoursePageDTO(BaseModel):
    items: list[CourseDTO]
    total: int
    limit: int
    offset: int
