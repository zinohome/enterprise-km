# 企业知识管理平台 (Enterprise KM)

基于 Open Notebook 的企业级知识管理平台，支持多用户、团队协作、AI 自动分类、联邦搜索。

## 架构

```
员工电脑                              企业服务器
┌──────────────────────────┐       ┌──────────────────────────────┐
│ 桌面应用 (Tauri)           │       │ nginx :443 (HTTPS + JWT)      │
│ ┌──────────────────────┐ │       │  ├─ /api/* → Server :5056     │
│ │ 联邦搜索               │ │       │  ├─ /enterprise/* → ON :5058 │
│ │ ① 本地 Open Notebook  │ │       │  └─ /classifier/* → :5057    │
│ │ ② 企业知识库 API       │─┼──→   │                              │
│ └──────────────────────┘ │       │ 企业 Open Notebook :5058      │
│                          │       │ (管理员策展发布的企业知识库)      │
│ Open Notebook :5055      │       │                              │
│ SurrealDB :8001          │       │ Enterprise KM Server :5056    │
│ rclone → MinIO          │       │ (认证/用户/团队/搜索/同步/策展)  │
└──────────────────────────┘       │                              │
                                   │ Classifier :5057              │
                                   │ (AI 分类 + MinIO webhook)     │
                                   │                              │
                                   │ MinIO :9000 (文档存储)         │
                                   │ SurrealDB :8000               │
                                   └──────────────────────────────┘
```

## 项目结构

```
enterprise-km/
├── server/                    # FastAPI 后端 (15 个 API 模块)
│   ├── api/                   # auth, users, teams, search, sync, curation...
│   ├── core/                  # config, database, security, permissions
│   ├── domain/                # user, category, approval
│   ├── migrations/            # SurrealDB schema
│   └── tests/                 # 173 个测试, 93% 覆盖率
├── classifier/                # AI 分类引擎
│   ├── api/                   # classify, webhook
│   ├── services/              # classifier, file_watcher
│   └── core/                  # config
├── desktop/                   # Tauri + Next.js 桌面应用
│   ├── src/
│   │   ├── app/               # 页面 (首页/登录/管理/企业知识库)
│   │   ├── components/        # FederatedSearch, SyncSettings, KnowledgeBase...
│   │   └── lib/               # API 客户端
│   ├── src-tauri/             # Rust 后端
│   │   └── src/               # main, rclone, services, tray, updater
│   └── scripts/               # setup.sh/bat, bin/ (rclone + SurrealDB)
├── deploy/                    # nginx, systemd, docker-compose
├── scripts/                   # backup, firewall, rclone-setup
├── docs/                      # 部署/用户/管理员文档
└── openspec/                  # OpenSpec 设计文档
```

## 快速开始

### 服务端部署

```bash
# 1. 启动基础设施
docker compose -f deploy/docker-compose.enterprise-notebook.yml up -d

# 2. 安装依赖
cd server && pip install -r requirements.txt
cd classifier && pip install -r requirements.txt

# 3. 运行迁移
python server/migrations/run.py

# 4. 启动服务
systemctl start enterprise-km-server
systemctl start enterprise-km-classifier
```

### 桌面应用

```bash
# 安装
sudo dpkg -i 企业知识管理_0.1.0_amd64.deb

# 首次启动自动初始化环境
#   rclone + SurrealDB → 秒级 (预置二进制)
#   Open Notebook → 2-3 分钟 (pip install)
```

## 测试

```bash
cd server
pytest tests/ -v --cov=server --cov=classifier
# 173 passed, 93% coverage
```

## 技术栈

| 层 | 技术 |
|---|------|
| 桌面应用 | Tauri 2 + Next.js 15 + Rust |
| 后端 API | FastAPI + SurrealDB |
| AI 分类 | Ollama (qwen2.5:7b) |
| 知识库引擎 | Open Notebook |
| 文件同步 | rclone → MinIO (S3) |
| 认证 | JWT + bcrypt |
| 部署 | systemd + nginx + Docker |
