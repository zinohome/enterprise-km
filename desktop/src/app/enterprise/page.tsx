"use client";

import { useEffect, useState } from "react";
import { categories } from "@/lib/api";

export default function EnterprisePage() {
  const [tree, setTree] = useState<Array<Record<string, unknown>>>([]);
  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<string | null>(null);

  useEffect(() => {
    categories.tree().then(setTree).catch(() => {});
  }, []);

  const filtered = search
    ? tree.filter((c) => (c.name as string).includes(search))
    : tree;

  return (
    <div style={{ padding: 24 }}>
      <h2>企业知识库</h2>
      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <input
          placeholder="搜索分类..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: "8px 12px", border: "1px solid #ddd", borderRadius: 4, width: 300 }}
        />
      </div>
      <div style={{ display: "flex", gap: 24 }}>
        <aside style={{ width: 250, borderRight: "1px solid #eee", paddingRight: 16 }}>
          <h3>分类树</h3>
          {filtered.map((cat) => (
            <div
              key={cat.id as string}
              onClick={() => setSelectedCat(cat.id as string)}
              style={{
                padding: "8px 12px",
                cursor: "pointer",
                borderRadius: 4,
                background: selectedCat === cat.id ? "#e6f4ff" : "transparent",
                marginBottom: 4,
              }}
            >
              📁 {cat.name as string}
              {(cat.children as Array<Record<string, unknown>>)?.map((child: Record<string, unknown>) => (
                <div key={child.id as string} style={{ paddingLeft: 20, fontSize: 13, color: "#666", marginTop: 4 }}>
                  📄 {child.name as string}
                </div>
              ))}
            </div>
          ))}
        </aside>
        <main style={{ flex: 1 }}>
          {selectedCat ? (
            <div>
              <h3>{(tree.find((c) => c.id === selectedCat)?.name as string) || "分类"}</h3>
              <p style={{ color: "#999" }}>此分类下暂无文档。上传文档后将自动归类。</p>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: 60, color: "#999" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>📚</div>
              <p>选择一个分类浏览知识文档</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
