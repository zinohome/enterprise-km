# Tasks: 企业级知识管理平台

## Phase 1: 基础设施搭建 (Week 1-2)

- [ ] **T1.1: 项目初始化**
  - 创建 `enterprise-km-server`、`enterprise-km-classifier`、`enterprise-km-desktop` 三个项目骨架
  - 配置 Docker Compose（MinIO + SurrealDB + Open Notebook + 新服务）
  - 配置开发环境（Python venv、Node.js、Rust/Tauri）
  - Files: `docker-compose.yml`, `Makefile`, 各项目 `pyproject.toml` / `package.json`
  - Verification: `docker compose up` 所有服务正常启动

- [ ] **T1.2: MinIO 部署与配置**
  - Docker 部署 MinIO
  - 创建 bucket：`enterprise-km`
  - 配置访问密钥
  - 测试 S3 API 连通性
  - Files: `docker-compose.yml` MinIO 配置
  - Verification: `aws s3 ls --endpoint-url http://localhost:9000` 可列出 bucket

- [ ] **T1.3: rclone 集成验证**
  - 在开发机上安装 rclone
  - 配置 MinIO remote
  - 测试 `rclone sync` 本地目录 → MinIO
  - 测试增量同步、冲突检测
  - Files: rclone 配置脚本
  - Verification: 本地文件变更后 MinIO 中文件同步更新

## Phase 2: 多用户系统 (Week 2-3)

- [ ] **T2.1: SurrealDB Schema 扩展**
  - 创建 user、team、team_member 表
  - 创建 audit_log 表
  - 创建 knowledge_category、approval 表
  - 改造 notebook、source、note 表（加 owner_id、visibility 等字段）
  - 编写数据库迁移脚本
  - Files: `open_notebook/database/migrations/`
  - Verification: 迁移执行成功，新表可正常 CRUD

- [ ] **T2.2: 用户认证 API**
  - 实现 `POST /api/auth/login`（JWT 签发）
  - 实现 `POST /api/auth/register`
  - 实现 `GET /api/auth/me`
  - 实现 JWT 中间件（验证 Token，注入 request.state.user）
  - Files: `enterprise-km-server/api/auth.py`, `enterprise-km-server/core/security.py`
  - Verification: 登录获取 Token，用 Token 访问受保护接口

- [ ] **T2.3: 用户管理 API**
  - 实现用户 CRUD（admin 权限）
  - 实现团队 CRUD
  - 实现团队成员管理
  - Files: `enterprise-km-server/api/users.py`, `enterprise-km-server/api/teams.py`
  - Verification: admin 可创建/编辑/删除用户和团队

- [ ] **T2.4: 权限中间件**
  - 实现角色权限装饰器（`@require_role("admin")`）
  - 实现数据权限过滤（查询时自动加 visibility 条件）
  - 改造 Open Notebook API，加权限校验
  - Files: `enterprise-km-server/core/permissions.py`
  - Verification: viewer 无法调用编辑接口，私有文档仅 owner 可见

## Phase 3: 知识处理增强 (Week 3-4)

- [ ] **T3.1: 文件监控服务**
  - 实现 MinIO bucket 事件监听（新文件上传通知）
  - 新文件自动触发 Open Notebook source processing
  - 处理结果回调（成功/失败通知）
  - Files: `enterprise-km-server/services/file_watcher.py`
  - Verification: 上传文件到 MinIO 后自动触发解析

- [ ] **T3.2: 自动分类引擎**
  - 实现文档分类 API（基于 LLM 的语义分类）
  - 实现关键词提取 API
  - 实现知识树建议 API
  - 实现批量分类
  - Files: `enterprise-km-classifier/api/classify.py`, `enterprise-km-classifier/services/classifier.py`
  - Verification: 上传文档后自动建议分类，准确率 > 70%

- [ ] **T3.3: 知识分类管理**
  - 实现知识分类树 CRUD API
  - 实现分类审核界面 API
  - 实现文档归类 API
  - Files: `enterprise-km-server/api/categories.py`
  - Verification: 管理员可创建分类树，将文档归入分类

- [ ] **T3.4: 审批工作流**
  - 实现审批提交 API
  - 实现审批处理 API（批准/退回）
  - 实现审批通知
  - Files: `enterprise-km-server/api/approvals.py`, `enterprise-km-server/services/approval_service.py`
  - Verification: editor 提交 → manager 审批 → 文档发布

## Phase 4: 桌面应用 (Week 4-6)

- [ ] **T4.1: Tauri 项目初始化**
  - 创建 Tauri 项目骨架
  - 集成 Next.js 前端（继承 Open Notebook 前端代码）
  - 配置开发环境
  - Files: `enterprise-km-desktop/src-tauri/`, `enterprise-km-desktop/src/`
  - Verification: `npm run tauri dev` 可启动桌面应用

- [ ] **T4.2: 登录页面**
  - 实现登录页面 UI
  - 对接认证 API
  - Token 持久化存储
  - Files: `enterprise-km-desktop/src/app/login/`
  - Verification: 输入账号密码可登录，Token 存储到本地

- [ ] **T4.3: rclone 集成**
  - Tauri 侧管理 rclone 进程（启动/停止/状态）
  - 实现同步目录选择 UI
  - 实现同步状态显示
  - Files: `enterprise-km-desktop/src-tauri/src/rclone.rs`, `enterprise-km-desktop/src/components/SyncStatus.tsx`
  - Verification: 选择目录后文件自动同步到 MinIO

- [ ] **T4.4: 系统托盘与自启**
  - 实现系统托盘图标
  - 实现关闭窗口最小化到托盘
  - 实现开机自启配置
  - Files: `enterprise-km-desktop/src-tauri/src/tray.rs`
  - Verification: 关闭窗口后托盘图标存在，右键可退出

- [ ] **T4.5: 自动更新**
  - 配置 Tauri updater
  - 实现版本检查
  - 实现自动下载安装
  - Files: `enterprise-km-desktop/src-tauri/src/updater.rs`
  - Verification: 发布新版本后应用提示更新

- [ ] **T4.6: 打包发布**
  - 配置 Windows .msi 打包
  - 配置 macOS .dmg 打包
  - 配置 Linux .AppImage 打包
  - 配置 CI/CD 自动构建
  - Files: `.github/workflows/release.yml`
  - Verification: 各平台安装包可正常安装运行

## Phase 5: 前端改造 (Week 4-5)

- [ ] **T5.1: 用户菜单**
  - 顶部栏加用户头像和下拉菜单
  - 个人信息、设置、退出登录
  - Files: `enterprise-km-desktop/src/components/UserMenu.tsx`
  - Verification: 登录后显示用户信息，可退出

- [ ] **T5.2: 知识库权限 UI**
  - 创建知识库时可选择权限（私有/团队/公开）
  - 知识库列表显示权限标识
  - Files: 改造 Open Notebook 前端 Notebook 创建/列表页
  - Verification: 创建私有知识库后其他用户不可见

- [ ] **T5.3: 企业知识库页面**
  - 新增"企业知识库"导航入口
  - 按分类树展示文档
  - 搜索支持按分类筛选
  - Files: `enterprise-km-desktop/src/app/enterprise/`
  - Verification: 可浏览企业知识库分类树，搜索可筛选

- [ ] **T5.4: 管理后台**
  - 用户管理页面（admin）
  - 知识分类管理页面（manager+）
  - 审批管理页面（manager+）
  - 审计日志页面（admin）
  - Files: `enterprise-km-desktop/src/app/admin/`
  - Verification: admin 可管理用户，manager 可审批文档

## Phase 6: 审计与监控 (Week 5-6)

- [ ] **T6.1: 审计日志**
  - 实现审计日志记录（登录/创建/编辑/删除/发布）
  - 实现审计日志查询 API
  - 实现审计日志前端页面
  - Files: `enterprise-km-server/services/audit_service.py`
  - Verification: 所有关键操作有日志记录

- [ ] **T6.2: 统计概览**
  - 实现统计 API（文档数/用户数/分类数/活跃度）
  - 实现统计前端页面
  - Files: `enterprise-km-server/api/stats.py`
  - Verification: 统计页面显示正确的数据

- [ ] **T6.3: 监控与告警**
  - 配置 Prometheus 指标采集
  - 配置 Grafana 仪表盘
  - 配置服务健康检查
  - Files: `docker/prometheus.yml`, `docker/grafana/`
  - Verification: Grafana 可查看各服务状态

## Phase 7: 测试与部署 (Week 6-7)

- [ ] **T7.1: 单元测试**
  - enterprise-km-server 核心 API 测试
  - enterprise-km-classifier 分类准确率测试
  - 权限中间件测试
  - Files: `tests/`
  - Verification: `pytest` 全部通过，覆盖率 > 80%

- [ ] **T7.2: 集成测试**
  - 端到端流程测试（上传 → 解析 → 分类 → 发布 → 搜索）
  - 多用户权限测试
  - 文件同步测试
  - Verification: 所有场景测试通过

- [ ] **T7.3: 部署文档**
  - 编写 Docker 部署指南
  - 编写 MinIO 配置指南
  - 编写桌面应用分发指南
  - Files: `docs/deployment.md`
  - Verification: 按文档可从零部署完整平台

- [ ] **T7.4: 用户文档**
  - 编写员工使用手册
  - 编写管理员手册
  - Files: `docs/user-guide.md`, `docs/admin-guide.md`
  - Verification: 新用户按文档可独立完成安装和使用
