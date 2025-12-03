#Enterprise RAG Platform

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform built with FastAPI, PostgreSQL, PGVector, LLM orchestration, and a modular architecture that mirrors how real companies build AI platforms.

🚀 Features (MVP)

Multi-tenant knowledge bases (create/list/delete)  
Document ingestion (PDF, DOCX, text/markdown) with extraction → chunking → embeddings → PGVector storage  
Similarity search + RAG query endpoint (`/rag/query`) with grounding sources  
JWT-based tenant-aware auth  
Configurable LLM client (stub by default; OpenAI/Groq supported)  
Basic request logging + response timing headers  
Deployable via Docker, Render, Fly.io

📂 Project Structure

backend/       → FastAPI app & core services  
docs/          → Architecture, diagrams, requirements  
docker-compose.yml

🏁 Getting Started (local)

- Copy `.env.example` to `.env` and set secrets (at least `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`).  
- Install Python 3.11+.  
- Install deps: `pip install -r requirements.txt` (set `PYTHONPATH=backend` when running locally).  
- Run API: `uvicorn app.main:app --app-dir backend --reload`.  
- Or via Docker Compose: `docker-compose up --build` (starts Postgres+PGVector and the API).  
- PGVector is enabled automatically via `db/init/01-enable-vector.sql` when the DB is first created. If you already have the volume, run `docker-compose exec db psql -U rag_user -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"`.

🔌 API quickstart

- `POST /kb` — create knowledge base.  
- `GET /kb` — list knowledge bases.  
- `DELETE /kb/{kb_id}` — delete knowledge base + cascaded chunks/documents.  
- `POST /ingest` — multipart upload: `file` (PDF/DOCX/TXT/MD), `kb_id`, optional `metadata` JSON string, optional `idempotency_key`. The pipeline extracts text → chunks → embeddings and marks the document `READY`; with `idempotency_key`, retries reuse the same doc record.  
- `GET /documents` — list documents for the tenant (optional `kb_id` filter) with ingestion status.  
- `GET /documents/{document_id}` — fetch a document record + status.  
- `GET /documents/{document_id}/chunks` — list chunk content/metadata for a document (tenant-scoped).  
- `POST /rag/query` — `{ "kb_id": "...", "query": "question", "top_k": 5, "max_tokens": 128 }` returns grounded answer + sources; tune `max_tokens` to trade off latency/cost.  
- Use `Authorization: Bearer <jwt-with-tenant_id>`; `/settings` is available for quick config inspection.
- Need a token? Run `python backend/scripts/generate_jwt.py --secret <JWT_SECRET>` to print a usable `tenant_id` and token.

🏗️ CI/CD

- GitHub Actions workflow `.github/workflows/ci.yml` runs on push/PR: installs deps, compile-checks the backend, runs `pytest`, and builds the backend Docker image to catch Dockerfile regressions.

🧪 Testing notes

- Production requires Postgres + PGVector; tests fall back to SQLite with portable model types (UUIDs as strings, metadata/embeddings stored as JSON). This is only for local/CI test runs; use Postgres in real deployments.

🔤 Embeddings & LLM

- Embeddings use `sentence-transformers/all-MiniLM-L6-v2` (dim 384, cosine-normalized). Adjust via `EMBEDDING_MODEL_NAME` / `VECTOR_DIMENSION`.  
- LLM client defaults to a stub; set `LLM_PROVIDER=openai|groq`, `LLM_MODEL=<model>`, and `LLM_API_KEY=<key>` to call a real provider.  
- Rebuild containers after changing models/deps: `docker-compose up --build --force-recreate`.

🧱 Tech Stack

Python, FastAPI
PostgreSQL + PGVector
sentence-transformers / Groq / OpenAI
Docker + Docker Compose
GitHub Actions (CI/CD)

📘 Documentation

See: /docs/Architecture.md

📌 Goal

To build and ship a real-world enterprise-grade RAG service end-to-end as part of a portfolio and practical learning project.
