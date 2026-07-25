const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://192.168.66.40:5056";

export async function api(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const auth = {
  login: (username: string, password: string) =>
    api("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (data: { username: string; email: string; password: string; display_name: string }) =>
    api("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  me: () => api("/auth/me"),
};

export const users = {
  list: () => api("/users"),
  get: (id: string) => api(`/users/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => api(`/users/${id}`, { method: "DELETE" }),
};

export const categories = {
  list: () => api("/categories"),
  tree: () => api("/categories/tree"),
  create: (data: { name: string; parent_id?: string; description?: string }) =>
    api("/categories", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    api(`/categories/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => api(`/categories/${id}`, { method: "DELETE" }),
};

export const approvals = {
  list: () => api("/approvals"),
  create: (source_id: string) =>
    api("/approvals", { method: "POST", body: JSON.stringify({ source_id }) }),
  approve: (id: string, comment?: string) =>
    api(`/approvals/${id}/approve`, { method: "POST", body: JSON.stringify({ comment }) }),
  reject: (id: string, comment: string) =>
    api(`/approvals/${id}/reject`, { method: "POST", body: JSON.stringify({ comment }) }),
};
