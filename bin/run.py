import uvicorn

from src.config.project import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run("src.app:app", host=settings.host, port=settings.port, reload=settings.debug)


if __name__ == "__main__":
    main()
