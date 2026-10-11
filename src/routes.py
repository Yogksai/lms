from fastapi import APIRouter

from src.courses.router import router as courses_router

router = APIRouter(prefix="/v1")
router.include_router(courses_router)
