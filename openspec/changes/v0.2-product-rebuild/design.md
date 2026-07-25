# Design: v0.2 产品重建

## 一、核心架构决策

### 决策 1：放弃改造 Open Notebook，改为"嵌入 + 代理"模式

**问题：** v0.1 试图给 Open Notebook 加 `owner_id` / `visibility` 字段，但 Open Notebook 的搜索、问答、笔记功能完全不认这些字段。

**方案：**
- **本地 Open Notebook**：保持原样，作为员工个人知识库。桌面应用内嵌其前端（webview 加载 localhost:5055）。
- **企业知识库**：完全自建，不再使用 Open Notebook 实例。
- **联邦搜索**：桌面应用同时查询本地 Open Notebook API（个人知识库）和企业搜索服务 API（企业知识库），合并结果展示。

**代价：** 放弃 Open Notebook 的 AI 问答能力用于企业知识库，需要自建 RAG。

### 决策 2：自建企业知识库引擎

| 组件 | 选型 | 原因 |
|------|------|------|
| 全文搜索 | Meilisearch | 单文件部署，中文分词（jieba），< 50MB 内存，API 简洁 |
| 向量搜索 | Qdrant | Rust 编写，高性能，支持 payload 过滤（权限） |
| 文档存储 | MinIO (已有) | S3 兼容，已有部署 |
| 元数据存储 | SurrealDB (已有) | 已有部署，原生支持图查询（知识图谱） |
| 任务队列 | Redis + RQ | 轻量，Python 原生，足够当前规模 |
| AI 推理 | Ollama (已有) | 已有部署，本地推理，数据不出域 |

### 决策 3：制造业知识模型

为制造业 5 种核心知识类型设计专用数据模型：

```surrealql
-- 故障分析报告
DEFINE TABLE fa_report SCHEMAFULL;
DEFINE FIELD phenomenon ON fa_report TYPE string;      -- 现象
DEFINE FIELD root_cause ON fa_report TYPE string;       -- 根因
DEFINE FIELD solution ON fa_report TYPE string;         -- 措施
DEFINE FIELD part_number ON fa_report TYPE string;      -- 零件号
DEFINE FIELD production_line ON fa_report TYPE string;  -- 产线
DEFINE FIELD equipment ON fa_report TYPE string;        -- 设备
DEFINE FIELD related_ecn ON fa_report TYPE array;       -- 关联 ECN
DEFINE FIELD similar_faults ON fa_report TYPE array;    -- 类似故障

-- 工程变更通知
DEFINE TABLE ecn SCHEMAFULL;
DEFINE FIELD change_reason ON ecn TYPE string;
DEFINE FIELD impact_scope ON ecn TYPE string;
DEFINE FIELD approval_chain ON ecn TYPE array;
DEFINE FIELD effective_date ON ecn TYPE datetime;
DEFINE FIELD related_parts ON ecn TYPE array;
DEFINE FIELD related_fa ON ecn TYPE array;

-- 工艺规范
DEFINE TABLE process_spec SCHEMAFULL;
DEFINE FIELD parameters ON process_spec TYPE object;
DEFINE FIELD applicable_products ON process_spec TYPE array;
DEFINE FIELD version_history ON process_spec TYPE array;
DEFINE FIELD related_quality_standards ON process_spec TYPE array;
DEFINE FIELD related_sops ON process_spec TYPE array;

-- 质检标准
DEFINE TABLE quality_standard SCHEMAFULL;
DEFINE FIELD test_method ON quality_standard TYPE string;
DEFINE FIELD acceptance_criteria ON quality_standard TYPE string;
DEFINE FIELD sampling_plan ON quality_standard TYPE string;
DEFINE FIELD related_process_specs ON quality_standard TYPE array;

-- 标准操作流程
DEFINE TABLE sop SCHEMAFULL;
DEFINE FIELD steps ON sop TYPE array;
DEFINE FIELD precautions ON sop TYPE array;
DEFINE FIELD required_tools ON sop TYPE array;
DEFINE FIELD related_faults ON sop TYPE array;
DEFINE FIELD related_process_specs ON sop TYPE array;
```

### 决策 4：知识图谱

利用 SurrealDB 的图查询能力，构建文档间关联：

```
FA-2024-001 (注塑缩痕)
  ├── → 关联零件 → P/N 12345
  ├── → 关联产线 → Line 3
  ├── → 关联ECN → ECN-2024-056
  ├── → 类似故障 → FA-2023-089, FA-2024-012
  └── → 参考SOP → SOP-Injection-03

P/N 12345
  ├── → 涉及ECN → ECN-2024-056, ECN-2024-012
  ├── → 涉及FA → FA-2024-001, FA-2023-089
  └── → 相关SOP → SOP-Injection-03
```

图查询示例：
```surrealql
-- 查询某个零件的完整变更历史
SELECT * FROM ecn WHERE related_parts CONTAINS "P/N 12345";

-- 查询某个故障的所有关联信息
SELECT *, ->related->* FROM fa_report WHERE id = "FA-2024-001";
```

### 决策 5：桌面应用重写

将核心逻辑从 Next.js 前端移到 Rust 后端：

```
v0.1:  Tauri(壳) → Next.js(网页) → 手动操作
v0.2:  Tauri(壳) → Rust 后端(文件监控/同步/通知/离线) → Next.js(UI only)
```

**Rust 后端新增能力：**

| 能力 | 实现 | 依赖 |
|------|------|------|
| 文件系统监控 | 实时监控同步目录变更 | `notify` crate (跨平台) |
| 自动同步 | 检测到变更 → 调用 rclone sync | 已有 rclone.rs |
| 原生通知 | 同步完成/新知识入库/审批 | `tauri-plugin-notification` |
| 离线检测 | 监听网络状态变化 | Tauri network API |
| 一键初始化 | 首次启动自动安装所有依赖 | 已有 services.rs |

### 决策 6：冷启动方案

不只是模板，而是完整的"5 分钟看到价值"体验：

1. **行业知识模型预设**：制造业分类树、标签体系、关联规则
2. **50+ 示例文档**：基于博世真实场景
3. **批量导入工具**：从 SharePoint/文件服务器导入
4. **AI 辅助录入**：上传文档 → AI 自动提取结构化字段
5. **快速开始向导**：5 步引导

### 决策 7：跨平台打包

GitHub Actions 三平台构建：

```yaml
strategy:
  matrix:
    os: [ubuntu-22.04, macos-14, windows-2022]
    include:
      - os: ubuntu-22.04 → .deb + .rpm + .AppImage
      - os: macos-14 → .dmg
      - os: windows-2022 → .msi
```

安装包内容：Tauri 二进制 + rclone 二进制 + SurrealDB 二进制 + setup 脚本。

## 二、架构图

```
┌─ 员工电脑 ──────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    桌面应用 (Tauri + Rust)                      │  │
│  │                                                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │  │
│  │  │ 文件监控  │  │ rclone   │  │ 系统托盘  │  │ 原生通知      │ │  │
│  │  │ (notify) │  │ 自动同步  │  │ 状态/菜单 │  │ 同步/审批     │ │  │
│  │  └────┬─────┘  └────┬─────┘  └──────────┘  └──────────────┘ │  │
│  │       │             │                                         │  │
│  │       │    ┌────────┴────────┐                                │  │
│  │       │    │  联邦搜索       │                                │  │
│  │       │    │ ① localhost    │                                │  │
│  │       │    │ ② /search/*    │                                │  │
│  │       │    └────────┬───────┘                                │  │
│  │       │             │                                         │  │
│  │  ┌────┴─────────────┴──────────────────────────────────────┐ │  │
│  │  │              Next.js 前端 (UI only)                       │ │  │
│  │  │  登录/搜索/知识库/管理/知识图谱/分析                        │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────┐  ┌────────────────────┐                    │
│  │ Open Notebook :5055 │  │ SurrealDB :8001    │                    │
│  │ (个人知识库, 不改)   │  │ (本地元数据)        │                    │
│  └─────────────────────┘  └────────────────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS + JWT
                                    ▼
┌─ 企业服务器 ─────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    nginx :443 (HTTPS + JWT)                      │ │
│  │  /api/* → :5056  /search/* → :5059  /classify/* → :5057         │ │
│  │  /analytics/* → :5060                                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Server :5056 │  │ Search :5059 │  │ Analytics    │               │
│  │ 认证/用户     │  │ Meilisearch  │  │ :5060        │               │
│  │ 团队/策展     │  │ + Qdrant     │  │ 知识仪表盘    │               │
│  │ 同步/通知     │  │ + RAG 问答   │  │ 缺口分析      │               │
│  │ 知识图谱      │  │ + 权限过滤   │  │ 使用统计      │               │
│  └──────┬───────┘  └──────────────┘  └──────────────┘               │
│         │                                                            │
│         │         ┌──────────────┐                                  │
│         ├─────────┤ SurrealDB    │                                  │
│         │         │ :8000        │                                  │
│         │         └──────────────┘                                  │
│         │                                                            │
│  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Classifier   │  │ Worker       │  │ Redis :6379  │               │
│  │ :5057        │  │ 解析/向量化   │  │ 任务队列      │               │
│  │ AI 分类      │  │ 字段提取      │  │ 缓存          │               │
│  │ webhook      │  │ 图谱关联      │  │              │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                                                                       │
│  ┌──────────────┐                                                    │
│  │ MinIO :9000  │                                                    │
│  │ 文档存储      │                                                    │
│  └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

## 三、数据流

### 核心链路数据流

```
1. 员工保存文档到同步目录
2. notify-rs 检测到文件变更
3. rclone sync → MinIO (user_{id}/path/to/file)
4. MinIO webhook → POST /classifier/webhook/minio
5. Classifier 将任务入队 Redis (rq)
6. Worker 从队列取任务:
   a. 从 MinIO 下载文件
   b. 解析文档内容
   c. AI 识别文档类型 (FA/ECN/工艺规范/质检标准/SOP)
   d. AI 提取结构化字段
   e. 调用 bge-m3 生成向量
   f. 调用 Ollama 分类
   g. 构建知识图谱关联
   h. 写入 SurrealDB (status=pending_review)
7. 管理员在后台审核
8. 审核通过 → 发布到 Meilisearch + Qdrant
9. 全员可搜索
```

### 搜索数据流

```
1. 用户在桌面应用输入搜索词
2. 桌面应用并行请求:
   a. GET localhost:5055/api/search?q=xxx (个人知识库)
   b. GET /search/api/search?q=xxx (企业知识库, 带 JWT)
3. 企业搜索服务:
   a. Meilisearch 全文搜索
   b. Qdrant 向量搜索 (bge-m3 embedding)
   c. RRF 合并排序
   d. 按用户权限过滤 (从 JWT 提取 user_id + teams)
   e. 返回结果
4. 桌面应用合并两个结果，展示:
   - "个人知识库" 标签
   - "企业知识库" 标签
```

### AI 问答数据流

```
1. 用户在企业搜索结果中点击"AI 问答"
2. 前端发送: POST /search/api/ask { question, context_doc_ids }
3. 搜索服务:
   a. 从 Qdrant 取 Top-5 相关片段
   b. 构建 prompt: 系统提示 + 上下文 + 用户问题
   c. 调用 Ollama (qwen2.5:7b) 生成回答
   d. 返回: { answer, sources: [{doc_title, excerpt, doc_id}] }
```

## 四、技术选型对比

| 组件 | v0.1 | v0.2 | 原因 |
|------|------|------|------|
| 企业知识库 | Open Notebook 实例 | Meilisearch + Qdrant | 可控权限、轻量、API 简洁 |
| 知识模型 | 通用文档 | 制造业 5 种类型 | 垂直深度是护城河 |
| 知识关联 | 无 | SurrealDB 图查询 | 知识图谱是差异化能力 |
| 任务队列 | 无 | Redis + RQ | 轻量、Python 原生 |
| 文件监控 | 无 | notify-rs | Rust 跨平台、成熟 |
| 原生通知 | 无 | tauri-plugin-notification | Tauri 官方插件 |
| 离线检测 | 无 | Tauri network API | 内置能力 |
| Open Notebook | 改造代码 | 嵌入原版 | 避免上游冲突 |
| 安装包 | 仅 Linux .deb | Mac/Win/Linux | 覆盖目标用户 |
| 冷启动 | 无 | 50+ 示例 + 向导 | 5 分钟看到价值 |
| 知识分析 | 无 | 仪表盘 + 缺口分析 | 管理价值可视化 |

## 五、数据安全架构

博世级别要求：

| 安全层 | 实现 |
|--------|------|
| 传输加密 | HTTPS/TLS 1.3，nginx 终止 |
| 存储加密 | MinIO 服务端加密 (SSE-S3) |
| 认证 | JWT (RS256) + bcrypt 密码哈希 |
| 授权 | 文档级 RBAC (私有/团队/公开) |
| 审计 | 所有操作记录到 audit_log 表，不可篡改 |
| 数据隔离 | MinIO bucket 级别隔离 |
| 备份 | 每日自动备份 SurrealDB + MinIO |
| 合规 | 支持数据导出、数据删除 (GDPR 准备) |

## 六、扩展性设计

| 规模 | 用户数 | 文档数 | 架构 |
|------|--------|--------|------|
| 小型 | < 100 | < 1万 | 单机部署，全部服务在一台机器 |
| 中型 | 100-1000 | 1-10万 | Meilisearch 集群，Qdrant 集群，Worker 多实例 |
| 大型 | 1000+ | 10万+ | 微服务拆分，K8s 部署，CDN 加速 |

v0.2 先做小型，架构预留扩展点：
- Meilisearch 支持多节点集群
- Qdrant 支持分布式部署
- Worker 支持水平扩展
- SurrealDB 支持分布式（v2.x）

## 七、风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| 制造业知识模型设计错误 | 高 | 与博世专家深度访谈，迭代 3 版 |
| AI 分类/字段提取准确率不足 | 高 | 人工审核门禁，置信度阈值，持续优化 prompt |
| 用户不改变工作习惯 | 高 | 文件自动同步，零额外操作；搜索优先于录入 |
| Open Notebook 上游不兼容 | 中 | 锁定版本，CI 自动检测兼容性 |
| Meilisearch 中文分词不够好 | 中 | 配置 jieba 分词器，Meilisearch 原生支持 |
| 竞品快速跟进 | 中 | 制造业垂直深度是护城河，通用平台做不到 |
| 团队规模不足 | 中 | 聚焦 P0，砍掉一切非核心功能 |
