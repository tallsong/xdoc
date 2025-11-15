from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from sqlmodel import create_engine as _create_engine

# Ensure tests run against an in-memory SQLite database to avoid requiring
# a running Postgres instance in CI/dev environments. We patch the app's
# core.db.engine before importing init_db.
import importlib
import app.core.db as _core_db
_core_db.engine = _create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
# Create tables for tests from SQLModel metadata
from sqlmodel import SQLModel
import app.models  # ensure models are imported and registered
SQLModel.metadata.create_all(_core_db.engine)

from app.core.db import engine, init_db
from app.main import app
from app.models import Item, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(Item)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
