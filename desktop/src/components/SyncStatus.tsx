"use client";

import { useEffect, useState } from "react";

export default function SyncStatus() {
  const [status, setStatus] = useState<"connected" | "syncing" | "error">("connected");
  const [lastSync, setLastSync] = useState<string>("");
  const [fileCount, setFileCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLastSync(new Date().toLocaleTimeString());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const statusColors = { connected: "#52c41a", syncing: "#1677ff", error: "#ff4d4f" };
  const statusLabels = { connected: "已连接", syncing: "同步中", error: "连接失败" };

  return (
    <div style={{ padding: 16, border: "1px solid #eee", borderRadius: 8, display: "inline-flex", alignItems: "center", gap: 12 }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: statusColors[status], display: "inline-block" }} />
      <span>{statusLabels[status]}</span>
      {lastSync && <span style={{ color: "#999" }}>· 最后同步: {lastSync}</span>}
      <span style={{ color: "#999" }}>· {fileCount} 份文档</span>
    </div>
  );
}
