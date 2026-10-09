from fastapi import APIRouter

from src.auth.router import router as auth_router
from src.courses.router import router as courses_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(courses_router)
