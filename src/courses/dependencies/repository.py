from typing import Annotated

from fastapi import Depends

from src.courses.repositories.course import CourseRepo

ICourseRepository = Annotated[CourseRepo, Depends()]
