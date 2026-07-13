import type { Agent, Capsule, PagedResponse, RAGItem, RAGChunk, RAGChatResponse, ProviderModels, Skill, SkillCatalogEntry } from "./types";

export const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
export const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8001";

async function throwOnError(res: Response): Promise<void> {
  if (res.ok) return;
  let detail = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {}
  throw new Error(detail);
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  await throwOnError(res);
  return res.json();
}

async function del_(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE", credentials: "include" });
  await throwOnError(res);
}

async function upload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", credentials: "include", body: formData });
  await throwOnError(res);
  return res.json();
}

export const api = {
  // Agents
  listAgents: (q?: string, page = 1, page_size = 20) => {
    const p = new URLSearchParams({ page: String(page), page_size: String(page_size) });
    if (q) p.set("q", q);
    return req<PagedResponse<Agent>>(`/agents/?${p}`);
  },
  getAgent: (id: string) => req<Agent>(`/agents/agent-config/${id}`),
  createAgent: (data: Record<string, unknown>) =>
    req<Agent>("/agents/", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: string, patch: Record<string, unknown>) =>
    req<Agent>(`/agents/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteAgent: (id: string) => del_(`/agents/${id}`),
  cloneAgent: (id: string) => req<Agent>(`/agents/${id}/clone`, { method: "POST" }),
  myAgentAccess: (id: string) => req<{ access: string }>(`/agents/${id}/my-access`),
  listTraces: (agentId: string) => req<Record<string, unknown>[]>(`/agents/${agentId}/traces`),
  getTrace: (agentId: string, traceId: string) =>
    req<Record<string, unknown>>(`/agents/${agentId}/traces/${traceId}`),

  // RAG
  listRags: (q?: string, page = 1, page_size = 20) => {
    const p = new URLSearchParams({ page: String(page), page_size: String(page_size) });
    if (q) p.set("q", q);
    return req<PagedResponse<RAGItem>>(`/rags/?${p}`);
  },
  getRag: (id: string) => req<RAGItem>(`/rags/${id}`),
  createRag: (data: Record<string, unknown>) =>
    req<RAGItem>("/rags/", { method: "POST", body: JSON.stringify(data) }),
  deleteRag: (id: string) => del_(`/rags/${id}`),
  listChunks: (ragId: string) => req<RAGChunk[]>(`/rags/${ragId}/data`),
  insertText: (ragId: string, data: Record<string, unknown>) =>
    req<{ chunks_created: number; chunks: RAGChunk[] }>(`/rags/${ragId}/data/text`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  insertFile: (ragId: string, formData: FormData) =>
    upload<{ chunks_created: number; chunks: RAGChunk[] }>(`/rags/${ragId}/data/files`, formData),
  queryRag: (ragId: string, data: Record<string, unknown>) =>
    req<RAGChatResponse>(`/rags/${ragId}/chat`, { method: "POST", body: JSON.stringify(data) }),

  // LLM info
  listProviders: () => req<ProviderModels[]>("/llm-info/providers"),

  // Auth
  login: (email: string, password: string) =>
    req<{ id: string; email: string; name: string; role: string }>("/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () =>
    req<{ id: string; email: string; name: string; role: string; credits_limit: number; credits_used: number }>("/auth/me"),

  // Credits
  myBalance: () =>
    req<{ credits_limit: number; credits_used: number; credits_period: string; next_reset_at: number; percent_used: number }>("/credits/me"),
  myUsage: (days = 30) => req<Record<string, unknown>>(`/credits/usage?days=${days}`),
  allUsage: (days = 30) => req<Record<string, unknown>>(`/credits/admin/usage?days=${days}`),
  modelCatalog: () => req<Record<string, unknown>[]>("/credits/catalog"),

  // Admin users
  listUsers: () => req<Record<string, unknown>[]>("/admin/users/"),
  createUser: (data: Record<string, unknown>) =>
    req<Record<string, unknown>>("/admin/users/", { method: "POST", body: JSON.stringify(data) }),
  updateUserCredits: (id: string, credits_limit: number, credits_period: string) =>
    req<{ ok: boolean }>(`/admin/users/${id}/credits`, {
      method: "PATCH", body: JSON.stringify({ credits_limit, credits_period }),
    }),
  deactivateUser: (id: string) => del_(`/admin/users/${id}`),

  // Skills
  listSkillsCatalog: (q?: string, page = 1, page_size = 10) => {
    const p = new URLSearchParams({ page: String(page), page_size: String(page_size) });
    if (q) p.set("q", q);
    return req<PagedResponse<SkillCatalogEntry>>(`/skills/catalog?${p}`);
  },
  listSkills: (q?: string, page = 1, page_size = 100) => {
    const p = new URLSearchParams({ page: String(page), page_size: String(page_size) });
    if (q) p.set("q", q);
    return req<PagedResponse<Skill>>(`/skills/?${p}`);
  },
  getSkill: (id: string) => req<Skill>(`/skills/${id}`),
  createSkill: (data: { name: string; description: string; content: string; github_url?: string }) =>
    req<Skill>("/skills/", { method: "POST", body: JSON.stringify(data) }),
  updateSkill: (id: string, data: { name?: string; description?: string; content?: string }) =>
    req<Skill>(`/skills/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSkill: (id: string) => del_(`/skills/${id}`),
  importSkillFromGithub: (url: string) =>
    req<Skill>("/skills/fetch-github", { method: "POST", body: JSON.stringify({ url }) }),

  // Capsules
  listCapsules: (params?: { session_id?: string; agent_id?: string }) => {
    const p = new URLSearchParams();
    if (params?.session_id) p.set("session_id", params.session_id);
    if (params?.agent_id) p.set("agent_id", params.agent_id);
    return req<Capsule[]>(`/capsules/?${p}`);
  },
  getCapsule: (id: string) => req<Capsule>(`/capsules/${id}`),
  deleteCapsule: (id: string) => del_(`/capsules/${id}`),
  refreshCapsuleUrl: (id: string) => req<{ file_url: string }>(`/capsules/${id}/refresh-url`, { method: "POST" }),

  // Shares
  listShares: (type: "agent" | "rag", id: string) =>
    req<{ id: string; email: string; access: string }[]>(`/shares/${type}/${id}`),
  createShare: (type: "agent" | "rag", id: string, email: string, access: "read" | "write") =>
    req<{ id: string; email: string; access: string }>(`/shares/${type}/${id}`, {
      method: "POST", body: JSON.stringify({ email, access }),
    }),
  revokeShare: (type: "agent" | "rag", id: string, shareId: string) =>
    del_(`/shares/${type}/${id}/${shareId}`),
};
