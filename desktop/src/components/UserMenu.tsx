"use client";

import { useState, useRef, useEffect } from "react";

interface UserMenuProps {
  user: { display_name: string; role: string; avatar_url?: string };
  onLogout: () => void;
}

export default function UserMenu({ user, onLogout }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <div onClick={() => setOpen(!open)} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", padding: "4px 8px", borderRadius: 4, background: open ? "#f0f0f0" : "transparent" }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1677ff", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
          {user.display_name[0]}
        </div>
        <span>{user.display_name}</span>
        <span style={{ fontSize: 12 }}>▼</span>
      </div>
      {open && (
        <div style={{ position: "absolute", right: 0, top: 44, background: "white", border: "1px solid #eee", borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", minWidth: 180, zIndex: 100 }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #eee" }}>
            <div style={{ fontWeight: 600 }}>{user.display_name}</div>
            <div style={{ fontSize: 12, color: "#999" }}>{user.role}</div>
          </div>
          <div style={{ padding: 4 }}>
            <div style={{ padding: "8px 12px", cursor: "pointer", borderRadius: 4 }} onClick={() => { setOpen(false); }}>个人设置</div>
            <div style={{ padding: "8px 12px", cursor: "pointer", borderRadius: 4, color: "#ff4d4f" }} onClick={() => { setOpen(false); onLogout(); }}>退出登录</div>
          </div>
        </div>
      )}
    </div>
  );
}
