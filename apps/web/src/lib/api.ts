/* ─── DeepDocs API 客户端 ─── */

const API_BASE = "/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API Error ${res.status}`);
  }

  return res.json();
}

// ─── 认证 ───
export const auth = {
  register: (data: { email: string; username: string; password: string }) =>
    request<{ access_token: string; user: any }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  login: (data: { username: string; password: string }) =>
    request<{ access_token: string; user: any }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  me: () => request<any>("/auth/me"),
};

// ─── 工作区 / 项目 ───
export const projects = {
  list: () => request<any[]>("/workspaces"),
  get: (id: string) => request<any>(`/workspaces/${id}`),
  create: (data: { name: string; description?: string }) =>
    request<any>("/workspaces", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/workspaces/${id}`, { method: "DELETE" }),
};

// ─── 知识库 ───
export const kb = {
  list: (workspaceId?: string) =>
    request<any[]>(`/knowledge-bases${workspaceId ? `?workspace_id=${workspaceId}` : ""}`),
  get: (id: string) => request<any>(`/knowledge-bases/${id}`),
  create: (data: { workspace_id: string; name: string; description?: string }) =>
    request<any>("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/knowledge-bases/${id}`, { method: "DELETE" }),
};

// ─── 文档 ───
export const documents = {
  list: (kbId: string, status?: string) =>
    request<any[]>(`/knowledge-bases/${kbId}/documents${status ? `?status_filter=${status}` : ""}`),
  get: (kbId: string, docId: string) =>
    request<any>(`/knowledge-bases/${kbId}/documents/${docId}`),
  upload: async (kbId: string, file: File) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    return res.json();
  },
  delete: (kbId: string, docId: string) =>
    request<void>(`/knowledge-bases/${kbId}/documents/${docId}`, { method: "DELETE" }),
};

// ─── 分析（问答/总结/比较/抽取） ───
export const analysis = {
  chat: (kbId: string, data: {
    question: string;
    mode?: string;
    model?: string;
    top_k?: number;
    stream?: boolean;
  }) => {
    const token = localStorage.getItem("token");
    return fetch(`${API_BASE}/knowledge-bases/${kbId}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
    });
  },
  summary: (kbId: string, docIds?: string[]) =>
    request<any>(`/knowledge-bases/${kbId}/summary`, {
      method: "POST",
      body: JSON.stringify({ doc_ids: docIds }),
    }),
};
