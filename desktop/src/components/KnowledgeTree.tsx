"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface TreeNode {
  name: string;
  children: TreeNode[];
  count: number;
}

export default function KnowledgeTree() {
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTree();
  }, []);

  async function loadTree() {
    try {
      const resp = await api("/categories/tree");
      if (resp.ok) {
        const categories = await resp.json();
        // Build tree from flat categories
        const tree = buildTree(categories);
        setTree(tree);
      }
    } catch {}
    setLoading(false);
  }

  function buildTree(categories: any[]): TreeNode[] {
    const map = new Map<string, TreeNode>();
    const roots: TreeNode[] = [];

    categories.forEach((c: any) => {
      map.set(c.id, { name: c.name, children: [], count: c.document_count || 0 });
    });

    categories.forEach((c: any) => {
      const node = map.get(c.id)!;
      if (c.parent_id && map.has(c.parent_id)) {
        map.get(c.parent_id)!.children.push(node);
      } else {
        roots.push(node);
      }
    });

    return roots;
  }

  function renderNode(node: TreeNode, depth: number = 0) {
    return (
      <div key={node.name} style={{ marginLeft: depth * 24 }}>
        <div className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-100 cursor-pointer">
          <span className="text-gray-400">{node.children.length > 0 ? "📁" : "📄"}</span>
          <span className="font-medium">{node.name}</span>
          <span className="text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">
            {node.count}
          </span>
        </div>
        {node.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  if (loading) return <div className="p-4 text-gray-400">加载中...</div>;

  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <h3 className="font-semibold mb-3 text-gray-700">知识分类树</h3>
      {tree.length === 0 ? (
        <p className="text-sm text-gray-400">暂无分类</p>
      ) : (
        tree.map((node) => renderNode(node))
      )}
    </div>
  );
}
