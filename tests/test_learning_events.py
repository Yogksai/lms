from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pamqp.commands import Basic

from src.learning_events.dto import QuizSubmitted
from src.learning_events.worker import consume, publish


def event() -> QuizSubmitted:
    return QuizSubmitted(
        user_id=1,
        course_id=2,
        attempt_id=uuid4(),
        module_title="Math",
        score_percent=70,
        passed=True,
    )


@pytest.mark.parametrize("confirm", [None, Basic.Nack(), Basic.Reject()])
async def test_only_positive_confirm_counts_as_publication(confirm: object) -> None:
    channel = AsyncMock()
    channel.default_exchange.publish.return_value = confirm
    with pytest.raises(RuntimeError):
        await publish(channel, b"{}")


async def test_notification_ack_happens_after_commit() -> None:
    sequence = []

    @asynccontextmanager
    async def transaction():
        yield
        sequence.append("commit")

    session = MagicMock()
    session.begin = transaction
    database = MagicMock()
    database.get_db_session.return_value.__aenter__ = AsyncMock(return_value=session)
    message = AsyncMock(body=event().model_dump_json().encode(), headers={})
    message.ack.side_effect = lambda: sequence.append("ack")
    with patch("src.learning_events.worker.LearningEventRepo") as repo:
        repo.return_value.deliver = AsyncMock()
        await consume(database, AsyncMock(), message)
    assert sequence == ["commit", "ack"]


@pytest.mark.parametrize("body", [b"bad", b"{}", b"x" * 32769])
async def test_invalid_messages_dead_lettered(body: bytes) -> None:
    message = AsyncMock(body=body, headers={})
    await consume(MagicMock(), AsyncMock(), message)
    message.reject.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_awaited()


@pytest.mark.parametrize("retry", [0, 5])
async def test_failure_uses_delayed_retry_then_dead_letter(retry: int) -> None:
    database = MagicMock()
    database.get_db_session.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError())
    message = AsyncMock(body=event().model_dump_json().encode(), headers={"retry": retry})
    with patch("src.learning_events.worker.publish", new_callable=AsyncMock) as send:
        await consume(database, AsyncMock(), message)
        if retry == 0:
            send.assert_awaited_once()
            assert send.await_args.kwargs["retry"] == 1
            message.ack.assert_awaited_once()
        else:
            send.assert_not_awaited()
            message.reject.assert_awaited_once_with(requeue=False)
