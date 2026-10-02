import asyncio

from src.config.db.engine import DatabaseHelper
from src.config.db.settings import get_settings
from src.courses.repositories.course import CourseRepo
from src.courses.seed_data import COURSES
from src.courses.service.seed import SeedService


async def seed() -> int:
    database = DatabaseHelper(get_settings())
    try:
        async with database.get_db_session() as session:
            return await SeedService(session, CourseRepo(session)).seed(COURSES)
    finally:
        await database.dispose()


def main() -> None:
    created = asyncio.run(seed())
    print(f"Created {created} demo courses; existing course slugs were left unchanged.")


if __name__ == "__main__":
    main()
