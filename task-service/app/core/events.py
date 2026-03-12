import json
import logging
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import OutboxEvent, OutboxStatus

logger = logging.getLogger(__name__)

_EVENT_ROUTING_KEYS = {
    "TaskCreated": "task.created",
    "TaskUpdated": "task.updated",
    "TaskAssigned": "task.assigned",
    "TaskStatusChanged": "task.status_changed",
    "TaskDeleted": "task.deleted",
}


def stage_task_event(
    db: Session,
    event_type: str,
    payload: dict,
    *,
    aggregate_id: int | None = None,
    correlation_id: str | None = None,
) -> str:
    """Ajoute un evenement metier dans l'outbox transactionnelle."""
    routing_key = _EVENT_ROUTING_KEYS.get(event_type)
    if routing_key is None:
        raise ValueError(f"Unsupported event type: {event_type}")

    event_id = str(uuid4())
    event = OutboxEvent(
        event_id=event_id,
        aggregate_id=aggregate_id,
        event_type=event_type,
        routing_key=routing_key,
        event_version=1,
        correlation_id=correlation_id or event_id,
        payload=payload,
        occurred_at=datetime.now(UTC),
        status=OutboxStatus.PENDING,
        attempt_count=0,
        available_at=datetime.now(UTC),
    )
    db.add(event)
    return event_id


def _to_envelope(event: OutboxEvent) -> dict:
    """Convertit un evenement outbox en enveloppe JSON publiee."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "occurred_at": event.occurred_at.isoformat(),
        "producer": settings.service_name,
        "correlation_id": event.correlation_id,
        "payload": event.payload,
    }


def _mark_publish_failure(event: OutboxEvent, error: str) -> None:
    """Met a jour le statut d'un evenement apres un echec de publication."""
    event.attempt_count += 1
    event.last_error = error[:1000]
    if event.attempt_count >= settings.outbox_max_attempts:
        event.status = OutboxStatus.FAILED
        event.available_at = datetime.now(UTC)
        return

    backoff_seconds = min(2**event.attempt_count, 60)
    event.status = OutboxStatus.PENDING
    event.available_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)


def _publish_pending_events_once() -> int:
    """Publie un lot d'evenements outbox en attente."""
    with SessionLocal() as db:
        now = datetime.now(UTC)
        events = db.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxStatus.PENDING,
                OutboxEvent.available_at <= now,
                OutboxEvent.attempt_count < settings.outbox_max_attempts,
            )
            .order_by(OutboxEvent.available_at.asc(), OutboxEvent.id.asc())
            .limit(settings.outbox_batch_size)
        ).all()
        if not events:
            return 0

        connection = None
        channel: BlockingChannel | None = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
            channel = connection.channel()
            # L'exchange topic doit exister avant toute publication.
            channel.exchange_declare(
                exchange=settings.rabbitmq_exchange,
                exchange_type="topic",
                durable=True,
            )
        except Exception as exc:
            logger.exception("Could not open RabbitMQ connection for outbox publish")
            for event in events:
                _mark_publish_failure(event, str(exc))
                db.add(event)
            db.commit()
            if connection is not None and connection.is_open:
                connection.close()
            return 0

        # Publication evenement par evenement pour marquer chaque resultat proprement.
        for event in events:
            try:
                envelope = _to_envelope(event)
                assert channel is not None
                channel.basic_publish(
                    exchange=settings.rabbitmq_exchange,
                    routing_key=event.routing_key,
                    body=json.dumps(envelope).encode("utf-8"),
                    properties=BasicProperties(delivery_mode=2),
                )
            except Exception as exc:
                logger.exception("Failed to publish outbox event_id=%s", event.event_id)
                _mark_publish_failure(event, str(exc))
                db.add(event)
            else:
                event.status = OutboxStatus.PUBLISHED
                event.published_at = datetime.now(UTC)
                event.attempt_count += 1
                event.last_error = None
                db.add(event)

        db.commit()
        if connection is not None and connection.is_open:
            connection.close()
        return len(events)


def _publisher_loop(stop_event: Event) -> None:
    """Boucle de publication outbox avec attente et reprise automatique."""
    interval = max(1, settings.outbox_publish_interval_seconds)
    while not stop_event.is_set():
        try:
            published_count = _publish_pending_events_once()
            if published_count > 0:
                continue
        except Exception:
            logger.exception("Unexpected failure in outbox publisher loop")

        stop_event.wait(timeout=interval)


def start_outbox_publisher(stop_event: Event) -> Thread | None:
    """Demarre le thread de publication outbox si active."""
    if not settings.publish_events:
        return None

    thread = Thread(
        target=_publisher_loop, args=(stop_event,), daemon=True, name="task-outbox-publisher"
    )
    thread.start()
    return thread
