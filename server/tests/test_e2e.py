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
    # Register or login test user
    httpx.post(f"{BASE}/auth/register", json={
        "username": "e2e_test_user", "email": "e2e@test.com",
        "password": "test123456", "display_name": "E2E Test User"
    })
    resp = httpx.post(f"{BASE}/auth/login", json={"username": "e2e_test_user", "password": "test123456"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_01_register_and_login(admin_token, user_token):
    assert admin_token
    assert user_token


def test_02_create_category(admin_token):
    resp = httpx.post(f"{BASE}/categories", json={"name": "E2E测试分类", "description": "端到端测试用"},
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_03_classify_document():
    resp = httpx.post(f"{CLASSIFIER}/classify", json={
        "content": "8D报告：客户投诉产品密封性不良，经分析发现O型圈尺寸超差，根本原因是模具磨损。"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "质量管理"
    assert data["confidence"] > 0.5


def test_04_classify_multiple_documents():
    docs = [
        {"id": "doc1", "content": "项目进度报告：本周完成需求评审，下周开始开发。"},
        {"id": "doc2", "content": "新员工入职培训：公司介绍、安全规范、IT系统使用指南。"},
        {"id": "doc3", "content": "财务预算报告：Q3研发支出超出预算15%，建议调整。"},
    ]
    resp = httpx.post(f"{CLASSIFIER}/classify/batch", json={"documents": docs})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3


def test_05_approval_workflow(admin_token, user_token):
    resp = httpx.post(f"{BASE}/approvals", json={"source_id": "source:e2e_test"},
        headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    approval_id = resp.json()["id"]

    resp = httpx.post(f"{BASE}/approvals/{approval_id}/approve", json={"comment": "E2E测试通过"},
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_06_permission_denied(user_token):
    resp = httpx.post(f"{BASE}/categories", json={"name": "should_fail"},
        headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


def test_07_category_tree(admin_token):
    resp = httpx.get(f"{BASE}/categories/tree",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    tree = resp.json()
    assert any(c["name"] == "E2E测试分类" for c in tree)


def test_08_audit_logs(admin_token):
    resp = httpx.get(f"{BASE}/audit",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_09_keywords_extraction():
    resp = httpx.post(f"{CLASSIFIER}/classify/keywords", json={
        "content": "密封圈在高温工况下出现老化裂纹，建议更换为氟橡胶材质，耐温可达250°C"
    })
    assert resp.status_code == 200
    assert len(resp.json()["keywords"]) > 0


def test_10_suggest_tree():
    docs = [
        {"title": "8D报告模板"}, {"title": "FMEA分析指南"},
        {"title": "项目周报"}, {"title": "员工手册"}, {"title": "财务报表"},
    ]
    resp = httpx.post(f"{CLASSIFIER}/classify/suggest-tree", json=docs)
    assert resp.status_code == 200
    assert "tree" in resp.json()
