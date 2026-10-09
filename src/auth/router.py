from fastapi import APIRouter, Response, status

from src.auth.dependencies.account import IAccountService
from src.auth.dependencies.current_user import ICurrentUser
from src.auth.dto import LoginDTO, ProfileUpdateDTO, RefreshDTO, RegisterDTO, TokenPairDTO, UserDTO

router = APIRouter(
    prefix="/auth", tags=["Accounts"], responses={401: {"description": "Invalid credentials"}}
)


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.post(
    "/register",
    response_model=UserDTO,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Account exists"}},
)
async def register(data: RegisterDTO, service: IAccountService, response: Response) -> UserDTO:
    no_store(response)
    return await service.register(data)


@router.post("/login", response_model=TokenPairDTO)
async def login(data: LoginDTO, service: IAccountService, response: Response) -> TokenPairDTO:
    no_store(response)
    return await service.login(data)


@router.post("/refresh", response_model=TokenPairDTO)
async def refresh(data: RefreshDTO, service: IAccountService, response: Response) -> TokenPairDTO:
    no_store(response)
    return await service.refresh(data.refresh_token.get_secret_value())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshDTO, service: IAccountService, response: Response) -> None:
    no_store(response)
    await service.logout(data.refresh_token.get_secret_value())


@router.get("/me", response_model=UserDTO)
async def me(user: ICurrentUser, response: Response) -> UserDTO:
    no_store(response)
    return user


@router.patch("/me", response_model=UserDTO)
async def update_profile(
    data: ProfileUpdateDTO, user: ICurrentUser, service: IAccountService, response: Response
) -> UserDTO:
    no_store(response)
    return await service.update_profile(user.id, data)
