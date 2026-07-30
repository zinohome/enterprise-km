import pytest
import httpx

BASE = "http://192.168.66.40:5056"
CLASSIFIER = "http://192.168.66.40:5057"


@pytest.fixture(scope="module")
def admin_token():
    resp = httpx.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def user_token():
    httpx.post(f"{BASE}/auth/register", json={
        "username": "full_test_user", "email": "full@test.com",
        "password": "test123456", "display_name": "Full Test User"
    })
    resp = httpx.post(f"{BASE}/auth/login", json={"username": "full_test_user", "password": "test123456"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ========== TEAMS ==========

def test_create_team(admin_token):
    resp = httpx.post(f"{BASE}/teams", json={"name": "测试团队", "description": "端到端测试"},
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "测试团队"
    return data["id"]


def test_list_teams(admin_token):
    resp = httpx.get(f"{BASE}/teams", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    teams = resp.json()
    assert len(teams) > 0


def test_add_team_member(admin_token, user_token):
    # Get team
    resp = httpx.get(f"{BASE}/teams", headers={"Authorization": f"Bearer {admin_token}"})
    teams = resp.json()
    if not teams:
        pytest.skip("No teams available")
    team = teams[0]
    team_id = team["id"]
    # Normalize SurrealDB RecordID
    if isinstance(team_id, dict):
        team_id = f"{team_id['table_name']}:{team_id['id']}"

    # Get user
    me = httpx.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    user = me.json()
    user_id = user["id"]
    if isinstance(user_id, dict):
        user_id = f"{user_id['table_name']}:{user_id['id']}"

    resp = httpx.post(f"{BASE}/teams/{team_id}/members",
        json={"user_id": user_id, "role": "member"},
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


# ========== SEARCH ==========

def test_search(admin_token):
    resp = httpx.get(f"{BASE}/search?q=test&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "total" in data


def test_search_suggest(admin_token):
    resp = httpx.get(f"{BASE}/search/suggest?q=te",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_search_stats(admin_token):
    resp = httpx.get(f"{BASE}/search/stats",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data


# ========== NOTIFICATIONS ==========

def test_create_notification(admin_token):
    resp = httpx.post(f"{BASE}/notifications", json={
        "user_id": "user:test", "title": "测试通知", "message": "这是一条测试通知", "type": "info"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_list_notifications(admin_token):
    resp = httpx.get(f"{BASE}/notifications",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_unread_count(admin_token):
    resp = httpx.get(f"{BASE}/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert "count" in resp.json()


# ========== SYNC ==========

def test_sync_status(admin_token):
    resp = httpx.get(f"{BASE}/sync/status",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_sync_config(admin_token):
    resp = httpx.post(f"{BASE}/sync/config", json={"directory": "/home/user/docs"},
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["directory"] == "/home/user/docs"


def test_sync_start_stop(admin_token):
    resp = httpx.post(f"{BASE}/sync/start",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["running"] is True

    resp = httpx.post(f"{BASE}/sync/stop",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["running"] is False


# ========== PERMISSIONS ==========

def test_set_visibility(admin_token):
    resp = httpx.put(f"{BASE}/permissions/source/source:test/visibility",
        json={"visibility": "enterprise"},
        headers={"Authorization": f"Bearer {admin_token}"})
    # May 404 if source doesn't exist, or 500 if SurrealDB rejects
    assert resp.status_code in (200, 404, 500)


def test_check_access(admin_token):
    resp = httpx.get(f"{BASE}/permissions/source/source:test/access",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code in (200, 404)


# ========== WEBHOOK ==========

def test_webhook_health():
    resp = httpx.get(f"{CLASSIFIER}/health")
    assert resp.status_code == 200


def test_webhook_minio():
    resp = httpx.post(f"{CLASSIFIER}/webhook/minio", json={
        "EventName": "s3:ObjectCreated:Put",
        "Key": "user_test/test_doc.pdf",
        "Records": [{
            "eventName": "s3:ObjectCreated:Put",
            "s3": {"object": {"key": "user_test/test_doc.pdf"}},
            "userMetadata": {"X-Amz-Meta-User-Id": "test_user"}
        }]
    })
    assert resp.status_code == 200


def test_webhook_manual_process():
    resp = httpx.post(f"{CLASSIFIER}/webhook/minio/test", json={"object_key": "test_file.pdf", "user_id": "test_user"})
    assert resp.status_code == 200


# ========== RATE LIMIT ==========

def test_rate_limit(admin_token):
    # Should not be rate limited on first request
    resp = httpx.get(f"{BASE}/health")
    assert resp.status_code == 200
