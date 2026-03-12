import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:////tmp/gf_query_service_test.db"
os.environ["ENABLE_EVENT_CONSUMER"] = "false"
os.environ["CONSUMER_MAX_RETRIES"] = "2"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "identity-service"
os.environ["JWT_AUDIENCE"] = "gf-task-management"

from app.core.db import Base, engine


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Recree une base propre avant execution des tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
