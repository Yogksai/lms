from typing import Annotated

from fastapi import Depends

from src.auth.repositories.session import SessionRepo

ISessionRepository = Annotated[SessionRepo, Depends()]
