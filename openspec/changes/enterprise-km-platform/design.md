# Design: 企业级知识管理平台

## Approach

**核心原则：Open Notebook 不改核心代码，企业能力加在外面。**

整个平台由四个独立服务组成，通过 API 和文件系统协作：

```
┌─────────────────────────────────────────────────────────────────┐
│                    企业级知识管理平台                             │
│                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐                  │
│  │  enterprise-km-   │   │  enterprise-km-   │                  │
│  │  desktop (Tauri)  │   │  server (FastAPI)  │                  │
│  │  · Open Notebook  │   │  · 多用户管理       │                  │
│  │    前端内嵌        │   │  · 权限控制         │                  │
│  │  · rclone 内置    │   │  · 审批工作流       │                  │
│  │  · 系统托盘       │   │  · 审计日志         │                  │
│  └────────┬─────────┘   └────────┬─────────┘                  │
│           │ 文件同步              │ REST API                     │
│           ▼                      ▼                              │
│  ┌──────────────────┐   ┌──────────────────┐                  │
│  │  MinIO            │   │  Open Notebook    │                  │
│  │  (S3 文件存储)     │   │  (核心引擎)        │                  │
│  │  · 用户目录       │   │  · SurrealDB      │                  │
│  │  · 共享目录       │   │  · LangGraph      │                  │
│  │  · 版本管理       │   │  · Esperanto      │                  │
│  └────────┬─────────┘   └────────┬─────────┘                  │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌──────────────────────────────────────────┐                  │
│  │  enterprise-km-classifier                 │                  │
│  │  · 文档自动分类                            │                  │
│  │  · 关键词提取                              │                  │
│  │  · 知识树构建                              │                  │
│  │  · 相似文档聚类                            │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

### 服务拆分

| 服务 | 技术栈 | 端口 | 职责 |
|------|--------|------|------|
| `enterprise-km-server` | FastAPI + Python 3.11+ | 5056 | 多用户管理、权限、审批、审计 |
| `enterprise-km-desktop` | Tauri + Next.js | 本地 | 桌面应用，内嵌前端 + rclone |
| `enterprise-km-classifier` | FastAPI + Python 3.11+ | 5057 | 自动分类、关键词提取、聚类 |
| Open Notebook | FastAPI + SurrealDB | 5055 | 知识处理引擎（改造为多用户） |
| MinIO | Go | 9000/9001 | S3 兼容文件存储 |

### 数据流

```
用户桌面                          服务器
────────                          ──────
本地文件                           MinIO
  │                                 │
  ▼                                 ▼
rclone ──── 同步 ────→ 文件到达 ──→ 文件监控服务
                                      │
                                      ▼
                              Open Notebook API
                              · 解析文档
                              · 向量化
                              · 生成摘要
                                      │
                                      ▼
                              enterprise-km-classifier
                              · 自动分类
                              · 提取关键词
                              · 聚类
                                      │
                                      ▼
                              enterprise-km-server
                              · 权限校验
                              · 审批流程
                              · 发布到企业知识库
```

### 数据库设计

#### 新增表（在 SurrealDB 中）

```sql
-- 用户表
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD username ON user TYPE string;
DEFINE FIELD password_hash ON user TYPE string;
DEFINE FIELD email ON user TYPE string;
DEFINE FIELD display_name ON user TYPE string;
DEFINE FIELD role ON user TYPE string;  -- admin / manager / editor / viewer
DEFINE FIELD department ON user TYPE string;
DEFINE FIELD avatar_url ON user TYPE option<string>;
DEFINE FIELD created_at ON user TYPE datetime;
DEFINE FIELD updated_at ON user TYPE datetime;

-- 团队表
DEFINE TABLE team SCHEMAFULL;
DEFINE FIELD name ON team TYPE string;
DEFINE FIELD description ON team TYPE string;
DEFINE FIELD owner_id ON team TYPE record<user>;
DEFINE FIELD created_at ON team TYPE datetime;

-- 用户-团队关联
DEFINE TABLE team_member SCHEMAFULL;
DEFINE FIELD user_id ON team_member TYPE record<user>;
DEFINE FIELD team_id ON team_member TYPE record<team>;
DEFINE FIELD role ON team_member TYPE string;  -- owner / member

-- 审计日志
DEFINE TABLE audit_log SCHEMAFULL;
DEFINE FIELD user_id ON audit_log TYPE record<user>;
DEFINE FIELD action ON audit_log TYPE string;
DEFINE FIELD resource_type ON audit_log TYPE string;
DEFINE FIELD resource_id ON audit_log TYPE string;
DEFINE FIELD details ON audit_log TYPE object;
DEFINE FIELD ip_address ON audit_log TYPE string;
DEFINE FIELD created_at ON audit_log TYPE datetime;

-- 知识库分类
DEFINE TABLE knowledge_category SCHEMAFULL;
DEFINE FIELD name ON knowledge_category TYPE string;
DEFINE FIELD parent_id ON knowledge_category TYPE option<record<knowledge_category>>;
DEFINE FIELD description ON knowledge_category TYPE string;
DEFINE FIELD sort_order ON knowledge_category TYPE int;
DEFINE FIELD created_at ON knowledge_category TYPE datetime;

-- 审批记录
DEFINE TABLE approval SCHEMAFULL;
DEFINE FIELD source_id ON approval TYPE record<source>;
DEFINE FIELD submitter_id ON approval TYPE record<user>;
DEFINE FIELD reviewer_id ON approval TYPE option<record<user>>;
DEFINE FIELD status ON approval TYPE string;  -- pending / approved / rejected
DEFINE FIELD comment ON approval TYPE option<string>;
DEFINE FIELD created_at ON approval TYPE datetime;
DEFINE FIELD updated_at ON approval TYPE datetime;
```

#### 改造现有表

```sql
-- Notebook 加权限字段
DEFINE FIELD owner_id ON notebook TYPE record<user>;
DEFINE FIELD visibility ON notebook TYPE string DEFAULT 'private';  -- private / team / public
DEFINE FIELD team_id ON notebook TYPE option<record<team>>;

-- Source 加权限字段
DEFINE FIELD owner_id ON source TYPE record<user>;
DEFINE FIELD visibility ON source TYPE string DEFAULT 'private';
DEFINE FIELD category_id ON source TYPE option<record<knowledge_category>>;
DEFINE FIELD tags ON source TYPE option<array<string>>;
DEFINE FIELD status ON source TYPE string DEFAULT 'draft';  -- draft / pending_review / published

-- Note 加权限字段
DEFINE FIELD owner_id ON note TYPE record<user>;
DEFINE FIELD visibility ON note TYPE string DEFAULT 'private';
```

### API 设计

#### enterprise-km-server (端口 5056)

```
POST   /api/auth/login              # 登录，返回 JWT
POST   /api/auth/register           # 注册
GET    /api/auth/me                 # 当前用户信息

GET    /api/users                   # 用户列表 (admin)
POST   /api/users                   # 创建用户 (admin)
PUT    /api/users/{id}              # 更新用户 (admin)
DELETE /api/users/{id}              # 删除用户 (admin)

GET    /api/teams                   # 团队列表
POST   /api/teams                   # 创建团队
PUT    /api/teams/{id}              # 更新团队
POST   /api/teams/{id}/members      # 添加成员
DELETE /api/teams/{id}/members/{uid} # 移除成员

GET    /api/categories              # 知识分类树
POST   /api/categories              # 创建分类 (manager+)
PUT    /api/categories/{id}         # 更新分类 (manager+)
DELETE /api/categories/{id}         # 删除分类 (manager+)

GET    /api/approvals               # 审批列表
POST   /api/approvals               # 提交审批
PUT    /api/approvals/{id}          # 审批 (approve/reject)

GET    /api/audit-logs              # 审计日志 (admin)
GET    /api/stats                   # 统计概览
```

#### enterprise-km-classifier (端口 5057)

```
POST   /api/classify                # 对单个文档分类
POST   /api/classify/batch          # 批量分类
POST   /api/extract-keywords        # 提取关键词
POST   /api/cluster                 # 文档聚类
GET    /api/suggest-tree            # 建议知识树结构
```

### 权限中间件设计

```python
# 权限校验流程
async def permission_middleware(request, call_next):
    # 1. 从 Authorization header 提取 JWT
    # 2. 解析 JWT，获取 user_id 和 role
    # 3. 注入 request.state.user
    # 4. 路由级别的权限装饰器检查 role
    # 5. 数据级别的权限在 service 层检查 visibility
```

### 桌面应用架构

```
enterprise-km-desktop/
├── src-tauri/              # Tauri Rust 后端
│   ├── src/
│   │   ├── main.rs         # 应用入口
│   │   ├── rclone.rs       # rclone 进程管理
│   │   ├── tray.rs         # 系统托盘
│   │   ├── updater.rs      # 自动更新
│   │   └── commands.rs     # Tauri commands
│   └── tauri.conf.json
├── src/                    # Next.js 前端 (继承 Open Notebook)
│   ├── app/
│   │   ├── login/          # 登录页 (新增)
│   │   ├── settings/       # 设置页 (新增)
│   │   └── ...             # Open Notebook 原有页面
│   ├── components/
│   │   ├── SyncStatus.tsx  # 同步状态组件 (新增)
│   │   ├── UserMenu.tsx    # 用户菜单 (新增)
│   │   └── ...             # Open Notebook 原有组件
│   └── hooks/
│       ├── useAuth.ts      # 认证 hook (新增)
│       └── useSync.ts      # 同步状态 hook (新增)
└── package.json
```

## Trade-offs

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|---------|------|
| 数据库 | SurrealDB (不改) | PostgreSQL | 保持 Open Notebook 兼容，减少改造量 |
| 桌面框架 | Tauri | Electron | 体积小 10 倍，性能好 |
| 文件同步 | rclone | Seafile Client | 轻量、S3 原生支持、无额外服务 |
| 认证 | 自建 JWT | Keycloak OIDC | v1 快速上线，v2 可升级 |
| 分类引擎 | 独立服务 | Open Notebook 插件 | 解耦，可独立迭代 |

## Open Questions

1. **SurrealDB 的 scope/auth 能否满足多用户需求？** 需要验证 scope 是否能实现行级权限（用户只能查自己的数据）
2. **rclone 在 Tauri 中如何管理？** 是打包 rclone 二进制还是调用系统安装的？
3. **自动分类的准确率目标？** 70% 是否足够？是否需要人工审核门禁？
4. **桌面应用是否需要离线模式？** 离线时 Open Notebook 功能是否可用？
5. **文件冲突策略？** 同名文件同时修改，保留哪个版本？
