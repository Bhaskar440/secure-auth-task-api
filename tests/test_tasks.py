import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_tasks.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.main import app
app.dependency_overrides[get_db] = override_get_db

from app.models import user, task, token  # noqa
Base.metadata.create_all(bind=engine)

client = TestClient(app)

USER = {"email": "task_user@example.com", "username": "taskuser", "password": "Secret123"}


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_token():
    client.post("/auth/register", json=USER)
    res = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    return res.json()["access_token"]


@patch("app.routers.tasks.process_task_async")
def test_create_task(mock_celery):
    mock_celery.delay.return_value.id = "fake-celery-id"
    token = get_token()
    res = client.post(
        "/tasks/",
        json={"title": "Write unit tests", "description": "Cover all endpoints", "priority": "high"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["title"] == "Write unit tests"


@patch("app.routers.tasks.process_task_async")
def test_list_tasks(mock_celery):
    mock_celery.delay.return_value.id = "fake-celery-id"
    token = get_token()
    client.post("/tasks/", json={"title": "Task 1"}, headers={"Authorization": f"Bearer {token}"})
    client.post("/tasks/", json={"title": "Task 2"}, headers={"Authorization": f"Bearer {token}"})
    res = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()) == 2


@patch("app.routers.tasks.process_task_async")
def test_update_task(mock_celery):
    mock_celery.delay.return_value.id = "fake-celery-id"
    token = get_token()
    create = client.post("/tasks/", json={"title": "Old title"}, headers={"Authorization": f"Bearer {token}"})
    task_id = create.json()["id"]
    res = client.patch(
        f"/tasks/{task_id}",
        json={"title": "New title", "status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "New title"
    assert res.json()["status"] == "in_progress"


@patch("app.routers.tasks.process_task_async")
def test_delete_task(mock_celery):
    mock_celery.delay.return_value.id = "fake-celery-id"
    token = get_token()
    create = client.post("/tasks/", json={"title": "Delete me"}, headers={"Authorization": f"Bearer {token}"})
    task_id = create.json()["id"]
    res = client.delete(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204


@patch("app.routers.tasks.process_task_async")
def test_get_task_not_found(mock_celery):
    mock_celery.delay.return_value.id = "fake"
    token = get_token()
    res = client.get("/tasks/9999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


@patch("app.routers.tasks.process_task_async")
def test_task_priority_default(mock_celery):
    mock_celery.delay.return_value.id = "fake"
    token = get_token()
    res = client.post("/tasks/", json={"title": "Default prio"}, headers={"Authorization": f"Bearer {token}"})
    assert res.json()["priority"] == "medium"
    assert res.json()["status"] == "pending"
