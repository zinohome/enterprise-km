# Phase 1: 基础设施搭建

**Feature Name:** 企业级知识管理平台 — 基础设施搭建
**Goal:** 创建项目骨架，部署 MinIO + SurrealDB + Open Notebook，验证 rclone 同步
**Architecture:** 5 个服务（enterprise-km-server, enterprise-km-classifier, enterprise-km-desktop, Open Notebook, MinIO），Docker Compose 编排
**Tech Stack:** Python 3.11+ (FastAPI), Node.js 22+ (Next.js), Rust (Tauri), Docker, MinIO, SurrealDB
**Global Constraints:** Open Notebook 不改核心代码；所有新代码在 enterprise-km 项目下；不使用 sudo

---

## File Structure (Phase 1 产出)

```
enterprise-km/
├── docker-compose.yml              # 编排所有服务
├── Makefile                        # 常用命令
├── .env.example                    # 环境变量模板
├── server/                         # enterprise-km-server
│   ├── pyproject.toml
│   ├── main.py                     # FastAPI 入口
│   └── __init__.py
├── classifier/                     # enterprise-km-classifier
│   ├── pyproject.toml
│   ├── main.py                     # FastAPI 入口
│   └── __init__.py
├── desktop/                        # enterprise-km-desktop (Tauri + Next.js)
│   ├── package.json
│   ├── src-tauri/
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json
│   │   └── src/
│   │       └── main.rs
│   └── src/                        # Next.js 前端
│       └── app/
│           └── page.tsx
├── scripts/
│   └── rclone-setup.sh             # rclone 配置脚本
├── openspec/                       # OpenSpec 文档（已存在）
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-07-23-phase-1-infrastructure.md  # 本文件
```

---

## T1.1: 项目初始化

### Task 1.1.1: 创建项目目录结构

**Files:** `server/`, `classifier/`, `desktop/`, `scripts/`
**Steps:**

1. 创建目录：
```bash
mkdir -p /opt/data/workspace/enterprise-km/{server,classifier,desktop,scripts}
```

2. 验证：
```bash
ls -la /opt/data/workspace/enterprise-km/{server,classifier,desktop,scripts}
```

---

### Task 1.1.2: 创建 enterprise-km-server (FastAPI)

**Files:** `server/pyproject.toml`, `server/main.py`, `server/__init__.py`
**Steps:**

1. 创建 `server/pyproject.toml`：
```toml
[project]
name = "enterprise-km-server"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",
    "loguru>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. 创建 `server/__init__.py`（空文件）

3. 创建 `server/main.py`：
```python
from fastapi import FastAPI
from loguru import logger

app = FastAPI(title="Enterprise KM Server", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-km-server"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Enterprise KM Server on port 5056")
    uvicorn.run(app, host="0.0.0.0", port=5056)
```

4. 验证：
```bash
cd /opt/data/workspace/enterprise-km/server && python3 -c "from main import app; print(app.title)"
```

---

### Task 1.1.3: 创建 enterprise-km-classifier (FastAPI)

**Files:** `classifier/pyproject.toml`, `classifier/main.py`, `classifier/__init__.py`
**Steps:**

1. 创建 `classifier/pyproject.toml`：
```toml
[project]
name = "enterprise-km-classifier"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "httpx>=0.27.0",
    "loguru>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. 创建 `classifier/__init__.py`（空文件）

3. 创建 `classifier/main.py`：
```python
from fastapi import FastAPI
from loguru import logger

app = FastAPI(title="Enterprise KM Classifier", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-km-classifier"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Enterprise KM Classifier on port 5057")
    uvicorn.run(app, host="0.0.0.0", port=5057)
```

4. 验证：
```bash
cd /opt/data/workspace/enterprise-km/classifier && python3 -c "from main import app; print(app.title)"
```

---

### Task 1.1.4: 创建 enterprise-km-desktop 骨架 (Tauri + Next.js)

**Files:** `desktop/package.json`, `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/tauri.conf.json`, `desktop/src-tauri/src/main.rs`, `desktop/src/app/page.tsx`
**Steps:**

1. 创建 `desktop/package.json`：
```json
{
  "name": "enterprise-km-desktop",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "tauri": "tauri"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0",
    "typescript": "^5.0.0",
    "@types/react": "^19.0.0",
    "@types/node": "^22.0.0"
  }
}
```

2. 创建 `desktop/src-tauri/Cargo.toml`：
```toml
[package]
name = "enterprise-km-desktop"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[build-dependencies]
tauri-build = { version = "2", features = [] }
```

3. 创建 `desktop/src-tauri/tauri.conf.json`：
```json
{
  "productName": "企业知识管理",
  "version": "0.1.0",
  "identifier": "com.enterprise.km",
  "build": {
    "devUrl": "http://localhost:3000",
    "frontendDist": "../out"
  },
  "app": {
    "withGlobalTauri": true,
    "windows": [
      {
        "title": "企业知识管理",
        "width": 1200,
        "height": 800
      }
    ]
  }
}
```

4. 创建 `desktop/src-tauri/src/main.rs`：
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

5. 创建 `desktop/src/app/page.tsx`：
```tsx
export default function Home() {
  return (
    <main>
      <h1>企业知识管理平台</h1>
      <p>Loading...</p>
    </main>
  );
}
```

6. 验证：
```bash
cd /opt/data/workspace/enterprise-km/desktop && ls package.json src-tauri/Cargo.toml src/app/page.tsx
```

---

### Task 1.1.5: 创建 Docker Compose

**Files:** `docker-compose.yml`, `.env.example`
**Steps:**

1. 创建 `.env.example`：
```bash
# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET=enterprise-km

# SurrealDB
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_PORT=8000

# Open Notebook
OPEN_NOTEBOOK_ENCRYPTION_KEY=dev-encryption-key-change-in-production
```

2. 创建 `docker-compose.yml`：
```yaml
version: "3.8"

services:
  minio:
    image: minio/minio:latest
    container_name: enterprise-km-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin123}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3

  surrealdb:
    image: surrealdb/surrealdb:latest
    container_name: enterprise-km-surrealdb
    ports:
      - "8000:8000"
    command: start --user ${SURREAL_USER:-root} --pass ${SURREAL_PASSWORD:-root}
    volumes:
      - surrealdb_data:/data
    healthcheck:
      test: ["CMD", "surreal", "is-ready", "--endpoint", "http://localhost:8000"]
      interval: 10s
      timeout: 5s
      retries: 5

  open-notebook:
    image: lfnovo/open-notebook:latest
    container_name: enterprise-km-open-notebook
    ports:
      - "5055:5055"
    environment:
      SURREAL_URL: ws://surrealdb:8000/rpc
      SURREAL_USER: ${SURREAL_USER:-root}
      SURREAL_PASSWORD: ${SURREAL_PASSWORD:-root}
      OPEN_NOTEBOOK_ENCRYPTION_KEY: ${OPEN_NOTEBOOK_ENCRYPTION_KEY:-dev-key}
    depends_on:
      surrealdb:
        condition: service_healthy
    volumes:
      - open_notebook_data:/app/data

volumes:
  minio_data:
  surrealdb_data:
  open_notebook_data:
```

3. 验证：
```bash
cd /opt/data/workspace/enterprise-km && docker compose config --quiet && echo "Config OK"
```

---

### Task 1.1.6: 创建 Makefile

**Files:** `Makefile`
**Steps:**

1. 创建 `Makefile`：
```makefile
.PHONY: up down status logs clean

up:
	docker compose up -d
	@echo "Services starting..."
	@sleep 5
	@$(MAKE) status

down:
	docker compose down

status:
	@echo "=== Service Status ==="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

logs:
	docker compose logs -f --tail=50

clean:
	docker compose down -v
	@echo "Volumes removed."

dev-server:
	cd server && uvicorn main:app --host 0.0.0.0 --port 5056 --reload

dev-classifier:
	cd classifier && uvicorn main:app --host 0.0.0.0 --port 5057 --reload

dev-desktop:
	cd desktop && npm run dev
```

2. 验证：
```bash
cd /opt/data/workspace/enterprise-km && make status 2>&1 | head -5
```

---

## T1.2: MinIO 部署与配置

### Task 1.2.1: 启动 MinIO

**Steps:**

1. 启动 MinIO：
```bash
cd /opt/data/workspace/enterprise-km && docker compose up -d minio
```

2. 等待健康检查通过：
```bash
sleep 5 && docker compose ps minio
```

3. 验证 MinIO 可访问：
```bash
curl -s http://localhost:9000/minio/health/live
```
**Expected:** 返回空响应（HTTP 200）

---

### Task 1.2.2: 创建 MinIO bucket

**Steps:**

1. 安装 MinIO Client（如果未安装）：
```bash
which mc || (curl -sL https://dl.min.io/client/mc/release/linux-amd64/mc -o ~/.local/bin/mc && chmod +x ~/.local/bin/mc)
```

2. 配置 MinIO 别名：
```bash
mc alias set localminio http://localhost:9000 minioadmin minioadmin123
```

3. 创建 bucket：
```bash
mc mb localminio/enterprise-km --ignore-existing
```

4. 验证 bucket 存在：
```bash
mc ls localminio/
```
**Expected:** 输出包含 `enterprise-km/`

---

### Task 1.2.3: 测试 S3 API 连通性

**Steps:**

1. 测试上传文件：
```bash
echo "test content" > /tmp/test-s3.txt
mc cp /tmp/test-s3.txt localminio/enterprise-km/test-s3.txt
```

2. 测试列出文件：
```bash
mc ls localminio/enterprise-km/
```
**Expected:** 输出包含 `test-s3.txt`

3. 测试下载文件：
```bash
mc cp localminio/enterprise-km/test-s3.txt /tmp/test-s3-downloaded.txt
diff /tmp/test-s3.txt /tmp/test-s3-downloaded.txt && echo "S3 API OK"
```
**Expected:** `S3 API OK`

4. 清理测试文件：
```bash
mc rm localminio/enterprise-km/test-s3.txt
rm /tmp/test-s3.txt /tmp/test-s3-downloaded.txt
```

---

## T1.3: rclone 集成验证

### Task 1.3.1: 安装 rclone

**Steps:**

1. 检查 rclone 是否已安装：
```bash
which rclone && rclone version --check || echo "NEED_INSTALL"
```

2. 如果未安装，安装 rclone：
```bash
curl -sL https://rclone.org/install.sh | bash
```

3. 验证安装：
```bash
rclone version | head -1
```
**Expected:** 输出版本号

---

### Task 1.3.2: 配置 rclone MinIO remote

**Files:** `scripts/rclone-setup.sh`
**Steps:**

1. 创建 `scripts/rclone-setup.sh`：
```bash
#!/bin/bash
# rclone MinIO 配置脚本
# 用法: bash scripts/rclone-setup.sh

RCLONE_REMOTE="enterprise-km-minio"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"
MINIO_BUCKET="${MINIO_BUCKET:-enterprise-km}"

echo "Configuring rclone remote: $RCLONE_REMOTE"

rclone config create "$RCLONE_REMOTE" s3 \
    provider=Minio \
    endpoint="$MINIO_ENDPOINT" \
    access_key_id="$MINIO_ACCESS_KEY" \
    secret_access_key="$MINIO_SECRET_KEY" \
    --non-interactive 2>&1

echo "Testing connection..."
rclone ls "$RCLONE_REMOTE:$MINIO_BUCKET" 2>&1

echo "Done! Remote '$RCLONE_REMOTE' configured."
echo ""
echo "Usage:"
echo "  rclone sync /local/path $RCLONE_REMOTE:$MINIO_BUCKET/user_001/"
echo "  rclone ls $RCLONE_REMOTE:$MINIO_BUCKET/"
```

2. 运行配置脚本：
```bash
chmod +x /opt/data/workspace/enterprise-km/scripts/rclone-setup.sh
bash /opt/data/workspace/enterprise-km/scripts/rclone-setup.sh
```

3. 验证 remote 已配置：
```bash
rclone listremotes | grep enterprise-km-minio
```
**Expected:** `enterprise-km-minio:`

---

### Task 1.3.3: 测试 rclone sync

**Steps:**

1. 创建测试目录和文件：
```bash
mkdir -p /tmp/rclone-test-source
echo "rclone sync test file 1" > /tmp/rclone-test-source/doc1.txt
echo "rclone sync test file 2" > /tmp/rclone-test-source/doc2.txt
mkdir -p /tmp/rclone-test-source/subdir
echo "nested file" > /tmp/rclone-test-source/subdir/nested.txt
```

2. 执行同步：
```bash
rclone sync /tmp/rclone-test-source enterprise-km-minio:enterprise-km/test-sync/ --verbose
```

3. 验证文件已同步：
```bash
rclone ls enterprise-km-minio:enterprise-km/test-sync/
```
**Expected:** 输出包含 `doc1.txt`, `doc2.txt`, `subdir/nested.txt`

---

### Task 1.3.4: 测试增量同步

**Steps:**

1. 修改本地文件：
```bash
echo "updated content" >> /tmp/rclone-test-source/doc1.txt
```

2. 再次同步：
```bash
rclone sync /tmp/rclone-test-source enterprise-km-minio:enterprise-km/test-sync/ --verbose
```

3. 验证只同步了变更文件（观察 verbose 输出中只有 doc1.txt 被传输）

4. 删除本地文件：
```bash
rm /tmp/rclone-test-source/doc2.txt
```

5. 同步（删除远端多余文件）：
```bash
rclone sync /tmp/rclone-test-source enterprise-km-minio:enterprise-km/test-sync/ --verbose
```

6. 验证远端文件已删除：
```bash
rclone ls enterprise-km-minio:enterprise-km/test-sync/ | grep doc2.txt
```
**Expected:** 无输出（doc2.txt 已被删除）

---

### Task 1.3.5: 清理测试数据

**Steps:**

1. 清理远端测试数据：
```bash
rclone purge enterprise-km-minio:enterprise-km/test-sync/
```

2. 清理本地测试数据：
```bash
rm -rf /tmp/rclone-test-source
```

3. 验证清理完成：
```bash
rclone ls enterprise-km-minio:enterprise-km/test-sync/ 2>&1
```
**Expected:** 报错或空输出（目录不存在）

---

## Phase 1 完成验证

全部任务完成后，运行以下验证：

```bash
# 1. 所有 Docker 服务正常
cd /opt/data/workspace/enterprise-km && docker compose ps

# 2. MinIO 可访问
curl -s http://localhost:9000/minio/health/live

# 3. rclone remote 已配置
rclone listremotes | grep enterprise-km-minio

# 4. 项目结构完整
ls -la server/main.py classifier/main.py desktop/package.json docker-compose.yml Makefile scripts/rclone-setup.sh
```

**全部通过后，Phase 1 完成。**
