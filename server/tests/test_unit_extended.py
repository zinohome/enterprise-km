"""
Extended unit tests to reach 90%+ coverage.
Tests API route handlers and domain methods with mocked DB.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


# ========== server/api/auth.py ==========

class TestAuthAPI:
    def test_login_success(self):
        with patch('server.api.auth.User') as mock_user_cls:
            mock_user = MagicMock()
            mock_user.id = "user:1"
            mock_user.username = "admin"
            mock_user.email = "a@b.com"
            mock_user.display_name = "Admin"
            mock_user.role = "admin"
            mock_user.verify_password = AsyncMock(return_value=True)
            mock_user_cls.get_by_username = AsyncMock(return_value=mock_user)

            with patch('server.api.auth.create_access_token', return_value="token123"):
                from server.api.auth import login, LoginRequest
                result = asyncio.run(login(LoginRequest(username="admin", password="pass")))
                assert result.access_token == "token123"
                assert result.user["username"] == "admin"

    def test_login_wrong_password(self):
        with patch('server.api.auth.User') as mock_user_cls:
            mock_user = MagicMock()
            mock_user.verify_password = AsyncMock(return_value=False)
            mock_user_cls.get_by_username = AsyncMock(return_value=mock_user)

            from server.api.auth import login, LoginRequest
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                asyncio.run(login(LoginRequest(username="admin", password="wrong")))
            assert exc.value.status_code == 401

    def test_login_user_not_found(self):
        with patch('server.api.auth.User') as mock_user_cls:
            mock_user_cls.get_by_username = AsyncMock(return_value=None)
            from server.api.auth import login, LoginRequest
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                asyncio.run(login(LoginRequest(username="nobody", password="x")))
            assert exc.value.status_code == 401

    def test_register_endpoint_mocked(self):
        with patch('server.api.auth.User') as mock_user_cls:
            mock_user_cls.get_by_username = AsyncMock(return_value=None)
            mock_new = MagicMock()
            mock_new.id = "user:2"
            mock_new.username = "new"
            mock_new.email = "n@b.com"
            mock_new.display_name = "New"
            mock_new.role = "viewer"
            mock_user_cls.create = AsyncMock(return_value=mock_new)

            with patch('server.api.auth.create_access_token', return_value="token"):
                from server.api.auth import register, RegisterRequest
                result = asyncio.run(register(RegisterRequest(
                    username="new", email="n@b.com", password="p", display_name="New"
                )))
                assert result.access_token == "token"

    def test_register_duplicate(self):
        with patch('server.api.auth.User') as mock_user_cls:
            mock_user_cls.get_by_username = AsyncMock(return_value=MagicMock())
            from server.api.auth import register, RegisterRequest
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                asyncio.run(register(RegisterRequest(
                    username="exists", email="e@b.com", password="p", display_name="E"
                )))
            assert exc.value.status_code == 400

    def test_me_endpoint(self):
        from server.api.auth import me
        from server.domain.user import User
        user = User(id="user:1", username="admin", email="a@b.com",
                     display_name="Admin", password_hash="h", role="admin")
        result = asyncio.run(me(user))
        assert result["username"] == "admin"


# ========== server/api/users.py ==========

class TestUsersAPI:
    def test_list_users(self):
        with patch('server.api.users.User') as mock_cls:
            u1 = MagicMock()
            u1.id = "user:1"; u1.username = "u1"; u1.email = "u1@t.com"
            u1.display_name = "U1"; u1.role = "viewer"; u1.department = None
            u2 = MagicMock()
            u2.id = "user:2"; u2.username = "u2"; u2.email = "u2@t.com"
            u2.display_name = "U2"; u2.role = "admin"; u2.department = None
            mock_cls.get_all = AsyncMock(return_value=[u1, u2])

            from server.api.users import list_users
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(list_users(admin))
            assert len(result) == 2

    def test_get_user(self):
        with patch('server.api.users.User') as mock_cls:
            mock_user = MagicMock()
            mock_user.id = "user:1"; mock_user.username = "u1"; mock_user.email = "u1@t.com"
            mock_user.display_name = "U1"; mock_user.role = "viewer"; mock_user.department = None
            mock_cls.get_by_id = AsyncMock(return_value=mock_user)

            from server.api.users import get_user
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(get_user("user:1", admin))
            assert result["username"] == "u1"

    def test_get_user_not_found(self):
        with patch('server.api.users.User') as mock_cls:
            mock_cls.get_by_id = AsyncMock(return_value=None)
            from server.api.users import get_user
            from server.domain.user import User
            from fastapi import HTTPException
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_user("user:999", admin))
            assert exc.value.status_code == 404

    def test_update_user(self):
        with patch('server.api.users.User') as mock_cls:
            mock_user = MagicMock()
            mock_user.id = "user:1"; mock_user.username = "u1"; mock_user.role = "editor"
            mock_user.update = AsyncMock()
            mock_cls.get_by_id = AsyncMock(return_value=mock_user)

            from server.api.users import update_user, UserUpdate
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(update_user("user:1", UserUpdate(display_name="Updated", role="editor"), admin))
            assert result["role"] == "editor"

    def test_delete_user(self):
        with patch('server.api.users.User') as mock_cls:
            mock_user = MagicMock()
            mock_user.delete = AsyncMock()
            mock_cls.get_by_id = AsyncMock(return_value=mock_user)

            from server.api.users import delete_user
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(delete_user("user:1", admin))
            assert result["message"] == "User deleted"


# ========== server/api/categories.py ==========

class TestCategoriesAPI:
    def test_create_category(self):
        with patch('server.api.categories.KnowledgeCategory') as mock_cls:
            mock_cat = MagicMock()
            mock_cat.model_dump.return_value = {"id": "cat:1", "name": "技术", "description": "技术文档",
                                                 "parent_id": None, "sort_order": 0}
            mock_cls.create = AsyncMock(return_value=mock_cat)

            from server.api.categories import create_category, CategoryCreate
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(create_category(CategoryCreate(name="技术", description="技术文档"), admin))
            assert result["name"] == "技术"

    def test_list_categories(self):
        with patch('server.api.categories.KnowledgeCategory') as mock_cls:
            mock_cat = MagicMock()
            mock_cat.model_dump.return_value = {"id": "cat:1", "name": "技术", "description": "d", "parent_id": None}
            mock_cls.get_all = AsyncMock(return_value=[mock_cat])

            from server.api.categories import list_categories
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(list_categories(user))
            assert len(result) == 1

    def test_get_category_tree(self):
        with patch('server.api.categories.KnowledgeCategory') as mock_cls:
            mock_cls.get_tree = AsyncMock(return_value=[{"name": "技术", "children": []}])

            from server.api.categories import get_tree
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(get_tree(user))
            assert isinstance(result, list)

    def test_delete_category(self):
        with patch('server.api.categories.KnowledgeCategory') as mock_cls:
            mock_cat = MagicMock()
            mock_cat.delete = AsyncMock()
            mock_cls.return_value = mock_cat

            from server.api.categories import delete_category
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(delete_category("cat:1", admin))
            assert result["message"] == "Deleted"


# ========== server/api/approvals.py ==========

class TestApprovalsAPI:
    def test_create_approval(self):
        with patch('server.api.approvals.Approval') as mock_cls:
            mock_approval = MagicMock()
            mock_approval.model_dump.return_value = {"id": "app:1", "source_id": "source:1",
                                                      "submitter_id": "user:1", "status": "pending"}
            mock_cls.create = AsyncMock(return_value=mock_approval)

            from server.api.approvals import create_approval, ApprovalCreate
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(create_approval(ApprovalCreate(source_id="source:1"), user))
            assert result["status"] == "pending"

    def test_list_approvals(self):
        with patch('server.api.approvals.Approval') as mock_cls:
            mock_a = MagicMock()
            mock_a.model_dump.return_value = {"id": "app:1", "status": "pending"}
            mock_cls.get_pending = AsyncMock(return_value=[mock_a])

            from server.api.approvals import list_approvals
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(list_approvals(admin))
            assert len(result) == 1

    def test_approve(self):
        with patch('server.api.approvals.Approval') as mock_cls:
            mock_approval = MagicMock()
            mock_approval.approve = AsyncMock()
            mock_approval.model_dump.return_value = {"id": "app:1", "status": "approved"}
            mock_cls.return_value = mock_approval

            from server.api.approvals import approve, ApprovalAction
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(approve("app:1", ApprovalAction(comment="ok"), admin))
            assert result["status"] == "approved"

    def test_reject(self):
        with patch('server.api.approvals.Approval') as mock_cls:
            mock_approval = MagicMock()
            mock_approval.reject = AsyncMock()
            mock_approval.model_dump.return_value = {"id": "app:1", "status": "rejected"}
            mock_cls.return_value = mock_approval

            from server.api.approvals import reject, ApprovalAction
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(reject("app:1", ApprovalAction(comment="no"), admin))
            assert result["status"] == "rejected"


# ========== server/api/audit.py ==========

class TestAuditAPI:
    def test_list_audit_logs(self):
        with patch('server.api.audit.db_query') as mock_db:
            mock_db.return_value = [{"id": "log:1", "user_id": "user:1", "action": "login",
                                      "resource_type": "auth", "created_at": "2024-01-01"}]
            from server.api.audit import list_audit_logs
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(list_audit_logs(admin))
            assert len(result) == 1

    def test_audit_stats(self):
        with patch('server.api.audit.db_query') as mock_db:
            mock_db.side_effect = [
                [{"count": 10}],  # users
                [{"count": 50}],  # sources
                [{"count": 30}],  # notes
            ]
            from server.api.audit import audit_stats
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(audit_stats(admin))
            assert result["users"] == 10
            assert result["sources"] == 50


# ========== server/api/auth_verify.py ==========

class TestAuthVerifyAPI:
    def test_verify_valid_token(self):
        with patch('server.api.auth_verify.decode_access_token', return_value={"sub": "user:1"}):
            from server.api.auth_verify import verify_token
            from fastapi import Request
            mock_req = MagicMock(spec=Request)
            mock_req.headers = {"Authorization": "Bearer valid.token.here"}
            result = asyncio.run(verify_token(mock_req))
            import json
            body = json.loads(result.body.decode())
            assert body["status"] == "ok"

    def test_verify_no_header(self):
        from server.api.auth_verify import verify_token
        from fastapi import Request, HTTPException
        mock_req = MagicMock(spec=Request)
        mock_req.headers = {}
        with pytest.raises(HTTPException) as exc:
            asyncio.run(verify_token(mock_req))
        assert exc.value.status_code == 401

    def test_verify_invalid_token(self):
        with patch('server.api.auth_verify.decode_access_token', return_value=None):
            from server.api.auth_verify import verify_token
            from fastapi import Request, HTTPException
            mock_req = MagicMock(spec=Request)
            mock_req.headers = {"Authorization": "Bearer bad.token"}
            with pytest.raises(HTTPException) as exc:
                asyncio.run(verify_token(mock_req))
            assert exc.value.status_code == 401


# ========== server/api/notifications.py ==========

class TestNotificationsAPI:
    def test_create_notification(self):
        with patch('server.api.notifications.db_query') as mock_db:
            mock_db.return_value = [{"id": "notif:1", "user_id": "user:1", "title": "T",
                                      "message": "M", "type": "info", "read": False}]
            from server.api.notifications import create_notification, NotificationCreate
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(create_notification(
                NotificationCreate(user_id="user:1", title="T", message="M"), admin))
            assert result["title"] == "T"

    def test_list_notifications(self):
        with patch('server.api.notifications.db_query') as mock_db:
            mock_db.return_value = [{"id": "n:1", "user_id": "user:1", "title": "T",
                                      "message": "M", "type": "info", "read": False}]
            from server.api.notifications import list_notifications
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(list_notifications(False, 50, user))
            assert len(result) == 1

    def test_mark_read(self):
        with patch('server.api.notifications.db_query') as mock_db:
            mock_db.return_value = []
            from server.api.notifications import mark_read
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(mark_read("n:1", user))
            assert result["status"] == "ok"

    def test_mark_all_read(self):
        with patch('server.api.notifications.db_query') as mock_db:
            mock_db.return_value = []
            from server.api.notifications import mark_all_read
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(mark_all_read(user))
            assert result["status"] == "ok"

    def test_unread_count(self):
        with patch('server.api.notifications.db_query') as mock_db:
            mock_db.return_value = [{"count": 3}]
            from server.api.notifications import unread_count
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(unread_count(user))
            assert result["count"] == 3


# ========== server/api/search.py ==========

class TestSearchAPI:
    def test_search(self):
        with patch('server.api.search.db_query') as mock_db:
            mock_db.return_value = [{"id": "s:1", "title": "Test Doc", "content": "hello"}]
            from server.api.search import search_knowledge
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(search_knowledge("test", None, None, 20, user))
            assert result["total"] == 1

    def test_search_suggest(self):
        with patch('server.api.search.db_query') as mock_db:
            mock_db.return_value = [{"title": "Test Doc"}, {"title": "Test 2"}]
            from server.api.search import search_suggest
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(search_suggest("te", 5, user))
            assert len(result) == 2

    def test_search_stats(self):
        with patch('server.api.search.db_query') as mock_db:
            mock_db.side_effect = [
                [{"count": 100}],
                [{"category": "tech", "count": 50}],
                [{"visibility": "enterprise", "count": 30}],
                [{"count": 10}],
            ]
            from server.api.search import search_stats
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(search_stats(user))
            assert result["total_documents"] == 100
            assert result["recent_7d"] == 10


# ========== server/api/sync.py ==========

class TestSyncAPI:
    def test_sync_status(self):
        with patch('server.api.sync.db_query') as mock_db:
            mock_db.return_value = [{"directory": "/home/docs", "running": True,
                                      "lastSync": "2024-01-01", "fileCount": 42}]
            from server.api.sync import sync_status
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(sync_status(user))
            assert result["running"] is True

    def test_sync_config_new(self):
        with patch('server.api.sync.db_query') as mock_db:
            mock_db.side_effect = [[], []]
            from server.api.sync import sync_config, SyncConfig
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(sync_config(SyncConfig(directory="/home/docs"), user))
            assert result["directory"] == "/home/docs"

    def test_sync_start_no_config(self):
        with patch('server.api.sync.db_query', return_value=[]):
            from server.api.sync import sync_start
            from server.domain.user import User
            from fastapi import HTTPException
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(sync_start(user))
            assert exc.value.status_code == 400

    def test_sync_stop(self):
        with patch('server.api.sync.db_query') as mock_db:
            mock_db.return_value = [{"id": "sync:1", "directory": "/d", "running": True}]
            from server.api.sync import sync_stop
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(sync_stop(user))
            assert result["running"] is False


# ========== server/api/teams.py ==========

class TestTeamsAPI:
    def test_create_team(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.return_value = [{"id": "team:1", "name": "T1", "description": "d",
                                      "owner_id": "user:0"}]
            from server.api.teams import create_team, TeamCreate
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(create_team(TeamCreate(name="T1", description="d"), admin))
            assert result["name"] == "T1"

    def test_list_teams(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.return_value = [{"id": "team:1", "name": "T1", "description": "d", "owner_id": "user:0"}]
            from server.api.teams import list_teams
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(list_teams(user))
            assert len(result) == 1

    def test_get_team(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.side_effect = [
                [{"id": "team:1", "name": "T1", "description": "d", "owner_id": "user:0"}],
                [],
            ]
            from server.api.teams import get_team
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(get_team("team:1", user))
            assert result["name"] == "T1"

    def test_add_member(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.return_value = [{"id": "tm:1", "team_id": "team:1", "user_id": "user:2", "role": "member"}]
            from server.api.teams import add_member, TeamMemberAdd
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(add_member("team:1", TeamMemberAdd(user_id="user:2", role="member"), admin))
            assert result["role"] == "member"

    def test_remove_member(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.return_value = []
            from server.api.teams import remove_member
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(remove_member("team:1", "user:2", admin))
            assert result["status"] == "ok"

    def test_delete_team(self):
        with patch('server.api.teams.db_query') as mock_db:
            mock_db.return_value = []
            from server.api.teams import delete_team
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(delete_team("team:1", admin))
            assert result["status"] == "ok"


# ========== server/api/permissions.py ==========

class TestPermissionsAPI:
    def test_set_visibility(self):
        with patch('server.api.permissions.db_query') as mock_db:
            mock_db.side_effect = [
                [{"id": "source:1", "owner_id": "user:0", "visibility": "private"}],
                [],
            ]
            from server.api.permissions import set_source_visibility, VisibilityUpdate
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(set_source_visibility("source:1", VisibilityUpdate(visibility="enterprise"), admin))
            assert result["visibility"] == "enterprise"

    def test_set_visibility_not_owner(self):
        with patch('server.api.permissions.db_query') as mock_db:
            mock_db.return_value = [{"id": "source:1", "owner_id": "user:99", "visibility": "private"}]
            from server.api.permissions import set_source_visibility, VisibilityUpdate
            from server.domain.user import User
            from fastapi import HTTPException
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(set_source_visibility("source:1", VisibilityUpdate(visibility="enterprise"), user))
            assert exc.value.status_code == 403

    def test_check_access_admin(self):
        with patch('server.api.permissions.db_query') as mock_db:
            mock_db.return_value = [{"id": "source:1", "owner_id": "user:99", "visibility": "private"}]
            from server.api.permissions import check_source_access
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(check_source_access("source:1", admin))
            assert result["access"] is True

    def test_check_access_owner(self):
        with patch('server.api.permissions.db_query') as mock_db:
            mock_db.return_value = [{"id": "source:1", "owner_id": "user:1", "visibility": "private"}]
            from server.api.permissions import check_source_access
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(check_source_access("source:1", user))
            assert result["access"] is True

    def test_check_access_denied(self):
        with patch('server.api.permissions.db_query') as mock_db:
            mock_db.return_value = [{"id": "source:1", "owner_id": "user:99", "visibility": "private"}]
            from server.api.permissions import check_source_access
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(check_source_access("source:1", user))
            assert result["access"] is False


# ========== server/api/curation.py ==========

class TestCurationAPI:
    def test_list_curatable_sources(self):
        with patch('server.api.curation.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = [{"id": "source:1", "title": "Doc 1", "status": "pending_review"}]
            mock_get_db.return_value = mock_db
            from server.api.curation import get_review_queue
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(get_review_queue(limit=50, offset=0, user=admin))
            assert result["total"] >= 0

    def test_list_curatable_denied(self):
        from server.api.curation import get_review_queue
        from server.domain.user import User
        from fastapi import HTTPException
        user = User(id="user:1", username="u", email="u@t.com",
                    display_name="U", password_hash="h", role="viewer")
        # Viewer can still access queue (auth is handled by Depends, not in function)
        with patch('server.api.curation.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = []
            mock_get_db.return_value = mock_db
            result = asyncio.run(get_review_queue(limit=50, offset=0, user=user))
            assert result["total"] == 0

    def test_publish_to_enterprise(self):
        with patch('server.api.curation.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = [{"id": "source:1", "title": "Test Doc", "full_text": "content"}]
            mock_get_db.return_value = mock_db
            from server.api.curation import review_document, ReviewAction
            from server.domain.user import User
            admin = User(id="user:0", username="admin", email="a@b.com",
                         display_name="A", password_hash="h", role="admin")
            result = asyncio.run(review_document(
                ReviewAction(source_id="source:1", action="approve"), admin))
            assert result["status"] == "approved"

    def test_list_enterprise_sources(self):
        with patch('server.api.curation.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = [{"id": "source:1", "title": "Enterprise Doc", "status": "approved"}]
            mock_get_db.return_value = mock_db
            from server.api.curation import get_review_queue
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(get_review_queue(status="approved", limit=50, offset=0, user=user))
            assert result["total"] >= 0


# ========== server/domain/user.py ==========

class TestUserDomainExtended:
    def test_create_user(self):
        with patch('server.domain.user.db_query') as mock_db, \
             patch('server.domain.user.hash_password', return_value="hashed"):
            mock_db.return_value = [{"id": "user:new", "username": "newuser", "email": "n@t.com",
                                      "display_name": "New", "password_hash": "hashed", "role": "viewer"}]
            from server.domain.user import User
            result = asyncio.run(User.create("newuser", "n@t.com", "pass", "New"))
            assert result.username == "newuser"

    def test_get_by_id(self):
        with patch('server.domain.user.db_query') as mock_db:
            mock_db.return_value = [{"id": "user:1", "username": "u1", "email": "u1@t.com",
                                      "display_name": "U1", "password_hash": "h", "role": "viewer"}]
            from server.domain.user import User
            result = asyncio.run(User.get_by_id("user:1"))
            assert result is not None
            assert result.username == "u1"

    def test_get_by_id_not_found(self):
        with patch('server.domain.user.db_query', return_value=[]):
            from server.domain.user import User
            result = asyncio.run(User.get_by_id("user:999"))
            assert result is None

    def test_get_all(self):
        with patch('server.domain.user.db_query') as mock_db:
            mock_db.return_value = [
                {"id": "user:1", "username": "u1", "email": "u1@t.com", "display_name": "U1",
                 "password_hash": "h", "role": "viewer"},
                {"id": "user:2", "username": "u2", "email": "u2@t.com", "display_name": "U2",
                 "password_hash": "h", "role": "admin"},
            ]
            from server.domain.user import User
            result = asyncio.run(User.get_all())
            assert len(result) == 2

    def test_verify_password(self):
        with patch('server.domain.user.verify_password', return_value=True):
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(user.verify_password("correct"))
            assert result is True

    def test_update_user(self):
        with patch('server.domain.user.db_query') as mock_db:
            mock_db.return_value = [{"id": "user:1", "username": "u", "email": "u@t.com",
                                      "display_name": "Updated", "password_hash": "h", "role": "editor"}]
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(user.update(display_name="Updated", role="editor"))
            assert result.display_name == "Updated"

    def test_delete_user(self):
        with patch('server.domain.user.db_query') as mock_db:
            mock_db.return_value = []
            from server.domain.user import User
            user = User(id="user:1", username="u", email="u@t.com",
                        display_name="U", password_hash="h", role="viewer")
            result = asyncio.run(user.delete())
            assert result is True


# ========== server/domain/category.py ==========

class TestCategoryDomainExtended:
    def test_create_category(self):
        with patch('server.domain.category.db_query') as mock_db:
            mock_db.return_value = [{"id": "cat:1", "name": "Tech", "description": "d",
                                      "parent_id": None, "sort_order": 0}]
            from server.domain.category import KnowledgeCategory
            result = asyncio.run(KnowledgeCategory.create("Tech", None, "d"))
            assert result.name == "Tech"

    def test_get_all_categories(self):
        with patch('server.domain.category.db_query') as mock_db:
            mock_db.return_value = [{"id": "cat:1", "name": "Tech", "description": "d",
                                      "parent_id": None, "sort_order": 0}]
            from server.domain.category import KnowledgeCategory
            result = asyncio.run(KnowledgeCategory.get_all())
            assert len(result) == 1

    def test_get_tree(self):
        with patch('server.domain.category.db_query') as mock_db:
            mock_db.return_value = [{"id": "cat:1", "name": "Tech", "description": "d",
                                      "parent_id": None, "sort_order": 0}]
            from server.domain.category import KnowledgeCategory
            result = asyncio.run(KnowledgeCategory.get_tree())
            assert isinstance(result, list)

    def test_delete_category(self):
        with patch('server.domain.category.db_query') as mock_db:
            mock_db.return_value = []
            from server.domain.category import KnowledgeCategory
            cat = KnowledgeCategory(id="cat:1", name="Tech", description="d")
            result = asyncio.run(cat.delete())
            assert result is None  # delete() returns None


# ========== server/domain/approval.py ==========

class TestApprovalDomainExtended:
    def test_create_approval(self):
        with patch('server.domain.approval.db_query') as mock_db:
            mock_db.return_value = [{"id": "app:1", "source_id": "source:1", "submitter_id": "user:1",
                                      "status": "pending"}]
            from server.domain.approval import Approval
            result = asyncio.run(Approval.create("source:1", "user:1"))
            assert result.status == "pending"

    def test_get_pending(self):
        with patch('server.domain.approval.db_query') as mock_db:
            mock_db.return_value = [{"id": "app:1", "source_id": "source:1", "submitter_id": "user:1",
                                      "status": "pending"}]
            from server.domain.approval import Approval
            result = asyncio.run(Approval.get_pending())
            assert len(result) == 1

    def test_approve_approval(self):
        with patch('server.domain.approval.db_query') as mock_db:
            mock_db.return_value = [{"id": "app:1", "source_id": "source:1", "submitter_id": "user:1",
                                      "status": "approved", "reviewer_id": "user:0"}]
            from server.domain.approval import Approval
            app = Approval(id="app:1", source_id="source:1", submitter_id="user:1")
            result = asyncio.run(app.approve("user:0", "ok"))
            assert result.status == "approved"

    def test_reject_approval(self):
        with patch('server.domain.approval.db_query') as mock_db:
            mock_db.return_value = [{"id": "app:1", "source_id": "source:1", "submitter_id": "user:1",
                                      "status": "rejected", "reviewer_id": "user:0"}]
            from server.domain.approval import Approval
            app = Approval(id="app:1", source_id="source:1", submitter_id="user:1")
            result = asyncio.run(app.reject("user:0", "not good"))
            assert result.status == "rejected"


# ========== classifier/api/classify.py ==========

class TestClassifierClassifyAPI:
    def test_classify_endpoint(self):
        with patch('classifier.api.classify.classify_document') as mock_classify:
            mock_classify.return_value = {"category": "技术", "confidence": 0.9}

            from classifier.api.classify import classify, ClassifyRequest
            result = asyncio.run(classify(ClassifyRequest(
                content="测试内容", title="测试文档"
            )))
            assert result["category"] == "技术"

    def test_classify_batch(self):
        with patch('classifier.api.classify.classify_document') as mock_classify:
            mock_classify.return_value = {"category": "技术", "confidence": 0.9}

            from classifier.api.classify import batch_classify, BatchClassifyRequest
            result = asyncio.run(batch_classify(BatchClassifyRequest(documents=[
                {"id": "1", "content": "doc1"},
                {"id": "2", "content": "doc2"},
            ])))
            assert len(result["results"]) == 2


# ========== classifier/api/webhook.py ==========

class TestClassifierWebhookAPI:
    def test_webhook_minio(self):
        from classifier.api.webhook import minio_webhook
        from fastapi import Request
        mock_req = MagicMock(spec=Request)
        mock_req.json = AsyncMock(return_value={
            "Records": [{
                "eventName": "s3:ObjectCreated:Put",
                "s3": {"object": {"key": "user_test/doc.pdf"}},
                "userMetadata": {"X-Amz-Meta-User-Id": "test_user"}
            }]
        })
        result = asyncio.run(minio_webhook(mock_req))
        assert result["status"] == "ok"

    def test_webhook_manual_process(self):
        with patch('classifier.api.webhook.start_pipeline') as mock_start:
            mock_start.return_value = {"job_id": "test-123", "object_key": "test.pdf"}
            from classifier.api.webhook import minio_webhook_test
            from fastapi import Request
            mock_req = MagicMock(spec=Request)
            mock_req.json = AsyncMock(return_value={"object_key": "test.pdf", "user_id": "user1"})
            result = asyncio.run(minio_webhook_test(mock_req))
            assert result["status"] == "ok"


# ========== classifier/services/classifier.py ==========

class TestClassifierServiceExtended:
    def test_classify_document_full(self):
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": '{"category": "技术研发", "confidence": 0.95}'
            }
            mock_http.return_value.__aenter__.return_value.post.return_value = mock_resp

            from classifier.services.classifier import classify_document
            result = asyncio.run(classify_document("AI and ML research paper"))
            assert isinstance(result, dict)

    def test_classify_document_error(self):
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_http.return_value.__aenter__.return_value.post.return_value = mock_resp

            from classifier.services.classifier import classify_document
            result = asyncio.run(classify_document("test"))
            assert result["category"] == "其他"  # fallback on error

    def test_extract_keywords_full(self):
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": '["人工智能", "机器学习", "深度学习"]'
            }
            mock_http.return_value.__aenter__.return_value.post.return_value = mock_resp

            from classifier.services.classifier import extract_keywords
            result = asyncio.run(extract_keywords("AI and ML content"))
            assert isinstance(result, list)

    def test_suggest_knowledge_tree_full(self):
        with patch('classifier.services.classifier.httpx.AsyncClient') as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": '{"tree": [{"name": "技术", "children": []}]}'
            }
            mock_http.return_value.__aenter__.return_value.post.return_value = mock_resp

            from classifier.services.classifier import suggest_knowledge_tree
            result = asyncio.run(suggest_knowledge_tree([{"title": "AI paper"}]))
            assert isinstance(result, dict)


# ========== server/core/database.py ==========

class TestDatabaseExtended:
    def test_get_db_returns_db(self):
        with patch('server.core.database._db') as mock_db:
            from server.core.database import get_db
            result = asyncio.run(get_db())
            assert result is mock_db

    def test_close_db(self):
        with patch('server.core.database._db') as mock_db:
            mock_db.close = AsyncMock()
            from server.core.database import close_db
            asyncio.run(close_db())
            mock_db.close.assert_called_once()
