# Tasks: v0.2 产品重建

> 总估算：8-10 周（1 人全职），共 8 个 Phase，42 个任务。

---

## Phase 1: 基础设施（Week 1）

### T1.1: 部署 Redis
- **Files:** `docker-compose.yml`
- **Steps:** 添加 Redis 服务（`redis:7-alpine`），配置持久化，启动验证
- **Verification:** `redis-cli ping` → PONG

### T1.2: 部署 Meilisearch
- **Files:** `docker-compose.yml`
- **Steps:** 添加 Meilisearch 服务（`getmeili/meilisearch:v1.10`），配置 jieba 中文分词，配置 master key
- **Verification:** `curl localhost:7700/health` → 200

### T1.3: 部署 Qdrant
- **Files:** `docker-compose.yml`
- **Steps:** 添加 Qdrant 服务（`qdrant/qdrant:latest`），配置持久化卷
- **Verification:** `curl localhost:6333/health` → 200

### T1.4: 创建 Worker 服务骨架
- **Files:** `worker/__init__.py`, `worker/main.py`, `worker/pyproject.toml`
- **Steps:** 创建 Worker 目录，RQ Worker 入口，定义任务类型
- **Verification:** Worker 启动，可接收任务

### T1.5: 创建 Analytics 服务骨架
- **Files:** `analytics/__init__.py`, `analytics/main.py`, `analytics/pyproject.toml`
- **Steps:** 创建 Analytics 目录，FastAPI 骨架，端口 5060
- **Verification:** `curl localhost:5060/health` → 200

### T1.6: 更新 docker-compose.yml
- **Files:** `docker-compose.yml`
- **Steps:** 整合所有服务，配置网络和健康检查
- **Verification:** `docker compose up -d` 所有服务正常启动

---

## Phase 2: 制造业知识模型（Week 1-2）

### T2.1: 制造业 Schema 设计
- **Files:** `server/migrations/002_manufacturing_schema.surrealql`
- **Steps:** 创建 5 张制造业知识表（fa_report, ecn, process_spec, quality_standard, sop），定义字段和图关系
- **Verification:** Schema 迁移成功，表可查询

### T2.2: 文档类型识别
- **Files:** `worker/tasks/identify.py`
- **Steps:** 实现 AI 文档类型识别（调用 Ollama），识别 FA/ECN/工艺规范/质检标准/SOP
- **Verification:** 5 种类型识别准确率 > 85%

### T2.3: 结构化字段提取
- **Files:** `worker/tasks/extract.py`
- **Steps:** 根据文档类型，AI 提取对应结构化字段（现象/根因/零件号等）
- **Verification:** 字段提取准确率 > 80%

### T2.4: 知识图谱关联
- **Files:** `worker/tasks/graph.py`
- **Steps:** 构建文档间关联（FA→零件→ECN→SOP），写入 SurrealDB 图关系
- **Verification:** 图查询返回正确关联

### T2.5: 制造业搜索过滤器
- **Files:** `search/api/search.py`
- **Steps:** 实现按知识类型/零件号/产线/日期筛选
- **Verification:** 筛选结果正确

---

## Phase 3: 核心链路自动化（Week 2-3）

### T3.1: MinIO Webhook 集成
- **Files:** `classifier/api/webhook.py`（重写）
- **Steps:** 接收 MinIO 事件，解析 bucket/object key，任务入队 Redis
- **Verification:** 上传文件 → webhook 收到 → 任务入队

### T3.2: 文档解析 Worker
- **Files:** `worker/tasks/parse.py`
- **Steps:** 从 MinIO 下载文件，解析内容，写入 SurrealDB
- **Verification:** 上传 PDF → Worker 解析 → SurrealDB 有记录

### T3.3: 向量化 Worker
- **Files:** `worker/tasks/vectorize.py`
- **Steps:** 调用 bge-m3 生成 embedding，写入 Qdrant
- **Verification:** 文档解析后 → Qdrant 有向量

### T3.4: 自动分类 Worker
- **Files:** `worker/tasks/classify.py`
- **Steps:** 调用 Ollama 分类，建议知识树位置，写入审核队列
- **Verification:** 文档向量化后 → 自动分类 → 审核队列有记录

### T3.5: 任务编排与重试
- **Files:** `worker/orchestrator.py`
- **Steps:** 实现任务链（parse → identify → extract → vectorize → classify → graph），每步失败重试 3 次
- **Verification:** 模拟失败 → 自动重试 → 3 次后标记失败

### T3.6: 管理员审核界面
- **Files:** `server/api/curation.py`（重写）, `desktop/src/app/admin/page.tsx`（重写）
- **Steps:** 待审核列表、批量通过/驳回、修改分类/字段、发布到搜索服务
- **Verification:** 审核通过 → 文档出现在 Meilisearch + Qdrant

### T3.7: 发布到搜索服务
- **Files:** `worker/tasks/publish.py`
- **Steps:** 审核通过后写入 Meilisearch + Qdrant，更新状态为 published
- **Verification:** 发布后 → 可搜索

---

## Phase 4: 企业知识库搜索服务（Week 3-4）

### T4.1: 搜索服务 API
- **Files:** `search/__init__.py`, `search/main.py`, `search/api/search.py`
- **Steps:** FastAPI 搜索服务（端口 5059），混合搜索（Meilisearch + Qdrant），RRF 合并排序，权限过滤
- **Verification:** `GET /search/api/search?q=注塑缺陷` → 返回混合结果

### T4.2: RAG 问答
- **Files:** `search/api/ask.py`
- **Steps:** `/search/api/ask` 端点，搜索 Top-5 片段，构建 prompt，调用 Ollama 生成回答，返回出处引用
- **Verification:** 提问 → AI 回答 → 带出处引用

### T4.3: 权限过滤实现
- **Files:** `search/core/permissions.py`
- **Steps:** 从 JWT 解析 user_id + team_ids，Meilisearch filter + Qdrant payload filter
- **Verification:** 不同用户搜索同一关键词，结果不同

### T4.4: 搜索服务部署
- **Files:** `deploy/enterprise-km-search.service`
- **Steps:** systemd 服务，nginx 代理（`/search/*` → :5059），部署到 192.168.66.40
- **Verification:** 通过 nginx 访问搜索 API

---

## Phase 5: 桌面应用重写（Week 4-5）

### T5.1: 文件系统监控
- **Files:** `desktop/src-tauri/src/watcher.rs`（新文件）
- **Steps:** 使用 `notify` crate 实现跨平台文件监控，防抖 500ms，触发 rclone sync
- **Verification:** 创建文件 → 5 秒内检测到 → 触发同步

### T5.2: 原生通知
- **Files:** `desktop/src-tauri/src/notifications.rs`（新文件）
- **Steps:** 集成 `tauri-plugin-notification`，通知类型：同步完成、新知识入库、审批请求
- **Verification:** 同步完成 → 系统弹出通知

### T5.3: 离线检测
- **Files:** `desktop/src-tauri/src/network.rs`（新文件）
- **Steps:** 监听网络状态，离线时托盘变灰暂停同步，恢复后自动同步
- **Verification:** 断网 → 10 秒检测 → 恢复后自动同步

### T5.4: 一键初始化
- **Files:** `desktop/src-tauri/src/setup.rs`（新文件）
- **Steps:** 首次启动检测，运行 setup.sh，进度条显示，初始化完成后启动本地服务
- **Verification:** 全新环境 → 一键初始化 → 3 分钟内可用

### T5.5: 系统托盘增强
- **Files:** `desktop/src-tauri/src/tray.rs`（重写）
- **Steps:** 托盘图标状态变化（蓝/绿/红/灰），菜单：打开/暂停/通知/退出
- **Verification:** 托盘图标状态正确，菜单功能正常

### T5.6: 联邦搜索 UI 更新
- **Files:** `desktop/src/components/FederatedSearch.tsx`（重写）
- **Steps:** 并行请求本地 + 企业，合并结果，区分标签，企业结果支持 AI 问答
- **Verification:** 搜索 → 同时显示个人和企业结果

---

## Phase 6: 冷启动（Week 5-6）

### T6.1: 制造业示例文档
- **Files:** `server/templates/samples/*.md`
- **Steps:** 基于博世真实场景编写 50+ 份示例 Markdown 文档，覆盖 5 种知识类型
- **Verification:** 示例文档内容真实、可搜索、可 AI 问答

### T6.2: 示例数据导入 API
- **Files:** `server/api/templates.py`
- **Steps:** `POST /api/templates/import-samples`，导入后自动处理全链路
- **Verification:** 导入 → 50+ 文档自动处理 → 可搜索

### T6.3: 批量导入工具
- **Files:** `scripts/import.py`
- **Steps:** 递归扫描目录，识别文件格式，逐个处理，进度显示，导入报告
- **Verification:** 导入 100 个文件 → 进度显示 → 报告生成

### T6.4: 快速开始向导
- **Files:** `desktop/src/components/OnboardingWizard.tsx`（新文件）
- **Steps:** 5 步向导：选择行业 → 导入示例 → 配置同步 → 邀请团队 → 完成
- **Verification:** 新用户首次登录 → 向导引导 → 5 分钟看到完整知识库

### T6.5: 知识分类树预设
- **Files:** `server/templates/manufacturing_tree.json`
- **Steps:** 制造业分类树 JSON，5 大类，3-5 层深度
- **Verification:** 选择制造业 → 分类树自动创建

---

## Phase 7: 知识分析与智能推荐（Week 6-7）

### T7.1: 知识仪表盘 API
- **Files:** `analytics/api/dashboard.py`
- **Steps:** 文档总量、分类分布、热门文档、知识缺口分析、使用统计
- **Verification:** 仪表盘数据正确

### T7.2: 知识缺口分析
- **Files:** `analytics/services/gap_analysis.py`
- **Steps:** 分析各分类文档数量，识别低于阈值的分类，建议补充
- **Verification:** 缺口分析结果合理

### T7.3: 智能推荐
- **Files:** `analytics/services/recommendations.py`
- **Steps:** "处理过这个故障的人还看了..."，基于协同过滤 + 内容相似度
- **Verification:** 推荐结果相关

### T7.4: 学习路径推荐
- **Files:** `analytics/services/learning_path.py`
- **Steps:** 根据岗位推荐必读文档，按优先级排序
- **Verification:** 不同岗位推荐不同学习路径

### T7.5: 知识分析前端
- **Files:** `desktop/src/components/AnalyticsDashboard.tsx`（新文件）
- **Steps:** 仪表盘页面，图表展示（分类分布饼图、热门文档排行、使用趋势）
- **Verification:** 仪表盘数据可视化正确

---

## Phase 8: 测试、打包、文档（Week 7-8）

### T8.1: 核心链路 E2E 测试
- **Files:** `server/tests/test_core_pipeline.py`（新文件）
- **Steps:** 测试全链路：上传 → webhook → Worker → 审核 → 发布 → 搜索
- **Verification:** E2E 测试通过

### T8.2: 制造业知识模型测试
- **Files:** `server/tests/test_manufacturing.py`（新文件）
- **Steps:** 测试 5 种文档类型识别、字段提取、图谱关联
- **Verification:** 准确率达标

### T8.3: 搜索服务测试
- **Files:** `search/tests/test_search.py`（新文件）
- **Steps:** 测试全文搜索、向量搜索、混合排序、权限过滤、RAG 问答
- **Verification:** 搜索测试全部通过

### T8.4: 回归测试
- **Steps:** 运行 v0.1 全部 173 个测试，修复因架构变更导致的失败
- **Verification:** 173 个测试通过，覆盖率 > 85%

### T8.5: GitHub Actions 三平台构建
- **Files:** `.github/workflows/release.yml`（重写）
- **Steps:** 配置 matrix build（ubuntu/macos/windows），构建 Tauri，打包为 .deb/.dmg/.msi
- **Verification:** 推送 tag → CI 自动构建 → Release 有 3 个安装包

### T8.6: 安装测试
- **Steps:** 在 Win/Mac/Linux 虚拟机测试安装和首次启动
- **Verification:** 三平台安装成功，首次启动正常

### T8.7: 文档更新
- **Files:** `README.md`, `docs/deploy.md`, `docs/user-guide.md`, `docs/admin-guide.md`
- **Steps:** 更新所有文档，反映新架构、新功能
- **Verification:** 文档与实际部署一致

### T8.8: 生产部署
- **Steps:** 在 192.168.66.40 上部署全部新服务，运行完整测试套件
- **Verification:** 所有服务运行正常，核心链路端到端通过

---

## 依赖关系

```
Phase 1 (基础设施)
  ├── Phase 2 (制造业知识模型)
  │     ├── Phase 3 (核心链路)
  │     │     └── Phase 4 (搜索服务)
  │     └── Phase 7 (知识分析) ← 依赖 Phase 2/3/4
  ├── Phase 5 (桌面应用) ← 可与 Phase 2/3/4 并行
  ├── Phase 6 (冷启动) ← 依赖 Phase 2/3/4
  └── Phase 8 (测试/打包/文档) ← 依赖 Phase 2-7
```

## 工作量估算

| Phase | 任务数 | 估算 |
|-------|--------|------|
| Phase 1: 基础设施 | 6 | 1 周 |
| Phase 2: 制造业知识模型 | 5 | 1 周 |
| Phase 3: 核心链路 | 7 | 1.5 周 |
| Phase 4: 搜索服务 | 4 | 1 周 |
| Phase 5: 桌面应用 | 6 | 1.5 周 |
| Phase 6: 冷启动 | 5 | 1 周 |
| Phase 7: 知识分析 | 5 | 1 周 |
| Phase 8: 测试/打包/文档 | 8 | 1.5 周 |
| **总计** | **46** | **9.5 周** |

## P0/P1/P2 优先级

### P0 — 没有这些就不是产品（Phase 1-4）
- 基础设施（Redis/Meilisearch/Qdrant/Worker）
- 制造业知识模型（5 种文档类型）
- 核心链路自动化（端到端）
- 搜索服务（混合搜索 + RAG + 权限过滤）

### P1 — 产品体验（Phase 5-6）
- 桌面应用重写（文件监控/通知/离线/一键初始化）
- 冷启动（示例文档/批量导入/向导）

### P2 — 差异化（Phase 7）
- 知识分析仪表盘
- 知识缺口分析
- 智能推荐
- 学习路径

### P3 — 企业级（Phase 8）
- 跨平台打包
- 测试与文档
- 生产部署
