from sqlalchemy import func, select, update
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
        instance = UserModel(
            name=user.name,
            email=user.email.lower(),
            password_hash=user.password_hash,
            is_active=user.is_active,
        )
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
        result = await self.session.execute(
            select(UserModel).where(func.lower(UserModel.email) == email.lower())
        )
        instance = result.scalar_one_or_none()
        return UserCredentialsDTO.model_validate(instance) if instance is not None else None

    async def update_name(self, user_id: int, name: str) -> UserDTO | None:
        instance = await self.session.scalar(
            update(UserModel)
            .where(UserModel.id == user_id, UserModel.is_active.is_(True))
            .values(name=name)
            .returning(UserModel)
        )
        return UserDTO.model_validate(instance) if instance is not None else None
