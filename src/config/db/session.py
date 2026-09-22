from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.db.engine import DatabaseHelper


def get_database_helper(request: Request) -> DatabaseHelper:
    helper: DatabaseHelper = request.app.state.database
    return helper


IDatabaseHelper = Annotated[DatabaseHelper, Depends(get_database_helper)]


async def get_session(helper: IDatabaseHelper) -> AsyncIterator[AsyncSession]:
    async with helper.get_db_session() as session:
        yield session


ISession = Annotated[AsyncSession, Depends(get_session)]
