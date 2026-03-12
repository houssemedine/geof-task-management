import json
import logging
import time
from datetime import UTC, datetime
from threading import Event, Thread
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import ProcessedEvent, TaskReadModel

logger = logging.getLogger(__name__)

_ROUTING_KEYS = (
    "task.created",
    "task.updated",
    "task.assigned",
    "task.status_changed",
    "task.deleted",
)


def _as_utc(value: datetime) -> datetime:
    """Normalise une date en UTC pour comparer les evenements."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: str | None, fallback: datetime) -> datetime:
    """Parse une date ISO, sinon retourne la valeur fallback."""
    if not value:
        return fallback

    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return fallback

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _task_payload_value(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    """Lit une valeur du payload avec une valeur par defaut."""
    if key in payload:
        return payload[key]
    return default


def _is_stale(task: TaskReadModel, occurred_at: datetime) -> bool:
    """Retourne True si l'evenement est plus ancien que l'etat projete."""
    return _as_utc(occurred_at) <= _as_utc(task.last_event_at)


def _apply_full_task_payload(
    task: TaskReadModel, payload: dict[str, Any], occurred_at: datetime
) -> None:
    """Applique toutes les donnees task sur la projection read-side."""
    task.title = str(_task_payload_value(payload, "title", task.title))
    task.description = _task_payload_value(payload, "description", task.description)
    task.status = str(_task_payload_value(payload, "status", task.status))
    task.priority = str(_task_payload_value(payload, "priority", task.priority))
    task.created_by = int(_task_payload_value(payload, "created_by", task.created_by))
    task.assigned_to = _task_payload_value(payload, "assigned_to", task.assigned_to)
    task.due_date = (
        _parse_datetime(payload.get("due_date"), occurred_at) if payload.get("due_date") else None
    )
    task.created_at = _parse_datetime(payload.get("created_at"), task.created_at)
    task.updated_at = _parse_datetime(payload.get("updated_at"), occurred_at)
    task.last_event_at = occurred_at


def _new_task_from_payload(payload: dict[str, Any], occurred_at: datetime) -> TaskReadModel:
    """Cree une nouvelle projection task depuis le payload evenement."""
    return TaskReadModel(
        task_id=int(payload["id"]),
        title=str(_task_payload_value(payload, "title", "")),
        description=_task_payload_value(payload, "description"),
        status=str(_task_payload_value(payload, "status", "open")),
        priority=str(_task_payload_value(payload, "priority", "medium")),
        created_by=int(_task_payload_value(payload, "created_by", 0)),
        assigned_to=_task_payload_value(payload, "assigned_to"),
        due_date=(
            _parse_datetime(payload.get("due_date"), occurred_at)
            if payload.get("due_date")
            else None
        ),
        created_at=_parse_datetime(payload.get("created_at"), occurred_at),
        updated_at=_parse_datetime(payload.get("updated_at"), occurred_at),
        last_event_at=occurred_at,
    )


def _apply_task_created(db: Session, payload: dict[str, Any], occurred_at: datetime) -> None:
    """Projette un evenement TaskCreated."""
    task_id = int(payload["id"])
    task = db.get(TaskReadModel, task_id)
    if task is not None and _is_stale(task, occurred_at):
        return

    if task is None:
        task = _new_task_from_payload(payload, occurred_at)
    else:
        _apply_full_task_payload(task, payload, occurred_at)

    db.add(task)


def _apply_task_updated(db: Session, payload: dict[str, Any], occurred_at: datetime) -> None:
    """Projette un evenement TaskUpdated."""
    task_id = int(payload["id"])
    task = db.get(TaskReadModel, task_id)
    if task is not None and _is_stale(task, occurred_at):
        return

    if task is None:
        task = _new_task_from_payload(payload, occurred_at)
    else:
        _apply_full_task_payload(task, payload, occurred_at)

    db.add(task)


def _apply_task_assigned(db: Session, payload: dict[str, Any], occurred_at: datetime) -> None:
    """Projette un evenement TaskAssigned."""
    task_id = int(payload["id"])
    task = db.get(TaskReadModel, task_id)
    if task is not None and _is_stale(task, occurred_at):
        return

    if task is None:
        task = _new_task_from_payload(payload, occurred_at)
    else:
        task.assigned_to = _task_payload_value(payload, "assigned_to", task.assigned_to)
        task.updated_at = _parse_datetime(payload.get("updated_at"), occurred_at)
        task.last_event_at = occurred_at

    db.add(task)


def _apply_task_status_changed(db: Session, payload: dict[str, Any], occurred_at: datetime) -> None:
    """Projette un evenement TaskStatusChanged."""
    task_id = int(payload["id"])
    task = db.get(TaskReadModel, task_id)
    if task is not None and _is_stale(task, occurred_at):
        return

    if task is None:
        task = _new_task_from_payload(payload, occurred_at)
    else:
        task.status = str(_task_payload_value(payload, "status", task.status))
        task.updated_at = _parse_datetime(payload.get("updated_at"), occurred_at)
        task.last_event_at = occurred_at

    db.add(task)


def _apply_task_deleted(db: Session, payload: dict[str, Any], occurred_at: datetime) -> None:
    """Projette un evenement TaskDeleted."""
    task_id = int(payload["id"])
    task = db.get(TaskReadModel, task_id)
    if task is None:
        return
    if _is_stale(task, occurred_at):
        return

    db.delete(task)


def process_task_event(envelope: dict[str, Any]) -> None:
    """Applique un evenement metier sur la projection read-model."""
    event_id = envelope.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Missing event_id")

    event_type = envelope.get("event_type")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload")

    event_type_name = str(event_type) if event_type is not None else "Unknown"
    occurred_at = _parse_datetime(envelope.get("occurred_at"), datetime.now(UTC))

    with SessionLocal() as db:
        # Idempotence: meme event_id deja traite => on ignore.
        if db.get(ProcessedEvent, event_id) is not None:
            return

        if event_type == "TaskCreated":
            _apply_task_created(db, payload, occurred_at)
        elif event_type == "TaskUpdated":
            _apply_task_updated(db, payload, occurred_at)
        elif event_type == "TaskAssigned":
            _apply_task_assigned(db, payload, occurred_at)
        elif event_type == "TaskStatusChanged":
            _apply_task_status_changed(db, payload, occurred_at)
        elif event_type == "TaskDeleted":
            _apply_task_deleted(db, payload, occurred_at)
        else:
            logger.debug("Ignoring unsupported event_type=%s", event_type)

        db.add(ProcessedEvent(event_id=event_id, event_type=event_type_name))
        db.commit()


def apply_task_event(envelope: dict[str, Any]) -> None:
    """Alias de compatibilite pour appliquer un evenement task."""
    process_task_event(envelope)


def _retry_count(properties: BasicProperties | None) -> int:
    """Retourne le nombre de retries deja appliques sur le message."""
    headers = properties.headers if properties is not None else {}
    headers = headers or {}
    raw = headers.get("x-retry-count", 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _handle_failed_message(
    channel: BlockingChannel,
    body: bytes,
    properties: BasicProperties | None,
    error: str,
) -> None:
    """Renvoie le message en retry ou en DLQ selon le compteur courant."""
    retry_count = _retry_count(properties)
    headers = dict(properties.headers) if properties is not None and properties.headers else {}
    headers["x-last-error"] = error[:500]

    if retry_count < settings.consumer_max_retries:
        headers["x-retry-count"] = retry_count + 1
        # Retry simple: republication dans la file principale.
        channel.basic_publish(
            exchange="",
            routing_key=settings.rabbitmq_queue,
            body=body,
            properties=BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers=headers,
            ),
        )
        logger.warning(
            "Message requeued for retry (%s/%s)", retry_count + 1, settings.consumer_max_retries
        )
        return

    headers["x-dlq-at"] = datetime.now(UTC).isoformat()
    # Trop d'echecs: direction DLQ pour inspection manuelle.
    channel.basic_publish(
        exchange="",
        routing_key=settings.rabbitmq_dlq_queue,
        body=body,
        properties=BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            headers=headers,
        ),
    )
    logger.error("Message moved to DLQ queue=%s after retries", settings.rabbitmq_dlq_queue)


def _on_message(
    channel: BlockingChannel,
    delivery_tag: int,
    properties: BasicProperties | None,
    body: bytes,
) -> None:
    """Traite un message RabbitMQ puis confirme (ack) ou reroute."""
    try:
        envelope = json.loads(body.decode("utf-8"))
        if not isinstance(envelope, dict):
            raise ValueError("Envelope must be an object")
        process_task_event(envelope)
    except Exception as exc:
        logger.exception("Failed to process incoming task event")
        try:
            _handle_failed_message(channel, body, properties, str(exc))
            channel.basic_ack(delivery_tag=delivery_tag)
            return
        except Exception:
            logger.exception("Failed while rerouting failed message; requeueing original")
            channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
            return

    channel.basic_ack(delivery_tag=delivery_tag)


def _consume_loop(stop_event: Event) -> None:
    """Boucle principale du consumer RabbitMQ avec reconnexion auto."""
    while not stop_event.is_set():
        connection = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
            channel = connection.channel()

            channel.exchange_declare(
                exchange=settings.rabbitmq_exchange,
                exchange_type="topic",
                durable=True,
            )
            channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
            channel.queue_declare(queue=settings.rabbitmq_dlq_queue, durable=True)
            # On relie toutes les cles d'evenement task sur la meme file de projection.
            for routing_key in _ROUTING_KEYS:
                channel.queue_bind(
                    exchange=settings.rabbitmq_exchange,
                    queue=settings.rabbitmq_queue,
                    routing_key=routing_key,
                )

            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(
                queue=settings.rabbitmq_queue,
                on_message_callback=lambda ch, method, properties, body: _on_message(
                    ch,
                    method.delivery_tag,
                    properties,
                    body,
                ),
            )

            while not stop_event.is_set():
                connection.process_data_events(time_limit=1)
        except Exception:
            logger.exception("RabbitMQ consumer connection failed; retrying")
            time.sleep(3)
        finally:
            if connection is not None and connection.is_open:
                connection.close()


def start_event_consumer(stop_event: Event) -> Thread | None:
    """Demarre le consumer RabbitMQ dans un thread dedie."""
    if not settings.enable_event_consumer:
        return None

    thread = Thread(
        target=_consume_loop, args=(stop_event,), daemon=True, name="query-event-consumer"
    )
    thread.start()
    return thread
