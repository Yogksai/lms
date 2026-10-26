from typing import Annotated

from fastapi import Depends

from src.quizzes.repository import QuizRepo

IQuizRepo = Annotated[QuizRepo, Depends()]
