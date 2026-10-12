from typing import Annotated

from fastapi import APIRouter, Path, Query, Response

from src.auth.dependencies.current_user import IOptionalUser
from src.courses.dependencies.service import ICourseService
from src.courses.dto import CourseDetailDTO, CoursePageDTO, LessonDTO, LessonOutlineDTO, ModuleDTO
from src.enrollment.dependencies_service import IEnrollmentService

router = APIRouter(
    prefix="/courses", tags=["Courses"], responses={404: {"description": "Content not found"}}
)
ContentId = Annotated[int, Path(gt=0)]


@router.get("", response_model=CoursePageDTO)
async def catalog(
    service: ICourseService,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> CoursePageDTO:
    return await service.list_courses(limit, offset, search.strip() if search else None)


@router.get("/{course_id}", response_model=CourseDetailDTO)
async def course_detail(course_id: ContentId, service: ICourseService) -> CourseDetailDTO:
    return await service.get_detail(course_id)


@router.get("/{course_id}/modules", response_model=list[ModuleDTO])
async def modules(course_id: ContentId, service: ICourseService) -> list[ModuleDTO]:
    return await service.list_modules(course_id)


@router.get("/{course_id}/modules/{module_id}/lessons", response_model=list[LessonOutlineDTO])
async def lessons(
    course_id: ContentId, module_id: ContentId, service: ICourseService
) -> list[LessonOutlineDTO]:
    return await service.list_lessons(course_id, module_id)


@router.get(
    "/{course_id}/modules/{module_id}/lessons/{lesson_id}",
    response_model=LessonDTO,
    responses={403: {"description": "Course access required"}},
)
async def lesson(
    course_id: ContentId,
    module_id: ContentId,
    lesson_id: ContentId,
    service: ICourseService,
    user: IOptionalUser,
    access_service: IEnrollmentService,
    response: Response,
) -> LessonDTO:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Authorization"
    full_access = await access_service.can_read(user, course_id) if user is not None else False
    return await service.get_lesson(course_id, module_id, lesson_id, full_access=full_access)
