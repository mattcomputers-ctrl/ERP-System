"""Basic API tests for BatchFlow ERP."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    admin = User(
        username="testadmin", email="admin@test.com",
        hashed_password=hash_password("testpass"),
        is_superuser=True, is_active=True,
    )
    db.add(admin)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def get_auth_headers():
    response = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "testpass"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuth:
    def test_login_success(self):
        response = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "testpass"})
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    def test_login_failure(self):
        response = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "wrong"})
        assert response.status_code == 401

    def test_get_me(self):
        headers = get_auth_headers()
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testadmin"

    def test_refresh_token(self):
        login = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "testpass"})
        refresh = login.json()["refresh_token"]
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestInventory:
    def test_create_item(self):
        headers = get_auth_headers()
        response = client.post("/api/v1/inventory/items", headers=headers, json={
            "item_code": "TEST-001",
            "name": "Test Item",
            "item_type": "raw_material",
        })
        assert response.status_code == 201
        assert response.json()["item_code"] == "TEST-001"

    def test_list_items(self):
        headers = get_auth_headers()
        client.post("/api/v1/inventory/items", headers=headers, json={
            "item_code": "TEST-002", "name": "Test Item 2", "item_type": "raw_material",
        })
        response = client.get("/api/v1/inventory/items", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_create_warehouse(self):
        headers = get_auth_headers()
        response = client.post("/api/v1/inventory/warehouses", headers=headers, json={
            "code": "WH-01", "name": "Test Warehouse",
        })
        assert response.status_code == 201


class TestGLGroups:
    def test_create_gl_group(self):
        headers = get_auth_headers()
        response = client.post("/api/v1/gl-groups", headers=headers, json={
            "name": "Test GL Group",
            "description": "Test",
            "account_mappings": [
                {"account_type": "sales", "account_name": "Test Sales", "account_number": "4000"},
            ],
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Test GL Group"
        assert len(response.json()["account_mappings"]) == 1


class TestUsers:
    def test_create_user(self):
        headers = get_auth_headers()
        response = client.post("/api/v1/users", headers=headers, json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "password123",
            "full_name": "New User",
        })
        assert response.status_code == 201

    def test_list_users(self):
        headers = get_auth_headers()
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
