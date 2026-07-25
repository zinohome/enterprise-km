"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SyncSettings from "@/components/SyncSettings";
import KnowledgeBase from "@/components/KnowledgeBase";
import ApprovalManager from "@/components/ApprovalManager";
import NotificationBell from "@/components/NotificationBell";
import UserMenu from "@/components/UserMenu";

interface UserInfo {
  id: string;
  username: string;
  display_name: string;
  role: string;
}

export default function HomePage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [tab, setTab] = useState<string>("knowledge");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  async function loadUser() {
    try {
      const resp = await api("/auth/me");
      if (resp.ok) setUser(await resp.json());
      else if (resp.status === 401) {
        window.location.href = "/login";
        return;
      }
    } catch {
      window.location.href = "/login";
      return;
    }
    setLoading(false);
  }

  function logout() {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }

  if (loading) {
    return <div className="flex items-center justify-center h-screen">加载中...</div>;
  }

  if (!user) {
    return <div className="flex items-center justify-center h-screen">请先登录</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold text-blue-600">企业知识管理</h1>
            <nav className="flex gap-1">
              {[
                { key: "knowledge", label: "知识库" },
                { key: "sync", label: "文件同步" },
                ...(user.role === "admin" || user.role === "manager"
                  ? [{ key: "approvals" as const, label: "审批管理" }]
                  : []),
                ...(user.role === "admin"
                  ? [{ key: "admin" as const, label: "管理后台" }]
                  : []),
              ].map((item) => (
                <button
                  key={item.key}
                  onClick={() => setTab(item.key)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                    tab === item.key
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <NotificationBell />
            <UserMenu user={user} onLogout={logout} />
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "knowledge" && <KnowledgeBase />}
        {tab === "sync" && <SyncSettings />}
        {tab === "approvals" && <ApprovalManager />}
        {tab === "admin" && (
          <iframe src="/admin" className="w-full min-h-[600px] border-0" />
        )}
      </main>
    </div>
  );
}
