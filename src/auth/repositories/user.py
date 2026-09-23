from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.auth.dto import UserCredentialsDTO, UserDTO
from src.auth.entities import UserEntity
from src.auth.exceptions import UserAlreadyExists
from src.auth.models.user import UserModel
from src.config.db.session import ISession


class UserRepo:
    def __init__(self, session: ISession) -> None:
        self.session = session

    async def create(self, user: UserEntity) -> UserDTO:
        instance = UserModel(name=user.name, email=user.email, password_hash=user.password_hash)
        self.session.add(instance)
        try:
            await self.session.flush()
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise UserAlreadyExists from error
            raise
        return UserDTO.model_validate(instance)

    async def get(self, pk: int) -> UserDTO | None:
        instance = await self.session.get(UserModel, pk)
        return UserDTO.model_validate(instance) if instance is not None else None

    async def find_credentials(self, email: str) -> UserCredentialsDTO | None:
        result = await self.session.execute(select(UserModel).where(UserModel.email == email))
        instance = result.scalar_one_or_none()
        return UserCredentialsDTO.model_validate(instance) if instance is not None else None
