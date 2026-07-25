"use client";

import { useEffect, useState } from "react";
import { auth, categories, users, approvals } from "@/lib/api";

export default function AdminPage() {
  const [user, setUser] = useState<Record<string, unknown> | null>(null);
  const [tab, setTab] = useState<"users" | "categories" | "approvals" | "audit">("users");
  const [userList, setUserList] = useState<Array<Record<string, unknown>>>([]);
  const [catList, setCatList] = useState<Array<Record<string, unknown>>>([]);
  const [approvalList, setApprovalList] = useState<Array<Record<string, unknown>>>([]);
  const [auditLogs, setAuditLogs] = useState<Array<Record<string, unknown>>>([]);
  const [newCatName, setNewCatName] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPass, setNewUserPass] = useState("");
  const [newUserDisplay, setNewUserDisplay] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { window.location.href = "/login"; return; }
    auth.me().then(setUser).catch(() => { localStorage.removeItem("token"); window.location.href = "/login"; });
  }, []);

  useEffect(() => {
    if (!user || (user.role as string) !== "admin") return;
    users.list().then(setUserList).catch(() => {});
    categories.list().then(setCatList).catch(() => {});
    approvals.list().then(setApprovalList).catch(() => {});
  }, [user, tab]);

  const loadAudit = async () => {
    const token = localStorage.getItem("token");
    const res = await fetch("http://192.168.66.40:5056/audit", { headers: { Authorization: `Bearer ${token}` } });
    setAuditLogs(await res.json());
  };

  const createCategory = async () => {
    if (!newCatName) return;
    await categories.create({ name: newCatName });
    setNewCatName("");
    categories.list().then(setCatList);
  };

  const createUser = async () => {
    if (!newUserName || !newUserEmail || !newUserPass) return;
    await auth.register({ username: newUserName, email: newUserEmail, password: newUserPass, display_name: newUserDisplay || newUserName });
    setNewUserName(""); setNewUserEmail(""); setNewUserPass(""); setNewUserDisplay("");
    users.list().then(setUserList);
  };

  const handleApprove = async (id: string) => {
    await approvals.approve(id, "已审核通过");
    approvals.list().then(setApprovalList);
  };

  const handleReject = async (id: string) => {
    await approvals.reject(id, "已退回");
    approvals.list().then(setApprovalList);
  };

  if (!user || (user.role as string) !== "admin") return <div style={{ padding: 40 }}>需要管理员权限</div>;

  const tabs = [
    { key: "users", label: "用户管理" },
    { key: "categories", label: "分类管理" },
    { key: "approvals", label: "审批管理" },
    { key: "audit", label: "审计日志" },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>管理后台</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {tabs.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key as typeof tab); if (t.key === "audit") loadAudit(); }} style={{ padding: "8px 16px", border: tab === t.key ? "2px solid #1677ff" : "1px solid #ddd", borderRadius: 4, background: tab === t.key ? "#e6f4ff" : "white", cursor: "pointer" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "users" && (
        <div>
          <h3>创建用户</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input placeholder="用户名" value={newUserName} onChange={(e) => setNewUserName(e.target.value)} style={{ padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            <input placeholder="邮箱" value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} style={{ padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            <input placeholder="密码" type="password" value={newUserPass} onChange={(e) => setNewUserPass(e.target.value)} style={{ padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            <input placeholder="显示名" value={newUserDisplay} onChange={(e) => setNewUserDisplay(e.target.value)} style={{ padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            <button onClick={createUser} style={{ padding: "6px 16px", background: "#1677ff", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>创建</button>
          </div>
          <h3>用户列表 ({userList.length})</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ background: "#f5f5f5" }}><th style={{ padding: 8, textAlign: "left" }}>用户名</th><th style={{ padding: 8, textAlign: "left" }}>显示名</th><th style={{ padding: 8, textAlign: "left" }}>角色</th><th style={{ padding: 8, textAlign: "left" }}>邮箱</th></tr></thead>
            <tbody>{userList.map((u) => <tr key={u.id as string} style={{ borderBottom: "1px solid #eee" }}><td style={{ padding: 8 }}>{u.username as string}</td><td style={{ padding: 8 }}>{u.display_name as string}</td><td style={{ padding: 8 }}>{u.role as string}</td><td style={{ padding: 8 }}>{u.email as string}</td></tr>)}</tbody>
          </table>
        </div>
      )}

      {tab === "categories" && (
        <div>
          <h3>创建分类</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input placeholder="分类名称" value={newCatName} onChange={(e) => setNewCatName(e.target.value)} style={{ padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            <button onClick={createCategory} style={{ padding: "6px 16px", background: "#1677ff", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>创建</button>
          </div>
          <h3>分类列表 ({catList.length})</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ background: "#f5f5f5" }}><th style={{ padding: 8, textAlign: "left" }}>名称</th><th style={{ padding: 8, textAlign: "left" }}>描述</th><th style={{ padding: 8, textAlign: "left" }}>操作</th></tr></thead>
            <tbody>{catList.map((c) => <tr key={c.id as string} style={{ borderBottom: "1px solid #eee" }}><td style={{ padding: 8 }}>{c.name as string}</td><td style={{ padding: 8 }}>{(c.description as string) || "-"}</td><td style={{ padding: 8 }}><button onClick={() => categories.delete(c.id as string).then(() => categories.list().then(setCatList))} style={{ color: "#ff4d4f", border: "none", background: "none", cursor: "pointer" }}>删除</button></td></tr>)}</tbody>
          </table>
        </div>
      )}

      {tab === "approvals" && (
        <div>
          <h3>待审批 ({approvalList.length})</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ background: "#f5f5f5" }}><th style={{ padding: 8, textAlign: "left" }}>文档ID</th><th style={{ padding: 8, textAlign: "left" }}>提交者</th><th style={{ padding: 8, textAlign: "left" }}>状态</th><th style={{ padding: 8, textAlign: "left" }}>操作</th></tr></thead>
            <tbody>{approvalList.map((a) => <tr key={a.id as string} style={{ borderBottom: "1px solid #eee" }}><td style={{ padding: 8 }}>{a.source_id as string}</td><td style={{ padding: 8 }}>{a.submitter_id as string}</td><td style={{ padding: 8 }}><span style={{ color: (a.status as string) === "approved" ? "#52c41a" : (a.status as string) === "rejected" ? "#ff4d4f" : "#faad14" }}>{a.status as string}</span></td><td style={{ padding: 8 }}>{(a.status as string) === "pending" ? <><button onClick={() => handleApprove(a.id as string)} style={{ marginRight: 8, color: "#52c41a", border: "none", background: "none", cursor: "pointer" }}>批准</button><button onClick={() => handleReject(a.id as string)} style={{ color: "#ff4d4f", border: "none", background: "none", cursor: "pointer" }}>退回</button></> : "-"}</td></tr>)}</tbody>
          </table>
        </div>
      )}

      {tab === "audit" && (
        <div>
          <h3>审计日志 ({auditLogs.length})</h3>
          <pre style={{ background: "#f5f5f5", padding: 16, borderRadius: 4, maxHeight: 400, overflow: "auto" }}>{JSON.stringify(auditLogs, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
