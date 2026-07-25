"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Approval {
  id: string;
  source_id: string;
  submitter_id: string;
  status: string;
  comment: string;
  created_at: string;
}

export default function ApprovalManager() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadApprovals(); }, []);

  async function loadApprovals() {
    try {
      const resp = await api("/approvals");
      if (resp.ok) setApprovals(await resp.json());
    } catch {}
  }

  async function approve(id: string) {
    setLoading(true);
    try {
      await api(`/approvals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ comment: "已批准" }),
      });
      loadApprovals();
    } catch {}
    setLoading(false);
  }

  async function reject(id: string) {
    const reason = prompt("拒绝原因:");
    if (!reason) return;
    setLoading(true);
    try {
      await api(`/approvals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ comment: reason }),
      });
      loadApprovals();
    } catch {}
    setLoading(false);
  }

  const pending = approvals.filter((a) => a.status === "pending");
  const done = approvals.filter((a) => a.status !== "pending");

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">审批管理</h1>

      {pending.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3 text-orange-600">
            待审批 ({pending.length})
          </h2>
          <div className="space-y-3">
            {pending.map((a) => (
              <div key={a.id} className="p-4 border rounded-lg bg-orange-50">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-medium">文档: {a.source_id}</p>
                    <p className="text-sm text-gray-500">提交时间: {a.created_at?.slice(0, 16)}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => approve(a.id)}
                      disabled={loading}
                      className="px-4 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                    >
                      批准
                    </button>
                    <button
                      onClick={() => reject(a.id)}
                      disabled={loading}
                      className="px-4 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                    >
                      拒绝
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-3">已完成 ({done.length})</h2>
        <div className="space-y-2">
          {done.slice(0, 20).map((a) => (
            <div key={a.id} className="p-3 border rounded-lg flex justify-between">
              <span>{a.source_id}</span>
              <span className={`px-2 py-0.5 rounded text-sm ${
                a.status === "approved" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              }`}>
                {a.status === "approved" ? "已批准" : "已拒绝"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
