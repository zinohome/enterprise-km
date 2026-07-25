# 企业知识管理平台 — 管理员手册

## 管理后台

访问桌面应用，使用 admin 账号登录后，左侧导航出现「管理后台」。

### 用户管理

- **创建用户**：输入用户名、邮箱、密码、显示名，点击创建
- **查看用户**：列表显示所有用户及角色
- **修改角色**：通过 API 或数据库修改用户 role 字段

### 知识分类管理

- **创建分类**：输入分类名称，点击创建
- **删除分类**：点击分类行的「删除」按钮
- **分类树**：系统自动构建树形结构

### 审批管理

- **查看待审批**：列表显示所有 pending 状态的审批
- **批准**：点击「批准」，文档自动发布
- **退回**：点击「退回」，填写退回原因

### 审计日志

- 查看所有关键操作记录（登录、创建、编辑、删除、审批）

## 数据库管理

### 连接 SurrealDB

```bash
surreal sql --endpoint ws://localhost:8000 --username root --password root --namespace open_notebook --database open_notebook
```

### 常用查询

```sql
-- 查看所有用户
SELECT * FROM user;

-- 修改用户角色
UPDATE user:xxx SET role = "admin";

-- 查看审批记录
SELECT * FROM approval WHERE status = "pending";

-- 查看审计日志
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 50;
```

## 监控

### Prometheus + Grafana

访问 `http://192.168.66.40:3000` (Grafana)，默认账号 admin/admin。

仪表盘包含：
- API 请求速率
- 活跃用户数
- 文档数量统计

## 备份

### MinIO 数据备份

```bash
rclone sync enterprise-km-minio:enterprise-km /backup/minio/
```

### SurrealDB 备份

```bash
surreal export --endpoint ws://localhost:8000 --username root --password root --namespace open_notebook --database open_notebook backup.surql
```
