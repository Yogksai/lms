from fastapi import FastAPI

from src.config.project import get_settings
from src.exceptions import init_exception_handlers
from src.health.router import router as health_router
from src.lifespan import lifespan
from src.middleware import init_middleware
from src.routes import router


def get_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.title,
        version=settings.version,
        root_path=settings.root_path,
        debug=settings.debug,
        lifespan=lifespan,
    )
    init_middleware(app)
    init_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(router)
    return app


app = get_app()
