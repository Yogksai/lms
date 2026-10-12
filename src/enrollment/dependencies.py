from typing import Annotated

from fastapi import Depends

from src.enrollment.repository import EnrollmentRepo

IEnrollmentRepo = Annotated[EnrollmentRepo, Depends()]
