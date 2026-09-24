from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.cors import get_settings


def init_middleware(app: FastAPI) -> None:
    settings = get_settings()
    if settings.allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allow_origins,
            allow_credentials=settings.allow_credentials,
            allow_methods=settings.allow_methods,
            allow_headers=settings.allow_headers,
        )
