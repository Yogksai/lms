from typing import Annotated

from fastapi import Depends

from src.auth.service.account import AccountService

IAccountService = Annotated[AccountService, Depends()]
