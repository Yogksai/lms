from typing import Annotated

from fastapi import Depends

from src.auth.service.token import TokenService
from src.config.jwt import get_settings as get_jwt_settings
from src.config.security import get_settings as get_security_settings


def get_token_service() -> TokenService:
    return TokenService(get_jwt_settings(), get_security_settings())


ITokenService = Annotated[TokenService, Depends(get_token_service)]
