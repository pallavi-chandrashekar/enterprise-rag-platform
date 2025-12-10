import { useEffect, useMemo, useState } from "react";
import { api, KnowledgeBase, RAGSource } from "./api";

type Tab = "setup" | "ingest" | "query";

const storageKeys = {
  token: "rag_token",
  tenantId: "rag_tenant_id",
  tenantName: "rag_tenant_name",
};

function App() {
  const [tab, setTab] = useState<Tab>("setup");
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(storageKeys.token));
  const [tenantId, setTenantId] = useState<string | null>(() => localStorage.getItem(storageKeys.tenantId));
  const [tenantName, setTenantName] = useState<string>(() => localStorage.getItem(storageKeys.tenantName) || "");
  const [tenantInput, setTenantInput] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [kbName, setKbName] = useState("");
  const [kbDesc, setKbDesc] = useState("");

  const [ingestKbId, setIngestKbId] = useState("");
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestMeta, setIngestMeta] = useState("");
  const [ingestStatus, setIngestStatus] = useState("");

  const [urlKbId, setUrlKbId] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [urlStatus, setUrlStatus] = useState("");

  const [queryKbId, setQueryKbId] = useState("");
  const [queryText, setQueryText] = useState("");
  const [searchType, setSearchType] = useState("hybrid");
  const [topK, setTopK] = useState(5);
  const [maxTokens, setMaxTokens] = useState(128);
  const [useRerank, setUseRerank] = useState(true);
  const [queryStatus, setQueryStatus] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<RAGSource[]>([]);

  const hasAuth = Boolean(token);
  const readyForActions = hasAuth && kbs.length > 0;
  const activeKbName = useMemo(
    () => kbs.find((kb) => kb.id === queryKbId || ingestKbId || urlKbId)?.name || "None selected",
    [ingestKbId, kbs, queryKbId, urlKbId]
  );

  useEffect(() => {
    if (!token) return;
    fetchKBs();
  }, [token]);

  useEffect(() => {
    const firstKb = kbs[0]?.id || "";
    setIngestKbId((prev) => prev || firstKb);
    setUrlKbId((prev) => prev || firstKb);
    setQueryKbId((prev) => prev || firstKb);
  }, [kbs]);

  async function fetchKBs() {
    if (!token) return;
    try {
      const data = await api.listKBs(token);
      setKbs(data);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed to load KBs");
    }
  }

  async function handleMintToken(e: React.FormEvent) {
    e.preventDefault();
    if (!tenantInput.trim()) return;
    setStatus("Minting token...");
    try {
      const resp = await api.issueToken(tenantInput.trim());
      localStorage.setItem(storageKeys.token, resp.token);
      localStorage.setItem(storageKeys.tenantId, resp.tenant_id);
      localStorage.setItem(storageKeys.tenantName, resp.tenant_name);
      setToken(resp.token);
      setTenantId(resp.tenant_id);
      setTenantName(resp.tenant_name);
      setTenantInput("");
      setStatus("Token saved.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to mint token");
    }
  }

  function handleLogout() {
    setToken(null);
    setTenantId(null);
    setTenantName("");
    localStorage.removeItem(storageKeys.token);
    localStorage.removeItem(storageKeys.tenantId);
    localStorage.removeItem(storageKeys.tenantName);
    setKbs([]);
  }

  async function handleCreateKB(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !kbName.trim()) return;
    setStatus("Creating KB...");
    try {
      await api.createKB(token, kbName.trim(), kbDesc.trim() || null);
      setKbName("");
      setKbDesc("");
      setStatus("KB created");
      fetchKBs();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to create KB");
    }
  }

  async function handleDeleteKB(id: string) {
    if (!token) return;
    if (!confirm("Delete this knowledge base and its documents?")) return;
    setStatus("Deleting KB...");
    try {
      await api.deleteKB(token, id);
      setStatus("KB deleted");
      fetchKBs();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to delete KB");
    }
  }

  async function handleIngestFile(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return setIngestStatus("Sign in first");
    if (!ingestKbId) return setIngestStatus("Pick a KB");
    if (!ingestFile) return setIngestStatus("Choose a file");
    setIngestStatus("Uploading...");
    try {
      await api.ingestFile(token, ingestKbId, ingestFile, ingestMeta.trim() || undefined);
      setIngestStatus("Ingestion started");
      setIngestFile(null);
      setIngestMeta("");
      const ingestFileElement = document.getElementById("ingest-file") as HTMLInputElement | null;
      if (ingestFileElement) {
        ingestFileElement.value = "";
      }
    } catch (err) {
      setIngestStatus(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function handleIngestUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return setUrlStatus("Sign in first");
    if (!urlKbId) return setUrlStatus("Pick a KB");
    if (!urlInput.trim()) return setUrlStatus("Enter a URL");
    setUrlStatus("Submitting...");
    try {
      await api.ingestUrl(token, urlKbId, urlInput.trim());
      setUrlStatus("URL queued for ingestion");
      setUrlInput("");
    } catch (err) {
      setUrlStatus(err instanceof Error ? err.message : "Failed to submit URL");
    }
  }

  async function handleQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return setQueryStatus("Sign in first");
    if (!queryKbId) return setQueryStatus("Pick a KB");
    if (!queryText.trim()) return setQueryStatus("Ask a question");
    setQueryStatus("Querying...");
    setAnswer("");
    setSources([]);
    try {
      const res = await api.query(token, {
        kb_id: queryKbId,
        query: queryText.trim(),
        top_k: topK,
        max_tokens: maxTokens,
        use_rerank: useRerank,
        search_type: searchType,
      });
      setAnswer(res.answer);
      setSources(res.sources || []);
      setQueryStatus(`Answered in ${res.latency_ms} ms`);
    } catch (err) {
      setQueryStatus(err instanceof Error ? err.message : "Query failed");
    }
  }

  const kbOptions = useMemo(
    () =>
      kbs.length
        ? kbs.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))
        : [<option key="none" value="">No KBs available</option>],
    [kbs]
  );

  return (
    <div className="page">
      <header>
        <div>
          <h1>Enterprise RAG Console</h1>
          <div className="muted">Admin panel for tenants, ingestion, and querying</div>
        </div>
        <div className="flex">
          <span className="pill">Multi-tenant</span>
          <span className="pill">Hybrid search</span>
          <a className="pill button-ghost" href="/docs" target="_blank" rel="noreferrer">
            Open API docs
          </a>
        </div>
      </header>

      <div className="banner" style={{ marginTop: 14 }}>
        <div>
          <h3>Status</h3>
          <div className="muted">
            {hasAuth ? `Signed in as ${tenantName || tenantId}` : "Not signed in. Mint a token to start."}
          </div>
        </div>
        <div className="banner-meta">
          <span className="chip">KBs: {kbs.length}</span>
          <span className="chip">Active KB: {activeKbName}</span>
          {!readyForActions && <span className="chip" style={{ color: "var(--danger)" }}>Setup required</span>}
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn ${tab === "setup" ? "active" : ""}`} onClick={() => setTab("setup")}>
          Setup
        </button>
        <button className={`tab-btn ${tab === "ingest" ? "active" : ""}`} onClick={() => setTab("ingest")}>
          Ingest
        </button>
        <button className={`tab-btn ${tab === "query" ? "active" : ""}`} onClick={() => setTab("query")}>
          Query
        </button>
      </div>

      <div className={`tab-panel ${tab === "setup" ? "active" : ""}`}>
        <div className="grid">
          <section className="card">
            <h2>Tenant</h2>
            <form onSubmit={handleMintToken}>
              <label>
                Tenant name
                <input value={tenantInput} onChange={(e) => setTenantInput(e.target.value)} placeholder="acme-inc" required />
              </label>
              <button type="submit">Mint token</button>
              <div className={`status ${status.toLowerCase().includes("token") ? "success" : ""}`}>{status}</div>
            </form>
            {hasAuth && (
              <div className="list" style={{ marginTop: 10 }}>
                <div className="chip">Tenant ID: {tenantId}</div>
                <div className="chip">Token saved locally</div>
                <button className="button-ghost" type="button" onClick={handleLogout}>
                  Clear token
                </button>
              </div>
            )}
            <div className="hint">Tokens are tenant-scoped. Use different names for separate tenants.</div>
          </section>

          <section className="card">
            <h2>Knowledge base</h2>
            <form onSubmit={handleCreateKB}>
              <label>
                Name
                <input value={kbName} onChange={(e) => setKbName(e.target.value)} placeholder="Product Docs" required />
              </label>
              <label>
                Description
                <input value={kbDesc} onChange={(e) => setKbDesc(e.target.value)} placeholder="Optional" />
              </label>
              <button type="submit" disabled={!hasAuth}>
                Create KB
              </button>
            </form>
            <div className="list">
              {kbs.length === 0 && <div className="muted">No KBs yet. Create one to start ingesting.</div>}
              {kbs.map((kb) => (
                <div key={kb.id} className="item">
                  <div>
                    <strong>{kb.name}</strong>
                    <div className="muted">{kb.description || "—"}</div>
                  </div>
                  <button className="button-ghost" type="button" onClick={() => handleDeleteKB(kb.id)}>
                    Delete
                  </button>
                </div>
              ))}
            </div>
            <div className="hint">Tip: Create separate KBs for distinct domains (e.g., product docs vs. policies).</div>
          </section>
        </div>
      </div>

      <div className={`tab-panel ${tab === "ingest" ? "active" : ""}`}>
        <div className="grid">
          <section className="card">
            <h2>Ingest file</h2>
            <form onSubmit={handleIngestFile}>
              <label>
                Knowledge base
                <select value={ingestKbId} onChange={(e) => setIngestKbId(e.target.value)} disabled={!readyForActions}>
                  {kbOptions}
                </select>
              </label>
              <label>
                File
                <input id="ingest-file" type="file" onChange={(e) => setIngestFile(e.target.files?.[0] || null)} />
              </label>
              <label>
                Metadata (JSON, optional)
                <input value={ingestMeta} onChange={(e) => setIngestMeta(e.target.value)} placeholder='{"source":"upload"}' />
              </label>
              <button type="submit" disabled={!readyForActions}>
                Upload
              </button>
            </form>
            <div className="status">{ingestStatus}</div>
            <div className="hint">Uploads run in the background. Check `/documents` for status.</div>
          </section>

          <section className="card">
            <h2>Ingest URL</h2>
            <form onSubmit={handleIngestUrl}>
              <label>
                Knowledge base
                <select value={urlKbId} onChange={(e) => setUrlKbId(e.target.value)} disabled={!readyForActions}>
                  {kbOptions}
                </select>
              </label>
              <label>
                URL
                <input value={urlInput} onChange={(e) => setUrlInput(e.target.value)} type="url" placeholder="https://example.com/page" />
              </label>
              <button type="submit" disabled={!readyForActions}>
                Fetch
              </button>
            </form>
            <div className="status">{urlStatus}</div>
            <div className="hint">For noisy pages, prefer the file upload with cleaned content.</div>
          </section>
        </div>
      </div>

      <div className={`tab-panel ${tab === "query" ? "active" : ""}`}>
        <section className="card" style={{ marginTop: 10 }}>
          <h2>Query</h2>
          <form onSubmit={handleQuery}>
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
              <label>
                Knowledge base
                <select value={queryKbId} onChange={(e) => setQueryKbId(e.target.value)} disabled={!readyForActions}>
                  {kbOptions}
                </select>
              </label>
              <label>
                Search type
                <select value={searchType} onChange={(e) => setSearchType(e.target.value)}>
                  <option value="hybrid">Hybrid (default)</option>
                  <option value="vector">Vector only</option>
                  <option value="full_text">Full text</option>
                </select>
              </label>
              <label>
                Top K
                <input value={topK} onChange={(e) => setTopK(Number(e.target.value))} type="number" min={1} max={10} />
              </label>
              <label>
                Max tokens
                <input value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} type="number" min={32} max={512} />
              </label>
              <label className="flex" style={{ alignItems: "center", marginTop: 8 }}>
                <input type="checkbox" checked={useRerank} onChange={(e) => setUseRerank(e.target.checked)} />
                <span className="muted">Use reranker</span>
              </label>
            </div>
            <label>
              Question
              <textarea value={queryText} onChange={(e) => setQueryText(e.target.value)} rows={3} placeholder="Ask a question using your KB..." />
            </label>
            <button type="submit" disabled={!readyForActions}>
              Ask
            </button>
          </form>
          <div className="status">{queryStatus}</div>
          {answer && (
            <div className="answer" style={{ display: "block" }}>
              {answer}
            </div>
          )}
          <div className="sources">
            {sources.length === 0 && <div className="muted">No sources returned.</div>}
            {sources.map((s) => (
              <div key={s.chunk_id} className="source">
                <div className="tag">Chunk {s.chunk_id.slice(0, 8)}...</div>
                <div style={{ margin: "8px 0", whiteSpace: "pre-wrap" }}>{s.content}</div>
                <small>Document: {s.document_id}</small>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
