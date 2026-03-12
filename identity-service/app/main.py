import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.core.bootstrap import bootstrap_rbac
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.routers import auth_router, health_router, rbac_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise puis libere les ressources partagees du service."""
    configure_logging()
    try:
        with SessionLocal() as db:
            bootstrap_rbac(db)
    except SQLAlchemyError:
        logger.warning("RBAC bootstrap skipped. Run Alembic migrations first.")
    yield


app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(rbac_router)
