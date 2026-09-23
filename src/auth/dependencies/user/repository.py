from typing import Annotated

from fastapi import Depends

from src.auth.repositories.user import UserRepo

IUserRepository = Annotated[UserRepo, Depends()]
