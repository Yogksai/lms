from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.db.settings import Settings


class DatabaseHelper:
    """Manage PostgreSQL connections; callers own use-case transactions."""

    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.echo,
            pool_pre_ping=True,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.connect_timeout,
            connect_args={
                "timeout": settings.connect_timeout,
                "command_timeout": settings.command_timeout,
            },
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    @asynccontextmanager
    async def get_db_session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def check_connection(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()
