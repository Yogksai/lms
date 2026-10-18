from typing import Annotated

from fastapi import Depends

from src.authoring.repository import AuthoringRepo

IAuthoringRepo = Annotated[AuthoringRepo, Depends()]
