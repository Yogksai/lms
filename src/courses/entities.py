from dataclasses import dataclass


@dataclass(frozen=True)
class LessonEntity:
    title: str
    position: int
    summary: str
    video_url: str


@dataclass(frozen=True)
class ModuleEntity:
    title: str
    description: str
    position: int
    lessons: tuple[LessonEntity, ...]


@dataclass(frozen=True)
class CourseEntity:
    slug: str
    title: str
    description: str
    modules: tuple[ModuleEntity, ...]
    is_published: bool = False
