import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.database.session import Base, get_db
from backend.app.main import app

# ---------------------------------------------------------------------------
# Per-function in-memory SQLite engine shared via StaticPool
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# TestClient fixture that:
#   1. Overrides get_db with the test session
#   2. Patches the lifespan engine so create_all targets the test engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(db_session, db_engine):
    import backend.app.database.session as db_module

    # Point the module-level engine at our test engine for the duration of the test
    original_engine = db_module.engine
    db_module.engine = db_engine

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Use lifespan=False to skip the startup handler that would call create_all
    # on the (now-patched) engine — tables already exist from db_engine fixture.
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    db_module.engine = original_engine
