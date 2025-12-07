const apiBase = window.location.origin;

const state = {
  token: null,
  tenantId: null,
  tenantName: null,
  knowledgeBases: [],
};

const els = {
  loginForm: document.getElementById("login-form"),
  tenantInput: document.getElementById("tenant-name"),
  loginStatus: document.getElementById("login-status"),
  authInfo: document.getElementById("auth-info"),
  tenantId: document.getElementById("tenant-id"),
  logout: document.getElementById("logout-btn"),
  kbForm: document.getElementById("kb-form"),
  kbName: document.getElementById("kb-name"),
  kbDesc: document.getElementById("kb-desc"),
  kbList: document.getElementById("kb-list"),
  ingestForm: document.getElementById("ingest-form"),
  ingestKb: document.getElementById("ingest-kb"),
  ingestFile: document.getElementById("ingest-file"),
  ingestMeta: document.getElementById("ingest-meta"),
  ingestStatus: document.getElementById("ingest-status"),
  urlForm: document.getElementById("url-form"),
  urlKb: document.getElementById("url-kb"),
  urlInput: document.getElementById("url-input"),
  urlStatus: document.getElementById("url-status"),
  queryForm: document.getElementById("query-form"),
  queryKb: document.getElementById("query-kb"),
  querySearch: document.getElementById("query-search"),
  queryTopK: document.getElementById("query-topk"),
  queryMax: document.getElementById("query-max"),
  queryRerank: document.getElementById("query-rerank"),
  queryText: document.getElementById("query-text"),
  queryStatus: document.getElementById("query-status"),
  answer: document.getElementById("answer"),
  sources: document.getElementById("sources"),
};

const storageKeys = {
  token: "rag_token",
  tenantId: "rag_tenant_id",
  tenantName: "rag_tenant_name",
};

function setStatus(el, message, type = "") {
  if (!el) return;
  el.textContent = message || "";
  el.classList.remove("success", "error");
  if (type) el.classList.add(type);
}

function saveAuth(token, tenantId, tenantName) {
  state.token = token;
  state.tenantId = tenantId;
  state.tenantName = tenantName;
  localStorage.setItem(storageKeys.token, token);
  localStorage.setItem(storageKeys.tenantId, tenantId);
  localStorage.setItem(storageKeys.tenantName, tenantName);
  renderAuth();
}

function clearAuth() {
  state.token = null;
  state.tenantId = null;
  state.tenantName = null;
  localStorage.removeItem(storageKeys.token);
  localStorage.removeItem(storageKeys.tenantId);
  localStorage.removeItem(storageKeys.tenantName);
  renderAuth();
}

function renderAuth() {
  const hasAuth = Boolean(state.token);
  els.authInfo.style.display = hasAuth ? "flex" : "none";
  els.tenantId.textContent = state.tenantId || "";
  if (hasAuth) {
    els.loginStatus.textContent = `Authenticated as ${state.tenantName}`;
    fetchKnowledgeBases();
  } else {
    els.loginStatus.textContent = "Mint a token to start";
    els.kbList.innerHTML = "";
    setKBOptions([]);
  }
}

async function api(path, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const opts = { ...options, headers };
  const res = await fetch(`${apiBase}${path}`, opts);
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!res.ok) {
    const detail = data?.detail || res.statusText || "Request failed";
    throw new Error(detail);
  }
  return data;
}

async function fetchKnowledgeBases() {
  if (!state.token) return;
  try {
    const kbs = await api("/kb");
    state.knowledgeBases = kbs;
    renderKnowledgeBases();
    setKBOptions(kbs);
  } catch (err) {
    setStatus(els.loginStatus, err.message, "error");
  }
}

function renderKnowledgeBases() {
  const list = els.kbList;
  list.innerHTML = "";
  if (!state.knowledgeBases.length) {
    list.innerHTML = '<div class="muted">No knowledge bases yet.</div>';
    return;
  }
  state.knowledgeBases.forEach((kb) => {
    const div = document.createElement("div");
    div.className = "item";
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = kb.name;
    const desc = document.createElement("div");
    desc.className = "muted";
    desc.textContent = kb.description || "No description";
    info.appendChild(title);
    info.appendChild(desc);

    const button = document.createElement("button");
    button.className = "button-ghost";
    button.textContent = "Delete";
    button.addEventListener("click", () => deleteKB(kb.id));

    div.appendChild(info);
    div.appendChild(button);
    list.appendChild(div);
  });
}

function setKBOptions(kbs) {
  const selects = [els.ingestKb, els.urlKb, els.queryKb];
  selects.forEach((select) => {
    if (!select) return;
    select.innerHTML = "";
    if (!kbs.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No KBs available";
      select.appendChild(opt);
      select.disabled = true;
    } else {
      select.disabled = false;
      kbs.forEach((kb) => {
        const opt = document.createElement("option");
        opt.value = kb.id;
        opt.textContent = kb.name;
        select.appendChild(opt);
      });
    }
  });
}

async function deleteKB(id) {
  if (!confirm("Delete this KB and its documents?")) return;
  try {
    await api(`/kb/${id}`, { method: "DELETE" });
    setStatus(els.loginStatus, "Knowledge base deleted", "success");
    fetchKnowledgeBases();
  } catch (err) {
    setStatus(els.loginStatus, err.message, "error");
  }
}

els.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const tenantName = els.tenantInput.value.trim();
  if (!tenantName) return;
  setStatus(els.loginStatus, "Minting token...");
  try {
    const data = await api("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_name: tenantName }),
    });
    saveAuth(data.token, data.tenant_id, data.tenant_name);
    setStatus(els.loginStatus, "Token saved. Ready to use.", "success");
  } catch (err) {
    setStatus(els.loginStatus, err.message, "error");
  }
});

els.logout.addEventListener("click", () => {
  clearAuth();
});

els.kbForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.token) return alert("Sign in first");
  const name = els.kbName.value.trim();
  if (!name) return;
  const description = els.kbDesc.value.trim();
  setStatus(els.loginStatus, "Creating KB...");
  try {
    await api("/kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: description || null }),
    });
    els.kbForm.reset();
    setStatus(els.loginStatus, "Knowledge base created", "success");
    fetchKnowledgeBases();
  } catch (err) {
    setStatus(els.loginStatus, err.message, "error");
  }
});

els.ingestForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.token) return alert("Sign in first");
  if (!els.ingestKb.value) return alert("Pick a knowledge base");
  if (!els.ingestFile.files.length) return alert("Choose a file to upload");
  const formData = new FormData();
  formData.append("kb_id", els.ingestKb.value);
  formData.append("file", els.ingestFile.files[0]);
  const meta = els.ingestMeta.value.trim();
  if (meta) formData.append("metadata", meta);
  setStatus(els.ingestStatus, "Uploading...");
  try {
    await api("/ingest", { method: "POST", body: formData });
    setStatus(els.ingestStatus, "Ingestion started (background task)", "success");
    els.ingestForm.reset();
  } catch (err) {
    setStatus(els.ingestStatus, err.message, "error");
  }
});

els.urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.token) return alert("Sign in first");
  if (!els.urlKb.value) return alert("Pick a knowledge base");
  const url = els.urlInput.value.trim();
  if (!url) return;
  setStatus(els.urlStatus, "Submitting URL...");
  try {
    await api("/ingest_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kb_id: els.urlKb.value, url }),
    });
    setStatus(els.urlStatus, "URL queued for ingestion", "success");
    els.urlForm.reset();
  } catch (err) {
    setStatus(els.urlStatus, err.message, "error");
  }
});

els.queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.token) return alert("Sign in first");
  const kbId = els.queryKb.value;
  if (!kbId) return alert("Pick a knowledge base");
  const question = els.queryText.value.trim();
  if (!question) return;
  setStatus(els.queryStatus, "Querying...");
  els.answer.style.display = "none";
  els.sources.innerHTML = "";
  try {
    const payload = {
      kb_id: kbId,
      query: question,
      top_k: Number(els.queryTopK.value) || 5,
      max_tokens: Number(els.queryMax.value) || 128,
      use_rerank: Boolean(els.queryRerank.checked),
      search_type: els.querySearch.value,
    };
    const res = await api("/rag/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    els.answer.style.display = "block";
    els.answer.textContent = res.answer;
    renderSources(res.sources);
    setStatus(els.queryStatus, `Answered in ${res.latency_ms} ms`, "success");
  } catch (err) {
    setStatus(els.queryStatus, err.message, "error");
  }
});

function renderSources(sources) {
  els.sources.innerHTML = "";
  if (!sources || !sources.length) {
    els.sources.innerHTML = '<div class="muted">No sources returned</div>';
    return;
  }
  sources.forEach((s) => {
    const div = document.createElement("div");
    div.className = "source";
    const tag = document.createElement("div");
    tag.className = "tag";
    tag.textContent = `Chunk ${s.chunk_id.slice(0, 8)}...`;

    const body = document.createElement("div");
    body.style.margin = "8px 0";
    body.style.whiteSpace = "pre-wrap";
    body.textContent = s.content;

    const meta = document.createElement("small");
    meta.textContent = `Document: ${s.document_id}`;

    div.appendChild(tag);
    div.appendChild(body);
    div.appendChild(meta);
    els.sources.appendChild(div);
  });
}

function restoreAuth() {
  const token = localStorage.getItem(storageKeys.token);
  const tenantId = localStorage.getItem(storageKeys.tenantId);
  const tenantName = localStorage.getItem(storageKeys.tenantName);
  if (token && tenantId) {
    state.token = token;
    state.tenantId = tenantId;
    state.tenantName = tenantName || "tenant";
  }
  renderAuth();
}

restoreAuth();
