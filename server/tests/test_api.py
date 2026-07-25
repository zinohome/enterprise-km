import pytest
import httpx

BASE = "http://192.168.66.40:5056"


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE)


@pytest.fixture
def token(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_me(client, token):
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code in (401, 403)


def test_users_list(client, token):
    resp = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_categories(client, token):
    resp = client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_categories_tree(client, token):
    resp = client.get("/categories/tree", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_approvals(client, token):
    resp = client.get("/approvals", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_classifier_health():
    resp = httpx.get("http://192.168.66.40:5057/health")
    assert resp.status_code == 200


def test_classify():
    resp = httpx.post(
        "http://192.168.66.40:5057/classify",
        json={"content": "密封圈高温老化，建议更换氟橡胶材质"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data
    assert "confidence" in data
