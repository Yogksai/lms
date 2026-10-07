from typing import Annotated

from fastapi import Depends

from src.auth.service.password import PasswordService

IPasswordService = Annotated[PasswordService, Depends()]
