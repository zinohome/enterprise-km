"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface SyncConfig {
  directory: string;
  running: boolean;
  lastSync: string;
  fileCount: number;
}

export default function SyncSettings() {
  const [config, setConfig] = useState<SyncConfig>({
    directory: "",
    running: false,
    lastSync: "从未同步",
    fileCount: 0,
  });
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    try {
      const resp = await api("/sync/status");
      if (resp.ok) setConfig(await resp.json());
    } catch {}
  }

  async function selectDirectory() {
    try {
      // @ts-ignore - Tauri API
      const { invoke } = window.__TAURI__;
      const dir = await invoke("pick_directory");
      if (dir) {
        setConfig({ ...config, directory: dir });
        await api("/sync/config", {
          method: "POST",
          body: JSON.stringify({ directory: dir }),
        });
      }
    } catch {
      // Fallback: manual input
      const dir = prompt("请输入同步目录路径:", config.directory);
      if (dir) {
        setConfig({ ...config, directory: dir });
        await api("/sync/config", {
          method: "POST",
          body: JSON.stringify({ directory: dir }),
        });
      }
    }
  }

  async function startSync() {
    setLoading(true);
    setStatus("正在同步...");
    try {
      const resp = await api("/sync/start", { method: "POST" });
      if (resp.ok) {
        setConfig({ ...config, running: true });
        setStatus("同步已启动");
      }
    } catch {
      setStatus("启动失败");
    }
    setLoading(false);
  }

  async function stopSync() {
    setLoading(true);
    try {
      const resp = await api("/sync/stop", { method: "POST" });
      if (resp.ok) {
        setConfig({ ...config, running: false });
        setStatus("同步已停止");
      }
    } catch {
      setStatus("停止失败");
    }
    setLoading(false);
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">文件同步设置</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          同步目录
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={config.directory}
            readOnly
            className="flex-1 px-3 py-2 border rounded bg-gray-50"
            placeholder="未选择目录"
          />
          <button
            onClick={selectDirectory}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            选择目录
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          选择本地文件夹，文件将自动同步到企业知识库
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">同步状态</div>
          <div className={`font-bold ${config.running ? "text-green-600" : "text-gray-600"}`}>
            {config.running ? "运行中" : "已停止"}
          </div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">上次同步</div>
          <div className="font-bold text-gray-600">{config.lastSync}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">已同步文件</div>
          <div className="font-bold text-gray-600">{config.fileCount}</div>
        </div>
      </div>

      <div className="flex gap-2">
        {!config.running ? (
          <button
            onClick={startSync}
            disabled={loading || !config.directory}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {loading ? "启动中..." : "开始同步"}
          </button>
        ) : (
          <button
            onClick={stopSync}
            disabled={loading}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            停止同步
          </button>
        )}
      </div>
      {status && <p className="mt-2 text-sm text-gray-600">{status}</p>}
    </div>
  );
}
