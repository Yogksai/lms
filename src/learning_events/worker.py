"""Run with python -m src.learning_events.worker publisher|consumer."""

import argparse
import asyncio
import logging
from datetime import UTC, datetime, timedelta

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage
from pamqp.commands import Basic
from pydantic import ValidationError
from sqlalchemy import select

from src.config.db.engine import DatabaseHelper
from src.config.db.settings import get_settings as db_settings
from src.config.rabbitmq import get_settings
from src.learning_events.dto import QuizSubmitted
from src.learning_events.models import LearningOutboxModel
from src.learning_events.repository import LearningEventRepo

logger = logging.getLogger(__name__)


async def topology(channel: AbstractChannel) -> None:
    name = get_settings().queue
    await channel.declare_queue(name + ".dead", durable=True)
    await channel.declare_queue(
        name,
        durable=True,
        arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": name + ".dead"},
    )
    await channel.declare_queue(
        name + ".retry",
        durable=True,
        arguments={
            "x-message-ttl": 5000,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": name,
        },
    )


async def publish(channel: AbstractChannel, body: bytes, *, retry: int = 0) -> None:
    settings = get_settings()
    result = await channel.default_exchange.publish(
        aio_pika.Message(
            body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            headers={"retry": retry},
        ),
        routing_key=settings.queue + (".retry" if retry else ""),
        mandatory=True,
        timeout=settings.timeout,
    )
    if not isinstance(result, Basic.Ack):
        raise RuntimeError("Broker did not confirm publication")


async def publish_one(database: DatabaseHelper, channel: AbstractChannel) -> bool:
    async with database.get_db_session() as session, session.begin():
        row = await session.scalar(
            select(LearningOutboxModel)
            .where(
                LearningOutboxModel.delivered_at.is_(None),
                LearningOutboxModel.next_attempt_at <= datetime.now(UTC),
            )
            .order_by(LearningOutboxModel.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return False
        try:
            event = QuizSubmitted.model_validate(row.payload)
            await publish(channel, event.model_dump_json().encode())
        except Exception:
            row.failures += 1
            row.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=min(300, 2 ** min(row.failures, 8))
            )
            logger.warning("Outbox publication delayed for event %s", row.event_id)
        else:
            row.delivered_at = datetime.now(UTC)
        return True


async def consume(
    database: DatabaseHelper, channel: AbstractChannel, message: AbstractIncomingMessage
) -> None:
    try:
        if len(message.body) > 32768:
            raise ValueError("Oversized event")
        event = QuizSubmitted.model_validate_json(message.body)
        raw_retry = (message.headers or {}).get("retry", 0)
        if not isinstance(raw_retry, int) or raw_retry < 0:
            raise ValueError("Invalid retry count")
    except ValidationError, ValueError:
        await message.reject(requeue=False)
        return
    try:
        async with database.get_db_session() as session, session.begin():
            await LearningEventRepo(session).deliver(event)
    except Exception:
        if raw_retry >= get_settings().retries:
            await message.reject(requeue=False)
        else:
            # Confirm the delayed retry before acknowledging the original delivery.
            await publish(channel, message.body, retry=raw_retry + 1)
            await message.ack()
        logger.warning("Notification delivery failed for event %s", event.event_id)
        return
    # Duplicate deliveries are harmless: event_id is unique in the inbox.
    await message.ack()


async def run(mode: str) -> None:
    database = DatabaseHelper(db_settings())
    settings = get_settings()
    try:
        while True:
            try:
                connection = await aio_pika.connect_robust(
                    host=settings.host,
                    port=settings.port,
                    login=settings.username,
                    password=settings.password.get_secret_value(),
                    virtualhost=settings.virtual_host,
                    ssl=settings.tls,
                    timeout=settings.timeout,
                )
                async with connection:
                    channel = await connection.channel(
                        publisher_confirms=True, on_return_raises=True
                    )
                    await channel.set_qos(prefetch_count=10)
                    await topology(channel)
                    if mode == "publisher":
                        while True:
                            if not await publish_one(database, channel):
                                await asyncio.sleep(1)
                    else:
                        queue = await channel.get_queue(settings.queue)
                        async with queue.iterator() as messages:
                            async for message in messages:
                                await consume(database, channel, message)
            except Exception:
                logger.warning("Learning worker reconnecting after connection or delivery failure")
                await asyncio.sleep(5)
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("publisher", "consumer"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(args.mode))


if __name__ == "__main__":
    main()
