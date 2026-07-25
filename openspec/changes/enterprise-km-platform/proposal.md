# Proposal: 企业级知识管理平台

## Motivation

企业知识散落在每个员工的电脑里——技术方案、项目总结、故障分析、培训材料——这些知识随着员工离职而流失，随着时间推移而遗忘。现有的开源方案（如 Open Notebook）是优秀的个人 AI 研究助手，但缺乏多用户协作、权限管理、自动知识汇聚等企业级能力。

本项目的目标：**基于 Open Notebook 核心引擎，构建一个企业级知识管理平台，让员工的知识自动汇聚、自动分类、形成体系化的企业知识库，全员共享使用。**

## Scope

### In Scope

1. **桌面应用**（Tauri + Open Notebook 前端 + rclone 内置）
   - 跨平台（Windows / Mac / Linux）
   - 内置文件同步（本地目录 → MinIO 服务器）
   - 系统托盘、开机自启、自动更新
   - 用户登录、个人知识库、企业知识库

2. **中央服务器**
   - MinIO 统一文件存储
   - Open Notebook 服务端（多用户改造）
   - 自动分类引擎（AI 驱动的知识归类）
   - 企业知识库自动构建

3. **多用户与权限**
   - 用户注册/登录（OIDC 或内置认证）
   - 角色：admin / manager / editor / viewer
   - 知识库权限：私有 / 团队 / 公开
   - 审批发布工作流

4. **自动分类引擎**
   - 文档自动归类到企业知识树
   - 关键词自动提取与打标签
   - 相似文档聚类
   - 知识管理员审核界面

5. **AI 能力**
   - 基于企业知识库的 AI 问答
   - 智能搜索（向量 + 全文）
   - 自动摘要生成
   - 知识关联推荐

### Out of Scope (v1)

- 实时协同编辑
- 外部系统集成（PLM/ERP/APS）
- 移动端应用
- 多语言国际化
- SSO/LDAP 集成（v2）

## Impact

### 新增服务
- `enterprise-km-server` — 中央服务器（FastAPI）
- `enterprise-km-desktop` — 桌面应用（Tauri）
- `enterprise-km-classifier` — 自动分类引擎

### 依赖服务
- MinIO — 文件存储
- SurrealDB — 数据库（继承 Open Notebook）
- Open Notebook — 核心引擎（改造为多用户）

### 改造 Open Notebook
- 加用户表 + 登录 API
- 加权限中间件
- Notebook/Source/Note 模型加 `user_id` / `visibility`
- 前端加登录页 + 用户菜单

## Risks

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| SurrealDB 企业接受度低 | 客户拒绝部署 | 提供 PostgreSQL 迁移方案作为备选 |
| 自动分类准确率不足 | 知识库混乱 | 人工审核门禁 + 置信度阈值 |
| 桌面应用跨平台兼容性 | 部分平台体验差 | Tauri 成熟度已验证，优先 Win/Mac |
| Open Notebook 上游更新冲突 | 改造代码需持续维护 | 最小化改动，尽量不改核心代码 |
| 文件同步可靠性 | 文档丢失或冲突 | rclone 成熟稳定，加冲突检测 |
