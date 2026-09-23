from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True)


class PasswordService:
    """Run bcrypt outside the event loop; reject silent byte truncation."""

    @staticmethod
    async def get_password_hash(password: str) -> str:
        if not password or len(password.encode("utf-8")) > 72:
            raise ValueError("Password must contain between 1 and 72 UTF-8 bytes")
        hashed: str = await run_in_threadpool(pwd_context.hash, password)
        return hashed

    @staticmethod
    async def verify_password(password: str, password_hash: str | None) -> bool:
        if not password_hash or not password or len(password.encode("utf-8")) > 72:
            return False
        verified: bool = await run_in_threadpool(pwd_context.verify, password, password_hash)
        return verified
