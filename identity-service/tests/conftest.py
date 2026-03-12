import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:////tmp/gf_identity_service_test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ISSUER"] = "identity-service"
os.environ["JWT_AUDIENCE"] = "gf-task-management"
os.environ["JWT_ACCESS_TOKEN_EXPIRES_SECONDS"] = "900"

from app.core.bootstrap import bootstrap_rbac
from app.core.db import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Recree une base propre avant execution des tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_rbac(db)
    yield
