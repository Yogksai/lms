from typing import Annotated

from fastapi import Depends

from src.enrollment.service import EnrollmentService

IEnrollmentService = Annotated[EnrollmentService, Depends()]
