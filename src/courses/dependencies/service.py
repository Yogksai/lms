from typing import Annotated

from fastapi import Depends

from src.courses.service.course import CourseService

ICourseService = Annotated[CourseService, Depends()]
