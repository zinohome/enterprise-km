"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    loadUnread();
    const interval = setInterval(loadUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadUnread() {
    try {
      const resp = await api("/notifications/unread-count");
      if (resp.ok) {
        const data = await resp.json();
        setUnread(data.count);
      }
    } catch {}
  }

  async function loadAll() {
    try {
      const resp = await api("/notifications?limit=20");
      if (resp.ok) setNotifications(await resp.json());
    } catch {}
  }

  async function markRead(id: string) {
    try {
      await api(`/notifications/${id}/read`, { method: "POST" });
      loadUnread();
      loadAll();
    } catch {}
  }

  async function markAllRead() {
    try {
      await api("/notifications/read-all", { method: "POST" });
      loadUnread();
      loadAll();
    } catch {}
  }

  function toggle() {
    if (!open) loadAll();
    setOpen(!open);
  }

  return (
    <div className="relative">
      <button onClick={toggle} className="relative p-2">
        <span className="text-xl">🔔</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50 max-h-96 overflow-y-auto">
          <div className="flex justify-between items-center p-3 border-b">
            <h3 className="font-semibold">通知</h3>
            {unread > 0 && (
              <button onClick={markAllRead} className="text-sm text-blue-500">
                全部已读
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-gray-400">暂无通知</div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                onClick={() => markRead(n.id)}
                className={`p-3 border-b cursor-pointer hover:bg-gray-50 ${!n.read ? "bg-blue-50" : ""}`}
              >
                <div className="font-medium text-sm">{n.title}</div>
                <div className="text-xs text-gray-500 mt-1">{n.message}</div>
                <div className="text-xs text-gray-400 mt-1">{n.created_at?.slice(0, 16)}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
