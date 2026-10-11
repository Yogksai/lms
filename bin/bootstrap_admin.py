"""Promote one existing active account only when no active admin exists."""

import argparse
import asyncio

from src.authoring.repository import AuthoringRepo
from src.config.db.engine import DatabaseHelper
from src.config.db.settings import get_settings


async def bootstrap(email: str) -> None:
    database = DatabaseHelper(get_settings())
    try:
        async with database.get_db_session() as session, session.begin():
            repository = AuthoringRepo(session)
            await repository.role_lock()
            if await repository.has_admin():
                raise ValueError("An active admin already exists; use admin role management")
            user = await repository.user_by_email(email.strip())
            if user is None or not user.is_active:
                raise ValueError("Bootstrap requires an existing active account")
            await repository.set_role(user.id, "admin")
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    args = parser.parse_args()
    try:
        asyncio.run(bootstrap(args.email))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print("Initial admin role assigned.")


if __name__ == "__main__":
    main()
