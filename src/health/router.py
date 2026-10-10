from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.health.dto import HealthDTO
from src.health.service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])
IHealthService = Annotated[HealthService, Depends()]


@router.get("/live", response_model=HealthDTO)
async def live() -> HealthDTO:
    return HealthDTO(status="ok")


@router.get("/ready", response_model=HealthDTO, responses={503: {"model": HealthDTO}})
async def ready(service: IHealthService, response: Response) -> HealthDTO:
    if not await service.is_ready():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthDTO(status="unavailable")
    return HealthDTO(status="ok")
