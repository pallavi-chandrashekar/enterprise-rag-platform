export type KnowledgeBase = {
  id: string;
  name: string;
  description?: string | null;
};

export type RAGSource = {
  document_id: string;
  chunk_id: string;
  content: string;
  chunk_metadata?: Record<string, unknown>;
};

type TokenResponse = {
  token: string;
  tenant_id: string;
  tenant_name: string;
  expires_at: string;
};

const API_BASE = window.location.origin;

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = options.headers ? { ...(options.headers as Record<string, string>) } : {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = (data as { detail?: string } | null)?.detail || res.statusText || "Request failed";
    throw new Error(detail);
  }
  return data as T;
}

export const api = {
  issueToken: (tenantName: string) =>
    request<TokenResponse>(
      "/auth/token",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_name: tenantName }),
      },
      undefined
    ),

  listKBs: (token: string) => request<KnowledgeBase[]>("/kb", { method: "GET" }, token),

  createKB: (token: string, name: string, description?: string | null) =>
    request<KnowledgeBase>(
      "/kb",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: description || null }),
      },
      token
    ),

  deleteKB: (token: string, id: string) => request<void>(`/kb/${id}`, { method: "DELETE" }, token),

  ingestFile: (token: string, kbId: string, file: File, metadata?: string) => {
    const form = new FormData();
    form.append("kb_id", kbId);
    form.append("file", file);
    if (metadata) form.append("metadata", metadata);
    return request("/ingest", { method: "POST", body: form }, token);
  },

  ingestUrl: (token: string, kbId: string, url: string) =>
    request("/ingest_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kb_id: kbId, url }),
    }, token),

  query: (token: string, payload: {
    kb_id: string;
    query: string;
    top_k: number;
    max_tokens: number;
    use_rerank: boolean;
    search_type: string;
  }) =>
    request<{ answer: string; sources: RAGSource[]; latency_ms: number }>(
      "/rag/query",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      token
    ),
};
