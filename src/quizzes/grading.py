from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.quizzes.dto import (
    Choice,
    PublicQuestionDTO,
    QuestionResultDTO,
    ResultDTO,
    ReviewDTO,
    SnapshotQuestion,
)


def daily_window(now: datetime, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    day = now.astimezone(zone).date()
    return (
        datetime.combine(day, time.min, zone).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC),
    )


def public_question(question: SnapshotQuestion) -> PublicQuestionDTO:
    return PublicQuestionDTO(**question.model_dump(exclude={"correct_option", "explanation"}))


def grade(
    snapshot: list[SnapshotQuestion],
    answers: dict[int, Choice],
    passing_score: int,
    current_lessons: set[int],
) -> ResultDTO:
    if not snapshot or not set(answers).issubset({question.question_id for question in snapshot}):
        raise ValueError("Answers must refer only to this attempt's questions")
    questions = []
    review: dict[int, ReviewDTO] = {}
    for question in snapshot:
        selected = answers.get(question.question_id)
        correct = selected == question.correct_option
        questions.append(
            QuestionResultDTO(
                **public_question(question).model_dump(),
                selected_option=selected,
                correct_option=question.correct_option,
                explanation=question.explanation,
                is_correct=correct,
            )
        )
        if not correct:
            if question.lesson_id not in review:
                review[question.lesson_id] = ReviewDTO(
                    lesson_id=question.lesson_id if question.lesson_id in current_lessons else None,
                    title=question.lesson_title,
                    wrong_answers=0,
                )
            review[question.lesson_id].wrong_answers += 1
    count = sum(question.is_correct for question in questions)
    return ResultDTO(
        correct_count=count,
        total=len(snapshot),
        score_percent=count * 100 // len(snapshot),
        passed=count * 100 >= passing_score * len(snapshot),
        questions=questions,
        review_lessons=sorted(review.values(), key=lambda item: -item.wrong_answers),
    )
