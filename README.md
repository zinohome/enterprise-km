# 企业知识管理平台 (Enterprise KM)

面向制造业的 AI 原生知识管理平台，私有部署，数据不出域。

## 产品定位

**一句话：** 制造业工程师写完报告自动归档，遇到故障 5 秒搜到历史方案。

**差异化：**
- 制造业知识模型（FA 报告/ECN/工艺规范/质检标准/SOP）
- AI 自动提取结构化字段 + 知识图谱关联
- 混合搜索（全文 + 向量）+ RAG 问答
- 桌面应用一键安装，文件自动同步

## 架构

```
员工电脑                              企业服务器
┌──────────────────────────┐       ┌──────────────────────────────┐
│  桌面应用 (Tauri + Rust)   │       │  nginx :443                   │
│  ├ 文件监控 (notify-rs)   │       │  ├ Server :5056 (认证/策展)    │
│  ├ rclone 自动同步        │  HTTPS│  ├ Search :5059 (混合搜索+RAG) │
│  ├ 系统托盘 + 原生通知    │ ────→ │  ├ Classifier :5057 (AI分类)  │
│  └ 联邦搜索               │       │  ├ Analytics :5060 (知识分析)  │
│                           │       │  ├ Worker (RQ 异步任务)        │
│  Open Notebook :5055      │       │  ├ Meilisearch :7700 (全文)    │
│  SurrealDB :8001          │       │  ├ Qdrant :6333 (向量)         │
└──────────────────────────┘       │  ├ Redis :6379 (队列)          │
                                    │  ├ MinIO :9000 (文档存储)      │
                                    │  └ SurrealDB :8000 (元数据)    │
                                    └──────────────────────────────┘
```

## 核心链路

```
文件保存 → notify检测(5s) → rclone同步 → MinIO webhook
→ Worker解析 → AI识别类型 → 提取字段 → 向量化(bge-m3)
→ 分类(Ollama) → 知识图谱关联 → 审核队列
→ 管理员通过 → 发布到Meilisearch+Qdrant → 全员可搜索
```

## 快速开始

### 服务端部署

```bash
# 1. 克隆仓库
git clone git@github.com:zinohome/enterprise-km.git
cd enterprise-km

# 2. 启动所有服务
docker compose up -d

# 3. 验证
curl http://localhost:5056/health
curl http://localhost:5059/health
curl http://localhost:5060/health
```

### 桌面应用安装

```bash
# Linux
sudo dpkg -i 企业知识管理_0.2.0_amd64.deb

# 首次启动自动初始化（rclone + SurrealDB 预置，Open Notebook 在线安装）
```

## 服务列表

| 服务 | 端口 | 用途 |
|------|------|------|
| Server | 5056 | 认证、用户、团队、策展、知识图谱 |
| Classifier | 5057 | AI 分类、MinIO webhook |
| Search | 5059 | Meilisearch + Qdrant 混合搜索 + RAG 问答 |
| Analytics | 5060 | 知识仪表盘、缺口分析、学习路径 |
| Worker | — | RQ 异步任务（解析/向量化/分类/发布） |
| Redis | 6379 | 任务队列 + 缓存 |
| Meilisearch | 7700 | 全文搜索 |
| Qdrant | 6333 | 向量搜索 |
| MinIO | 9000/9001 | 文档存储 |
| SurrealDB | 8000 | 元数据 + 知识图谱 |

## 制造业知识模型

| 类型 | 结构化字段 | 关联 |
|------|-----------|------|
| FA 报告 | 现象、根因、措施、零件号、产线 | 同类故障、关联 ECN、参考 SOP |
| ECN | 变更原因、影响范围、审批记录 | 关联零件、关联 FA |
| 工艺规范 | 工艺参数、适用产品、版本历史 | 关联质检标准、关联 SOP |
| 质检标准 | 检测方法、合格标准、抽样方案 | 关联工艺规范 |
| SOP | 操作步骤、注意事项、所需工具 | 关联故障案例、关联工艺规范 |

## 技术栈

- **后端:** Python 3.12 + FastAPI + SurrealDB
- **搜索:** Meilisearch + Qdrant + bge-m3
- **AI:** Ollama (qwen2.5:7b + bge-m3)
- **桌面:** Tauri 2 + Rust + Next.js
- **存储:** MinIO (S3 兼容)
- **任务队列:** Redis + RQ
- **部署:** Docker Compose + systemd + nginx

## 测试

```bash
# v0.2 测试 (16 passed, 3 skipped)
pytest server/tests/test_v2_e2e.py -v

# v0.1 回归测试 (78 passed)
pytest server/tests/test_unit_extended.py server/tests/test_api.py -v
```

## 路线图

- [x] v0.1 — 技术原型，验证可行性
- [x] v0.2 — 产品重建，制造业垂直场景，端到端可用
- [ ] v0.3 — 知识分析仪表盘、SSO/LDAP、高可用
- [ ] v0.4 — 多企业租户、知识图谱可视化、智能推荐
- [ ] v1.0 — 企业版正式发布

## 商业模式

**Open Core：**
- 社区版（开源免费）：核心功能、单机部署
- 企业版（付费）：高可用、SSO/LDAP、审计合规、专属支持

## License

Apache 2.0
