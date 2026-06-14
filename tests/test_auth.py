import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_auth.db"
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

# Create tables BEFORE building the TestClient
from app.models import user, task, token  # noqa
Base.metadata.create_all(bind=engine)

client = TestClient(app)

USER = {"email": "bhaskar@example.com", "username": "bhaskar", "password": "Secret123"}


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register():
    res = client.post("/auth/register", json=USER)
    assert res.status_code == 201
    assert res.json()["email"] == USER["email"]


def test_register_duplicate():
    client.post("/auth/register", json=USER)
    res = client.post("/auth/register", json=USER)
    assert res.status_code == 400


def test_login():
    client.post("/auth/register", json=USER)
    res = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password():
    client.post("/auth/register", json=USER)
    res = client.post("/auth/login", data={"username": USER["username"], "password": "wrong"})
    assert res.status_code == 401


def test_me():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    token = login.json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == USER["username"]


def test_refresh_token():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    refresh = login.json()["refresh_token"]
    res = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_logout():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    token = login.json()["access_token"]
    res = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204


# ── Users router coverage ──────────────────────────────────────────────────

def test_list_users_forbidden_for_non_admin():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    token = login.json()["access_token"]
    res = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_get_own_user_profile():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    data = login.json()
    token = data["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]
    res = client.get(f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == USER["username"]


def test_update_own_user():
    client.post("/auth/register", json=USER)
    login = client.post("/auth/login", data={"username": USER["username"], "password": USER["password"]})
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]
    res = client.patch(
        f"/users/{user_id}",
        json={"username": "bhaskar_updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "bhaskar_updated"


def test_invalid_token_rejected():
    res = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401
