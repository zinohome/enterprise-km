# 企业知识管理平台 — 部署文档

## 环境要求

- Docker 29+ / Docker Compose v5+
- Python 3.12+ (服务器端)
- Node.js 22+ / Rust (桌面应用构建)
- MinIO (S3 兼容存储)
- SurrealDB v2
- Open Notebook v1

## 快速部署

### 1. 克隆项目

```bash
git clone <repo-url> /opt/enterprise-km
cd /opt/enterprise-km
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 修改密钥和密码
```

### 3. 启动基础设施

```bash
docker compose up -d minio
```

### 4. 初始化 MinIO

```bash
mc alias set localminio http://localhost:9000 minioadmin minioadmin123
mc mb localminio/enterprise-km
```

### 5. 配置 rclone

```bash
bash scripts/rclone-setup.sh
```

### 6. 安装 Python 依赖

```bash
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn python-jose passlib python-multipart httpx loguru surrealdb
```

### 7. 执行数据库迁移

```bash
.venv/bin/python -c "
import asyncio
from surrealdb import AsyncSurreal
async def migrate():
    db = AsyncSurreal('ws://localhost:8000/rpc')
    await db.signin({'username':'root','password':'root'})
    await db.use('open_notebook','open_notebook')
    with open('server/migrations/001_phase2_schema.surrealql') as f:
        for stmt in f.read().split(';'):
            if stmt.strip(): await db.query(stmt)
    await db.close()
asyncio.run(migrate())
"
```

### 8. 启动服务

```bash
# 服务器
nohup .venv/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port 5056 &

# 分类引擎
nohup .venv/bin/python -m uvicorn classifier.main:app --host 0.0.0.0 --port 5057 &
```

### 9. 验证

```bash
curl http://localhost:5056/health
curl http://localhost:5057/health
```

## 桌面应用构建

```bash
cd desktop
npm install
npm run tauri build
```

输出在 `desktop/src-tauri/target/release/bundle/`

## 服务端口

| 服务 | 端口 |
|------|------|
| Open Notebook | 5055 |
| Enterprise KM Server | 5056 |
| Enterprise KM Classifier | 5057 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| SurrealDB | 8000 |
