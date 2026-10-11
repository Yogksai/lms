from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from src.auth.dependencies.current_user import ICurrentUser
from src.auth.dto import UserDTO
from src.authoring.dto import (
    AssignmentDTO,
    CourseWriteDTO,
    EditorCourseDTO,
    EditorCoursePageDTO,
    LessonWriteDTO,
    ModuleWriteDTO,
    OrderDTO,
    RoleDTO,
    StatusDTO,
    UserPageDTO,
)
from src.authoring.service import AuthoringService

IService = Annotated[AuthoringService, Depends()]
Id = Annotated[int, Path(gt=0)]
Revision = Annotated[int, Query(ge=1)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/authoring/courses", tags=["Authoring"], dependencies=[Depends(no_store)]
)
admin_router = APIRouter(prefix="/admin/users", tags=["Admin"], dependencies=[Depends(no_store)])


@router.get("", response_model=EditorCoursePageDTO)
async def catalog(
    user: ICurrentUser, service: IService, limit: Limit = 20, offset: Offset = 0
) -> EditorCoursePageDTO:
    return await service.list_courses(user, limit, offset)


@router.post("", response_model=EditorCourseDTO, status_code=201)
async def create(data: CourseWriteDTO, user: ICurrentUser, service: IService) -> EditorCourseDTO:
    return await service.create(user, data)


@router.get("/{course_id}", response_model=EditorCourseDTO)
async def detail(course_id: Id, user: ICurrentUser, service: IService) -> EditorCourseDTO:
    return await service.get(user, course_id)


@router.put("/{course_id}", response_model=EditorCourseDTO)
async def update(
    course_id: Id, revision: Revision, data: CourseWriteDTO, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.update_course(user, course_id, revision, data)


@router.put("/{course_id}/status", response_model=EditorCourseDTO)
async def status(
    course_id: Id, revision: Revision, data: StatusDTO, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.change_status(user, course_id, revision, data.status)


@router.post("/{course_id}/modules", response_model=EditorCourseDTO, status_code=201)
async def add_module(
    course_id: Id, revision: Revision, data: ModuleWriteDTO, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.add_module(user, course_id, revision, data)


@router.put("/{course_id}/modules/order", response_model=EditorCourseDTO)
async def module_order(
    course_id: Id, revision: Revision, data: OrderDTO, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.reorder(user, course_id, revision, data)


@router.put("/{course_id}/modules/{module_id}", response_model=EditorCourseDTO)
async def update_module(
    course_id: Id,
    module_id: Id,
    revision: Revision,
    data: ModuleWriteDTO,
    user: ICurrentUser,
    service: IService,
) -> EditorCourseDTO:
    return await service.update_module(user, course_id, module_id, revision, data)


@router.delete("/{course_id}/modules/{module_id}", response_model=EditorCourseDTO)
async def delete_module(
    course_id: Id, module_id: Id, revision: Revision, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.delete_module(user, course_id, module_id, revision)


@router.post(
    "/{course_id}/modules/{module_id}/lessons", response_model=EditorCourseDTO, status_code=201
)
async def add_lesson(
    course_id: Id,
    module_id: Id,
    revision: Revision,
    data: LessonWriteDTO,
    user: ICurrentUser,
    service: IService,
) -> EditorCourseDTO:
    return await service.add_lesson(user, course_id, module_id, revision, data)


@router.put("/{course_id}/modules/{module_id}/lessons/order", response_model=EditorCourseDTO)
async def lesson_order(
    course_id: Id,
    module_id: Id,
    revision: Revision,
    data: OrderDTO,
    user: ICurrentUser,
    service: IService,
) -> EditorCourseDTO:
    return await service.reorder(user, course_id, revision, data, module_id)


@router.put("/{course_id}/modules/{module_id}/lessons/{lesson_id}", response_model=EditorCourseDTO)
async def update_lesson(
    course_id: Id,
    module_id: Id,
    lesson_id: Id,
    revision: Revision,
    data: LessonWriteDTO,
    user: ICurrentUser,
    service: IService,
) -> EditorCourseDTO:
    return await service.update_lesson(user, course_id, module_id, lesson_id, revision, data)


@router.delete(
    "/{course_id}/modules/{module_id}/lessons/{lesson_id}", response_model=EditorCourseDTO
)
async def delete_lesson(
    course_id: Id,
    module_id: Id,
    lesson_id: Id,
    revision: Revision,
    user: ICurrentUser,
    service: IService,
) -> EditorCourseDTO:
    return await service.delete_lesson(user, course_id, module_id, lesson_id, revision)


@router.post("/{course_id}/teachers", response_model=EditorCourseDTO)
async def assign(
    course_id: Id, revision: Revision, data: AssignmentDTO, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.assign(user, course_id, revision, data.user_id)


@router.delete("/{course_id}/teachers/{user_id}", response_model=EditorCourseDTO)
async def unassign(
    course_id: Id, user_id: Id, revision: Revision, user: ICurrentUser, service: IService
) -> EditorCourseDTO:
    return await service.assign(user, course_id, revision, user_id, remove=True)


@admin_router.get("", response_model=UserPageDTO)
async def users(
    user: ICurrentUser,
    service: IService,
    limit: Limit = 20,
    offset: Offset = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> UserPageDTO:
    return await service.list_users(user, limit, offset, search.strip() if search else None)


@admin_router.put("/{user_id}/role", response_model=UserDTO)
async def role(user_id: Id, data: RoleDTO, user: ICurrentUser, service: IService) -> UserDTO:
    return await service.change_role(user, user_id, data)
