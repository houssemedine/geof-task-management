from contextlib import asynccontextmanager
from threading import Event

from fastapi import FastAPI

from app.core.config import settings
from app.core.events import start_event_consumer
from app.core.logging import configure_logging
from app.routers import analytics_router, health_router, tasks_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise puis libere les ressources partagees du service."""
    configure_logging()

    stop_event = Event()
    consumer_thread = start_event_consumer(stop_event)
    try:
        yield
    finally:
        stop_event.set()
        if consumer_thread is not None:
            consumer_thread.join(timeout=5)


app = FastAPI(title=settings.service_name, version=settings.service_version, lifespan=lifespan)

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(analytics_router)
