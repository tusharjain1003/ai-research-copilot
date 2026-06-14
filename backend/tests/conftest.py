import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base, get_db, SessionLocal as OrigSessionLocal
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_research.db"


@pytest.fixture(autouse=True)
def _setup_db():
    """Override database to use test DB with isolated tables."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    import app.database.session as db_mod
    db_mod.engine = engine
    db_mod.SessionLocal = TestingSessionLocal

    import app.services.workflow as workflow_mod
    workflow_mod.SessionLocal = TestingSessionLocal

    import app.workflow.persistence as persistence_mod
    persistence_mod.SessionLocal = TestingSessionLocal

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    db_mod.SessionLocal = OrigSessionLocal
    from app.core.config import settings
    from sqlalchemy import create_engine as ce
    db_mod.engine = ce(settings.database_url, echo=settings.debug)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Provide a raw DB session for test setup/assertions."""
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()