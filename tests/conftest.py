import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_shared.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # import all models so they register with Base
    from app.models import user, task, token  # noqa
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db] = override_get_db
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)
