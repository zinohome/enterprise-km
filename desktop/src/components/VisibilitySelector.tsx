"use client";

import { useState } from "react";

interface VisibilitySelectorProps {
  value: string;
  onChange: (v: string) => void;
}

export default function VisibilitySelector({ value, onChange }: VisibilitySelectorProps) {
  const options = [
    { value: "private", label: "🔒 私有", desc: "仅自己可见" },
    { value: "team", label: "👥 团队", desc: "团队成员可见" },
    { value: "public", label: "🌐 公开", desc: "全员可见" },
  ];

  return (
    <div style={{ display: "flex", gap: 8 }}>
      {options.map((opt) => (
        <div
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            padding: "12px 16px",
            border: value === opt.value ? "2px solid #1677ff" : "1px solid #ddd",
            borderRadius: 8,
            cursor: "pointer",
            background: value === opt.value ? "#e6f4ff" : "white",
            flex: 1,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 18, marginBottom: 4 }}>{opt.label}</div>
          <div style={{ fontSize: 12, color: "#999" }}>{opt.desc}</div>
        </div>
      ))}
    </div>
  );
}
