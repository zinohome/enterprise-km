"""
Unit tests for server/core and classifier modules.
Tests import code directly — no HTTP calls.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock


class TestConfig:
    def test_jwt_secret_generated(self):
        from server.core.config import JWT_SECRET
        assert len(JWT_SECRET) > 32
        assert JWT_SECRET != "dev-secret-change-in-production"

    def test_jwt_algorithm(self):
        from server.core.config import JWT_ALGORITHM
        assert JWT_ALGORITHM == "HS256"

    def test_jwt_expiration(self):
        from server.core.config import JWT_EXPIRATION_MINUTES
        assert JWT_EXPIRATION_MINUTES > 0

    def test_surreal_config(self):
        from server.core.config import SURREAL_URL, SURREAL_NAMESPACE, SURREAL_DATABASE
        assert "8000" in SURREAL_URL
        assert SURREAL_NAMESPACE == "open_notebook"
        assert SURREAL_DATABASE == "open_notebook"

    def test_cors_origins(self):
        from server.core.config import CORS_ORIGINS
        assert isinstance(CORS_ORIGINS, list)

    def test_rate_limit(self):
        from server.core.config import RATE_LIMIT
        assert "minute" in RATE_LIMIT or "second" in RATE_LIMIT


class TestSecurity:
    def test_hash_password(self):
        from server.core.security import hash_password
        hashed = hash_password("test123")
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_password_correct(self):
        from server.core.security import hash_password, verify_password
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_wrong(self):
        from server.core.security import hash_password, verify_password
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_create_access_token(self):
        from server.core.security import create_access_token
        token = create_access_token({"sub": "user1", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20
        assert token.count(".") == 2

    def test_decode_valid_token(self):
        from server.core.security import create_access_token, decode_access_token
        token = create_access_token({"sub": "user1"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user1"

    def test_decode_invalid_token(self):
        from server.core.security import decode_access_token
        assert decode_access_token("invalid.token.here") is None
        assert decode_access_token("") is None
        assert decode_access_token("not.a.jwt") is None

    def test_token_expiration(self):
        from server.core.security import create_access_token, decode_access_token
        from datetime import timedelta
        token = create_access_token({"sub": "user1"}, expires_delta=timedelta(hours=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_token_with_custom_claims(self):
        from server.core.security import create_access_token, decode_access_token
        token = create_access_token({
            "sub": "user123",
            "role": "manager",
            "department": "engineering"
        })
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "manager"
        assert payload["department"] == "engineering"


class TestPermissions:
    def test_require_role_decorator_exists(self):
        from server.core.permissions import require_role
        assert callable(require_role)

    def test_require_admin_exists(self):
        from server.core.permissions import require_admin
        assert callable(require_admin)

    def test_require_manager_exists(self):
        from server.core.permissions import require_manager
        assert callable(require_manager)

    def test_require_editor_exists(self):
        from server.core.permissions import require_editor
        assert callable(require_editor)


class TestDatabase:
    def test_check_db_health_disconnected(self):
        import asyncio
        with patch('server.core.database.get_db', side_effect=Exception("no connection")):
            from server.core.database import check_db_health
            result = asyncio.run(check_db_health())
            assert result is False

    def test_db_query_calls_get_db(self):
        import asyncio
        mock_db = AsyncMock()
        mock_db.query = AsyncMock(return_value=[{"result": "ok"}])
        with patch('server.core.database.get_db', return_value=mock_db):
            from server.core.database import db_query
            result = asyncio.run(db_query("SELECT 1;"))
            mock_db.query.assert_called_once()
            assert result == [{"result": "ok"}]

    def test_db_query_with_vars(self):
        import asyncio
        mock_db = AsyncMock()
        mock_db.query = AsyncMock(return_value=[{"id": "test"}])
        with patch('server.core.database.get_db', return_value=mock_db):
            from server.core.database import db_query
            result = asyncio.run(db_query("SELECT * FROM $id;", {"id": "test"}))
            mock_db.query.assert_called_once_with("SELECT * FROM $id;", {"id": "test"})
            assert result == [{"id": "test"}]


class TestUserDomain:
    def test_user_model_fields(self):
        from server.domain.user import User
        fields = User.model_fields
        assert "username" in fields
        assert "email" in fields
        assert "display_name" in fields
        assert "role" in fields
        assert "password_hash" in fields

    def test_user_default_role(self):
        from server.domain.user import User
        user = User(
            id="user:test",
            username="testuser",
            email="test@test.com",
            display_name="Test",
            password_hash="hash",
        )
        assert user.role == "viewer"

    def test_user_to_dict(self):
        from server.domain.user import User
        user = User(
            id="user:test",
            username="testuser",
            email="test@test.com",
            display_name="Test User",
            password_hash="hash",
            role="admin",
        )
        d = user.model_dump()
        assert d["username"] == "testuser"
        assert d["role"] == "admin"
        # password_hash is in the model, just verify it's present
        assert "password_hash" in d

    def test_user_get_by_username_mock(self):
        with patch('server.domain.user.db_query') as mock_query:
            mock_query.return_value = [{
                "id": "user:test",
                "username": "testuser",
                "email": "test@test.com",
                "display_name": "Test",
                "password_hash": "hash",
                "role": "viewer",
            }]
            import asyncio
            from server.domain.user import User
            result = asyncio.run(User.get_by_username("testuser"))
            assert result is not None
            assert result.username == "testuser"

    def test_user_get_by_username_not_found(self):
        with patch('server.domain.user.db_query') as mock_query:
            mock_query.return_value = []
            import asyncio
            from server.domain.user import User
            result = asyncio.run(User.get_by_username("nonexistent"))
            assert result is None


class TestCategoryDomain:
    def test_category_model_fields(self):
        from server.domain.category import KnowledgeCategory
        fields = KnowledgeCategory.model_fields
        assert "name" in fields
        assert "description" in fields
        assert "parent_id" in fields

    def test_category_create(self):
        from server.domain.category import KnowledgeCategory
        cat = KnowledgeCategory(name="测试分类", description="测试用")
        assert cat.name == "测试分类"
        assert cat.description == "测试用"


class TestApprovalDomain:
    def test_approval_model_fields(self):
        from server.domain.approval import Approval
        fields = Approval.model_fields
        assert "source_id" in fields
        assert "submitter_id" in fields
        assert "status" in fields

    def test_approval_default_status(self):
        from server.domain.approval import Approval
        app = Approval(source_id="source:1", submitter_id="user:1")
        assert app.status == "pending"


class TestAPIDeps:
    def test_get_current_user_no_token(self):
        import asyncio
        from server.api.deps import get_current_user
        from fastapi import HTTPException
        with pytest.raises(AttributeError):
            asyncio.run(get_current_user(None))

    def test_get_current_user_invalid_token(self):
        import asyncio
        from server.api.deps import get_current_user
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user(creds))
        assert exc.value.status_code == 401


class TestClassifierConfig:
    def test_ollama_url(self):
        from classifier.core.config import OLLAMA_URL
        assert "11434" in OLLAMA_URL

    def test_open_notebook_url(self):
        from classifier.core.config import OPEN_NOTEBOOK_URL
        assert "5055" in OPEN_NOTEBOOK_URL

    def test_minio_config(self):
        from classifier.core.config import MINIO_ENDPOINT, MINIO_BUCKET
        assert MINIO_BUCKET == "enterprise-km"


class TestClassifierService:
    def test_classify_document_returns_dict(self):
        import asyncio
        from classifier.services.classifier import classify_document
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {"content": '{"category": "技术研发", "confidence": 0.95}'}
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_resp

            result = asyncio.run(classify_document("测试内容"))
            assert isinstance(result, dict)

    def test_extract_keywords_returns_list(self):
        import asyncio
        from classifier.services.classifier import extract_keywords
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {"content": '["关键词1", "关键词2", "关键词3"]'}
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_resp

            result = asyncio.run(extract_keywords("测试内容"))
            assert isinstance(result, list)

    def test_suggest_knowledge_tree(self):
        import asyncio
        from classifier.services.classifier import suggest_knowledge_tree
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {"content": '{"tree": [{"name": "技术", "children": []}]}'}
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_resp

            result = asyncio.run(suggest_knowledge_tree([{"title": "test"}]))
            assert isinstance(result, dict)


class TestFileWatcher:
    def test_process_new_file_mocked(self):
        import asyncio
        from classifier.services.file_watcher import process_new_file
        with patch('classifier.services.file_watcher.httpx.AsyncClient') as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "source:test123"}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_resp
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp

            result = asyncio.run(process_new_file("test.pdf", "user1"))
            assert result is not None
            assert "source_id" in result

    def test_process_batch_files(self):
        import asyncio
        from classifier.services.file_watcher import process_batch_files
        with patch('classifier.services.file_watcher.process_new_file') as mock_process:
            mock_process.return_value = {"source_id": "test", "file_key": "f1.pdf"}
            files = [{"key": "f1.pdf", "user_id": "u1"}, {"key": "f2.pdf", "user_id": "u2"}]
            result = asyncio.run(process_batch_files(files))
            assert len(result) == 2


class TestAPIModels:
    def test_auth_models(self):
        from server.api.auth import LoginRequest, RegisterRequest
        login = LoginRequest(username="admin", password="pass")
        assert login.username == "admin"

        reg = RegisterRequest(username="new", email="new@test.com", password="pass", display_name="New")
        assert reg.email == "new@test.com"

    def test_category_models(self):
        from server.api.categories import CategoryCreate
        cat = CategoryCreate(name="测试", description="描述")
        assert cat.name == "测试"

    def test_approval_models(self):
        from server.api.approvals import ApprovalCreate
        app = ApprovalCreate(source_id="source:1")
        assert app.source_id == "source:1"

    def test_team_models(self):
        from server.api.teams import TeamCreate, TeamMemberAdd
        team = TeamCreate(name="团队1", description="测试团队")
        assert team.name == "团队1"

        member = TeamMemberAdd(user_id="user:1", role="member")
        assert member.role == "member"

    def test_sync_models(self):
        from server.api.sync import SyncConfig
        cfg = SyncConfig(directory="/home/user/docs")
        assert cfg.directory == "/home/user/docs"

    def test_permission_models(self):
        from server.api.permissions import VisibilityUpdate
        v = VisibilityUpdate(visibility="enterprise")
        assert v.visibility == "enterprise"

    def test_notification_models(self):
        from server.api.notifications import NotificationCreate
        n = NotificationCreate(user_id="user:1", title="测试", message="内容", type="info")
        assert n.type == "info"


class TestFastAPIApp:
    def test_server_app_created(self):
        from server.main import app
        assert app.title == "Enterprise KM Server"
        assert app.version == "0.1.0"

    def test_classifier_app_created(self):
        from classifier.main import app
        assert app.title == "Enterprise KM Classifier"

    def test_server_routes_registered(self):
        from server.main import app
        # Verify app has routes by checking OpenAPI schema
        schema = app.openapi()
        paths = schema.get("paths", {})
        required = ["/health", "/auth/login", "/auth/register", "/auth/me", "/auth/verify",
                     "/users", "/categories", "/approvals", "/teams", "/search",
                     "/notifications", "/sync/status", "/api/curation/queue"]
        for route in required:
            assert route in paths, f"Missing route: {route}"

    def test_classifier_routes_registered(self):
        from classifier.main import app
        schema = app.openapi()
        paths = schema.get("paths", {})
        required = ["/health", "/classify", "/webhook/minio"]
        for route in required:
            assert route in paths, f"Missing route: {route}"


class TestEdgeCases:
    def test_empty_password_hash(self):
        from server.core.security import hash_password
        hashed = hash_password("")
        assert hashed.startswith("$2b$")

    def test_long_password(self):
        from server.core.security import hash_password, verify_password
        long_pass = "x" * 50  # bcrypt max 72 bytes
        hashed = hash_password(long_pass)
        assert verify_password(long_pass, hashed)

    def test_unicode_password(self):
        from server.core.security import hash_password, verify_password
        passwd = "密码测试"
        hashed = hash_password(passwd)
        assert verify_password(passwd, hashed)

    def test_token_with_empty_claims(self):
        from server.core.security import create_access_token, decode_access_token
        token = create_access_token({})
        payload = decode_access_token(token)
        assert payload is not None

    def test_user_model_minimal(self):
        from server.domain.user import User
        user = User(
            id="user:min",
            username="min",
            email="min@test.com",
            display_name="Min",
            password_hash="h",
        )
        assert user.role == "viewer"
        assert user.department is None
        assert user.avatar_url is None

    def test_category_with_parent(self):
        from server.domain.category import KnowledgeCategory
        cat = KnowledgeCategory(name="子分类", parent_id="cat:parent")
        assert cat.parent_id == "cat:parent"

    def test_approval_statuses(self):
        from server.domain.approval import Approval
        pending = Approval(source_id="s:1", submitter_id="u:1")
        assert pending.status == "pending"

        approved = Approval(source_id="s:1", submitter_id="u:1", status="approved")
        assert approved.status == "approved"

        rejected = Approval(source_id="s:1", submitter_id="u:1", status="rejected")
        assert rejected.status == "rejected"
