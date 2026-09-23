from dataclasses import dataclass


@dataclass(frozen=True)
class UserEntity:
    name: str
    email: str
    password_hash: str | None = None
