# Phase 2: 多用户系统

**Feature Name:** 企业级知识管理平台 — 多用户认证与权限
**Goal:** 实现用户注册/登录(JWT)、角色管理、团队管理、权限中间件
**Architecture:** enterprise-km-server (FastAPI, 端口5056) 提供认证和用户管理 API，连接 SurrealDB (192.168.66.40:8000)
**Tech Stack:** FastAPI, python-jose (JWT), passlib (bcrypt), SurrealDB
**Global Constraints:** 不改 Open Notebook 核心代码；所有新代码在 enterprise-km/server/ 下；TDD 优先

---

## File Structure (Phase 2 产出)

```
enterprise-km/server/
├── main.py                    # FastAPI 入口 (已有)
├── core/
│   ├── __init__.py
│   ├── config.py              # 配置 (JWT_SECRET, SURREAL_URL 等)
│   ├── security.py            # JWT 签发/验证, 密码哈希
│   ├── permissions.py         # 角色装饰器, 数据权限过滤
│   └── database.py            # SurrealDB 连接管理
├── domain/
│   ├── __init__.py
│   ├── user.py                # User 模型
│   ├── team.py                # Team 模型
│   └── audit.py               # AuditLog 模型
├── api/
│   ├── __init__.py
│   ├── auth.py                # POST /auth/login, /auth/register, GET /auth/me
│   ├── users.py               # CRUD /users
│   ├── teams.py               # CRUD /teams, /teams/{id}/members
│   └── deps.py                # get_current_user 依赖
├── migrations/
│   └── 001_phase2_schema.surrealql  # SurrealDB Schema 迁移
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_users.py
    └── test_permissions.py
```

---

## T2.1: SurrealDB Schema 扩展

### Task 2.1.1: 创建数据库连接模块

**Files:** `server/core/config.py`, `server/core/database.py`
**Steps:**

1. 创建 `server/core/__init__.py`（空文件）

2. 创建 `server/core/config.py`：
```python
import os

SURREAL_URL = os.getenv("SURREAL_URL", "ws://192.168.66.40:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASSWORD = os.getenv("SURREAL_PASSWORD", "root")
SURREAL_NAMESPACE = os.getenv("SURREAL_NAMESPACE", "open_notebook")
SURREAL_DATABASE = os.getenv("SURREAL_DATABASE", "open_notebook")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours
```

3. 创建 `server/core/database.py`：
```python
from contextlib import asynccontextmanager
from surrealdb import AsyncSurreal
from .config import SURREAL_URL, SURREAL_USER, SURREAL_PASSWORD, SURREAL_NAMESPACE, SURREAL_DATABASE

@asynccontextmanager
async def get_db():
    db = AsyncSurreal(SURREAL_URL)
    await db.signin({"username": SURREAL_USER, "password": SURREAL_PASSWORD})
    await db.use(SURREAL_NAMESPACE, SURREAL_DATABASE)
    try:
        yield db
    finally:
        await db.close()

async def db_query(query: str, vars: dict = None):
    async with get_db() as db:
        return await db.query(query, vars or {})
```

4. 验证：`python3 -c "from server.core.database import get_db; print('OK')"`

---

### Task 2.1.2: 编写 SurrealDB Schema 迁移

**Files:** `server/migrations/001_phase2_schema.surrealql`
**Steps:**

1. 创建 `server/migrations/` 目录

2. 创建 `server/migrations/001_phase2_schema.surrealql`：
```sql
-- Phase 2: 多用户系统 Schema 扩展

-- 用户表
DEFINE TABLE IF NOT EXISTS user SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS username ON user TYPE string;
DEFINE FIELD IF NOT EXISTS password_hash ON user TYPE string;
DEFINE FIELD IF NOT EXISTS email ON user TYPE string;
DEFINE FIELD IF NOT EXISTS display_name ON user TYPE string;
DEFINE FIELD IF NOT EXISTS role ON user TYPE string DEFAULT 'viewer';
DEFINE FIELD IF NOT EXISTS department ON user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS avatar_url ON user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON user TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated_at ON user TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS idx_user_username ON user COLUMNS username UNIQUE;
DEFINE INDEX IF NOT EXISTS idx_user_email ON user COLUMNS email UNIQUE;

-- 团队表
DEFINE TABLE IF NOT EXISTS team SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON team TYPE string;
DEFINE FIELD IF NOT EXISTS description ON team TYPE option<string>;
DEFINE FIELD IF NOT EXISTS owner_id ON team TYPE record<user>;
DEFINE FIELD IF NOT EXISTS created_at ON team TYPE datetime DEFAULT time::now();

-- 用户-团队关联
DEFINE TABLE IF NOT EXISTS team_member SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS in ON team_member TYPE record<team>;
DEFINE FIELD IF NOT EXISTS out ON team_member TYPE record<user>;
DEFINE FIELD IF NOT EXISTS role ON team_member TYPE string DEFAULT 'member';
DEFINE FIELD IF NOT EXISTS joined_at ON team_member TYPE datetime DEFAULT time::now();

-- 审计日志
DEFINE TABLE IF NOT EXISTS audit_log SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS user_id ON audit_log TYPE record<user>;
DEFINE FIELD IF NOT EXISTS action ON audit_log TYPE string;
DEFINE FIELD IF NOT EXISTS resource_type ON audit_log TYPE string;
DEFINE FIELD IF NOT EXISTS resource_id ON audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS details ON audit_log TYPE option<object>;
DEFINE FIELD IF NOT EXISTS ip_address ON audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON audit_log TYPE datetime DEFAULT time::now();

-- 知识库分类
DEFINE TABLE IF NOT EXISTS knowledge_category SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON knowledge_category TYPE string;
DEFINE FIELD IF NOT EXISTS parent_id ON knowledge_category TYPE option<record<knowledge_category>>;
DEFINE FIELD IF NOT EXISTS description ON knowledge_category TYPE option<string>;
DEFINE FIELD IF NOT EXISTS sort_order ON knowledge_category TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS created_at ON knowledge_category TYPE datetime DEFAULT time::now();

-- 审批记录
DEFINE TABLE IF NOT EXISTS approval SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS source_id ON approval TYPE record<source>;
DEFINE FIELD IF NOT EXISTS submitter_id ON approval TYPE record<user>;
DEFINE FIELD IF NOT EXISTS reviewer_id ON approval TYPE option<record<user>>;
DEFINE FIELD IF NOT EXISTS status ON approval TYPE string DEFAULT 'pending';
DEFINE FIELD IF NOT EXISTS comment ON approval TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON approval TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated_at ON approval TYPE datetime DEFAULT time::now();

-- 改造现有表：加 owner_id 和 visibility
DEFINE FIELD IF NOT EXISTS owner_id ON notebook TYPE option<record<user>>;
DEFINE FIELD IF NOT EXISTS visibility ON notebook TYPE string DEFAULT 'private';
DEFINE FIELD IF NOT EXISTS team_id ON notebook TYPE option<record<team>>;

DEFINE FIELD IF NOT EXISTS owner_id ON source TYPE option<record<user>>;
DEFINE FIELD IF NOT EXISTS visibility ON source TYPE string DEFAULT 'private';
DEFINE FIELD IF NOT EXISTS category_id ON source TYPE option<record<knowledge_category>>;
DEFINE FIELD IF NOT EXISTS tags ON source TYPE option<array<string>>;
DEFINE FIELD IF NOT EXISTS status ON source TYPE string DEFAULT 'draft';

DEFINE FIELD IF NOT EXISTS owner_id ON note TYPE option<record<user>>;
DEFINE FIELD IF NOT EXISTS visibility ON note TYPE string DEFAULT 'private';
```

3. 执行迁移：
```bash
surreal sql --endpoint ws://192.168.66.40:8000/rpc -u root -p root --ns open_notebook --db open_notebook < server/migrations/001_phase2_schema.surrealql
```

4. 验证：查询新表是否存在
```bash
surreal sql --endpoint ws://192.168.66.40:8000/rpc -u root -p root --ns open_notebook --db open_notebook -c "INFO FOR TABLE user;"
```

---

## T2.2: 用户认证 API

### Task 2.2.1: 创建安全模块 (JWT + 密码)

**Files:** `server/core/security.py`
**Steps:**

1. 创建 `server/core/security.py`：
```python
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
```

2. 验证：
```bash
cd /opt/data/workspace/enterprise-km && .venv/bin/python3 -c "
from server.core.security import hash_password, verify_password, create_access_token, decode_access_token
h = hash_password('test123')
assert verify_password('test123', h)
assert not verify_password('wrong', h)
t = create_access_token({'sub': 'user:test'})
d = decode_access_token(t)
assert d['sub'] == 'user:test'
print('ALL OK')
"
```

---

### Task 2.2.2: 创建 User 领域模型

**Files:** `server/domain/__init__.py`, `server/domain/user.py`
**Steps:**

1. 创建 `server/domain/__init__.py`（空文件）

2. 创建 `server/domain/user.py`：
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from server.core.database import db_query
from server.core.security import hash_password, verify_password

class User(BaseModel):
    id: Optional[str] = None
    username: str
    password_hash: Optional[str] = None
    email: str
    display_name: str
    role: str = "viewer"
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def create(cls, username: str, email: str, password: str, display_name: str) -> "User":
        password_hash = hash_password(password)
        result = await db_query(
            "CREATE user CONTENT { username: $username, email: $email, password_hash: $password_hash, display_name: $display_name, role: 'viewer' } RETURN AFTER;",
            {"username": username, "email": email, "password_hash": password_hash, "display_name": display_name}
        )
        return cls(**result[0])

    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        result = await db_query(
            "SELECT * FROM user WHERE username = $username LIMIT 1;",
            {"username": username}
        )
        return cls(**result[0]) if result else None

    @classmethod
    async def get_by_id(cls, user_id: str) -> Optional["User"]:
        result = await db_query("SELECT * FROM $id;", {"id": user_id})
        return cls(**result[0]) if result else None

    @classmethod
    async def get_all(cls) -> list["User"]:
        result = await db_query("SELECT * FROM user ORDER BY created_at DESC;")
        return [cls(**r) for r in result]

    async def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash or "")

    async def update(self, **kwargs) -> "User":
        kwargs["updated_at"] = datetime.now()
        result = await db_query(
            "UPDATE $id MERGE $data RETURN AFTER;",
            {"id": self.id, "data": kwargs}
        )
        for k, v in result[0].items():
            setattr(self, k, v)
        return self

    async def delete(self) -> bool:
        await db_query("DELETE $id;", {"id": self.id})
        return True
```

3. 验证：
```bash
cd /opt/data/workspace/enterprise-km && .venv/bin/python3 -c "from server.domain.user import User; print('OK')"
```

---

### Task 2.2.3: 创建认证 API 路由

**Files:** `server/api/__init__.py`, `server/api/deps.py`, `server/api/auth.py`
**Steps:**

1. 创建 `server/api/__init__.py`（空文件）

2. 创建 `server/api/deps.py`：
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from server.core.security import decode_access_token
from server.domain.user import User

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await User.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

3. 创建 `server/api/auth.py`：
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from server.domain.user import User
from server.core.security import create_access_token
from server.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await User.get_by_username(req.username)
    if not user or not await user.verify_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role}
    )

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    existing = await User.get_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = await User.create(username=req.username, email=req.email, password=req.password, display_name=req.display_name)
    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role}
    )

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "display_name": current_user.display_name, "role": current_user.role}
```

4. 更新 `server/main.py` 注册路由：
```python
from fastapi import FastAPI
from loguru import logger
from server.api import auth

app = FastAPI(title="Enterprise KM Server", version="0.1.0")
app.include_router(auth.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-km-server"}
```

5. 验证：启动服务并测试
```bash
# 启动服务
cd /opt/data/workspace/enterprise-km && .venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 5056 &
sleep 2

# 测试注册
curl -s -X POST http://localhost:5056/auth/register -H "Content-Type: application/json" -d '{"username":"testuser","email":"test@test.com","password":"test123","display_name":"Test User"}'

# 测试登录
curl -s -X POST http://localhost:5056/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"test123"}'

# 测试 me (用返回的 token)
TOKEN=$(curl -s -X POST http://localhost:5056/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:5056/auth/me -H "Authorization: Bearer $TOKEN"
```

---

## T2.3: 用户管理 API

### Task 2.3.1: 创建用户管理路由

**Files:** `server/api/users.py`
**Steps:**

1. 创建 `server/api/users.py`：
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("")
async def list_users(current_user: User = Depends(get_current_user)):
    users = await User.get_all()
    return [{"id": u.id, "username": u.username, "email": u.email, "display_name": u.display_name, "role": u.role, "department": u.department} for u in users]

@router.get("/{user_id}")
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role, "department": user.department}

@router.put("/{user_id}")
async def update_user(user_id: str, data: UserUpdate, admin: User = Depends(require_admin)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    await user.update(**update_data)
    return {"id": user.id, "username": user.username, "role": user.role}

@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
    return {"message": "User deleted"}
```

2. 更新 `server/main.py` 注册路由：
```python
from server.api import users
app.include_router(users.router)
```

---

## T2.4: 权限中间件

### Task 2.4.1: 创建权限模块

**Files:** `server/core/permissions.py`
**Steps:**

1. 创建 `server/core/permissions.py`：
```python
from functools import wraps
from typing import Callable, List
from fastapi import HTTPException, Depends
from server.domain.user import User
from server.api.deps import get_current_user

def require_role(*roles: str) -> Callable:
    """装饰器：要求用户具有指定角色之一"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail=f"Requires one of roles: {roles}")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 预定义角色快捷方式
require_admin = require_role("admin")
require_manager = require_role("admin", "manager")
require_editor = require_role("admin", "manager", "editor")
```

2. 验证：
```bash
cd /opt/data/workspace/enterprise-km && .venv/bin/python3 -c "from server.core.permissions import require_admin, require_manager; print('OK')"
```

---

## Phase 2 完成验证

```bash
# 1. Schema 迁移成功
surreal sql --endpoint ws://192.168.66.40:8000/rpc -u root -p root --ns open_notebook --db open_notebook -c "SELECT count() FROM user GROUP ALL;"

# 2. 注册新用户
curl -s -X POST http://localhost:5056/auth/register -H "Content-Type: application/json" -d '{"username":"admin","email":"admin@test.com","password":"admin123","display_name":"Admin"}'

# 3. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:5056/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 4. 验证 token
curl -s http://localhost:5056/auth/me -H "Authorization: Bearer $TOKEN"

# 5. 用户列表
curl -s http://localhost:5056/users -H "Authorization: Bearer $TOKEN"
```
