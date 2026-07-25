"use client";

import { useState, useCallback } from "react";

interface SearchResult {
  id: string;
  title: string;
  content?: string;
  score?: number;
  source: "local" | "enterprise";
  type: "source" | "note";
}

export default function FederatedSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "local" | "enterprise">("all");

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);

    const localResults: SearchResult[] = [];
    const enterpriseResults: SearchResult[] = [];

    // Search local Open Notebook
    try {
      const resp = await fetch("http://localhost:5055/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, type: "text", limit: 20 }),
      });
      if (resp.ok) {
        const data = await resp.json();
        (data.results || []).forEach((r: any) => {
          localResults.push({
            id: r.id || r.record_id || "",
            title: r.title || r.name || "Untitled",
            content: r.content || r.full_text || "",
            score: r.score,
            source: "local",
            type: r.content ? "note" : "source",
          });
        });
      }
    } catch {
      // Local Open Notebook not running — that's fine
    }

    // Search enterprise Open Notebook
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const enterpriseUrl = process.env.NEXT_PUBLIC_ENTERPRISE_URL || "https://192.168.66.40";
        const resp = await fetch(`${enterpriseUrl}/enterprise/api/search`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ query, type: "text", limit: 20 }),
        });
        if (resp.ok) {
          const data = await resp.json();
          (data.results || []).forEach((r: any) => {
            enterpriseResults.push({
              id: r.id || r.record_id || "",
              title: r.title || r.name || "Untitled",
              content: r.content || r.full_text || "",
              score: r.score,
              source: "enterprise",
              type: r.content ? "note" : "source",
            });
          });
        }
      } catch {
        // Enterprise unreachable
      }
    }

    setResults([...localResults, ...enterpriseResults]);
    setLoading(false);
  }, [query]);

  const filtered = results.filter((r) => {
    if (activeTab === "all") return true;
    return r.source === activeTab;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Search bar */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="搜索个人知识库 + 企业知识库..."
          className="flex-1 px-4 py-3 border rounded-lg text-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={search}
          disabled={loading}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-lg"
        >
          {loading ? "搜索中..." : "搜索"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b">
        {[
          { key: "all", label: `全部 (${results.length})` },
          { key: "local", label: `个人 (${results.filter((r) => r.source === "local").length})` },
          { key: "enterprise", label: `企业 (${results.filter((r) => r.source === "enterprise").length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === tab.key
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-400">搜索中...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            {query ? "未找到结果" : "输入关键词搜索"}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((r, i) => (
              <div
                key={r.id || i}
                className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                          r.source === "enterprise"
                            ? "bg-purple-100 text-purple-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {r.source === "enterprise" ? "企业" : "个人"}
                      </span>
                      <span className="text-xs text-gray-400">
                        {r.type === "note" ? "笔记" : "文档"}
                      </span>
                      {r.score !== undefined && (
                        <span className="text-xs text-gray-400">
                          相关度: {(r.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold">{r.title}</h3>
                    {r.content && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-3">
                        {r.content.slice(0, 300)}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
