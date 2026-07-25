"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Doc {
  id: string;
  title: string;
  category: string;
  visibility: string;
  owner_name: string;
  created_at: string;
}

export default function KnowledgeBase() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [stats, setStats] = useState({ total_documents: 0, recent_7d: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStats();
    loadCategories();
    search("");
  }, []);

  async function loadStats() {
    try {
      const resp = await api("/search/stats");
      if (resp.ok) setStats(await resp.json());
    } catch {}
  }

  async function loadCategories() {
    try {
      const resp = await api("/categories");
      if (resp.ok) {
        const data = await resp.json();
        setCategories(data.map((c: any) => c.name));
      }
    } catch {}
  }

  async function search(q: string) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ q: q || "*", limit: "50" });
      if (category) params.set("category", category);
      const resp = await api(`/search?${params}`);
      if (resp.ok) {
        const data = await resp.json();
        setDocs(data.results || []);
      }
    } catch {}
    setLoading(false);
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">企业知识库</h1>
        <div className="flex gap-4 text-sm">
          <span className="px-3 py-1 bg-blue-100 rounded">总文档: {stats.total_documents}</span>
          <span className="px-3 py-1 bg-green-100 rounded">近7天新增: {stats.recent_7d}</span>
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search(query)}
          placeholder="搜索知识库..."
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); search(query); }}
          className="px-4 py-2 border rounded-lg"
        >
          <option value="">全部分类</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={() => search(query)}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          搜索
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">搜索中...</div>
      ) : docs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {query ? "未找到匹配的文档" : "知识库为空，开始同步文件吧"}
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((doc) => (
            <div key={doc.id} className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg">{doc.title}</h3>
                  <div className="flex gap-3 mt-1 text-sm text-gray-500">
                    <span>分类: {doc.category || "未分类"}</span>
                    <span>作者: {doc.owner_name || "未知"}</span>
                    <span>可见: {doc.visibility === "enterprise" ? "全企业" : doc.visibility === "team" ? "团队" : "私有"}</span>
                  </div>
                </div>
                <span className="text-xs text-gray-400">{doc.created_at?.slice(0, 10)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
