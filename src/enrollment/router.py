from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from src.auth.dependencies.current_user import ICurrentUser
from src.enrollment.dto import (
    AccessDTO,
    DecisionDTO,
    EnrollmentPageDTO,
    GrantDTO,
    GrantInputDTO,
    GrantPageDTO,
    RequestInputDTO,
    RequestPageDTO,
    RequestStatus,
)
from src.enrollment.service import EnrollmentService

IEnrollmentService = Annotated[EnrollmentService, Depends()]
Id = Annotated[int, Path(gt=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Authorization"


router = APIRouter(tags=["Enrollment"], dependencies=[Depends(no_store)])
management_router = APIRouter(
    prefix="/access/courses", tags=["Access management"], dependencies=[Depends(no_store)]
)


@router.get("/me/courses", response_model=EnrollmentPageDTO)
async def mine(
    user: ICurrentUser, service: IEnrollmentService, limit: Limit = 20, offset: Offset = 0
) -> EnrollmentPageDTO:
    return await service.mine(user, limit, offset)


@router.get("/courses/{course_id}/access", response_model=AccessDTO)
async def access(course_id: Id, user: ICurrentUser, service: IEnrollmentService) -> AccessDTO:
    return await service.status(user, course_id)


@router.post("/courses/{course_id}/enrollment", response_model=AccessDTO)
async def enroll(course_id: Id, user: ICurrentUser, service: IEnrollmentService) -> AccessDTO:
    return await service.enroll(user, course_id)


@router.delete("/courses/{course_id}/enrollment", status_code=204)
async def leave(course_id: Id, user: ICurrentUser, service: IEnrollmentService) -> None:
    await service.leave(user, course_id)


@router.post("/courses/{course_id}/access-requests", response_model=AccessDTO)
async def request_access(
    course_id: Id, data: RequestInputDTO, user: ICurrentUser, service: IEnrollmentService
) -> AccessDTO:
    return await service.request_access(user, course_id, data)


@router.delete("/courses/{course_id}/access-requests/{request_id}", response_model=AccessDTO)
async def cancel(
    course_id: Id, request_id: Id, user: ICurrentUser, service: IEnrollmentService
) -> AccessDTO:
    return await service.cancel(user, course_id, request_id)


@management_router.get("/{course_id}/requests", response_model=RequestPageDTO)
async def requests(
    course_id: Id,
    user: ICurrentUser,
    service: IEnrollmentService,
    limit: Limit = 20,
    offset: Offset = 0,
    status: Annotated[RequestStatus | None, Query()] = "pending",
) -> RequestPageDTO:
    return await service.requests(user, course_id, status, limit, offset)


@management_router.put("/{course_id}/requests/{request_id}", status_code=204)
async def decide(
    course_id: Id,
    request_id: Id,
    data: DecisionDTO,
    user: ICurrentUser,
    service: IEnrollmentService,
) -> None:
    await service.decide(user, course_id, request_id, data)


@management_router.get("/{course_id}/grants", response_model=GrantPageDTO)
async def grants(
    course_id: Id,
    user: ICurrentUser,
    service: IEnrollmentService,
    active_only: bool = True,
    limit: Limit = 20,
    offset: Offset = 0,
) -> GrantPageDTO:
    return await service.grants(user, course_id, active_only, limit, offset)


@management_router.post("/{course_id}/grants", response_model=GrantDTO, status_code=201)
async def grant(
    course_id: Id, data: GrantInputDTO, user: ICurrentUser, service: IEnrollmentService
) -> GrantDTO:
    return await service.grant(user, course_id, data)


@management_router.delete("/{course_id}/grants/{grant_id}", status_code=204)
async def revoke(
    course_id: Id, grant_id: Id, user: ICurrentUser, service: IEnrollmentService
) -> None:
    await service.revoke(user, course_id, grant_id)
