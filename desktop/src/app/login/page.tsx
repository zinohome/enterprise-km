"use client";

import { useState } from "react";
import { auth } from "@/lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await auth.login(username, password);
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      window.location.href = "/";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f5f5f5" }}>
      <form onSubmit={handleLogin} style={{ background: "white", padding: 40, borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.1)", width: 360 }}>
        <h1 style={{ textAlign: "center", marginBottom: 24 }}>企业知识管理</h1>
        {error && <div style={{ color: "red", marginBottom: 12, textAlign: "center" }}>{error}</div>}
        <input type="text" placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: "100%", padding: 10, marginBottom: 12, border: "1px solid #ddd", borderRadius: 4 }} />
        <input type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%", padding: 10, marginBottom: 20, border: "1px solid #ddd", borderRadius: 4 }} />
        <button type="submit" disabled={loading} style={{ width: "100%", padding: 12, background: "#1677ff", color: "white", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 16 }}>
          {loading ? "登录中..." : "登录"}
        </button>
      </form>
    </div>
  );
}
