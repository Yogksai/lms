from fastapi import APIRouter

from src.auth.router import router as auth_router
from src.authoring.router import admin_router
from src.authoring.router import router as authoring_router
from src.courses.router import router as courses_router
from src.enrollment.router import management_router
from src.enrollment.router import router as enrollment_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(courses_router)
router.include_router(authoring_router)
router.include_router(admin_router)
router.include_router(enrollment_router)
router.include_router(management_router)
