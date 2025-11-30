#Enterprise RAG Platform

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform built with FastAPI, PostgreSQL, PGVector, LLM orchestration, and a modular architecture that mirrors how real companies build AI platforms.

🚀 Features (MVP)

Multi-tenant knowledge bases
Document ingestion (PDF, DOCX, text, HTML)
Text extraction, cleaning, chunking
Embeddings (local or cloud)
Vector search using PGVector
RAG query endpoint (/rag/query)
JWT-based tenant-aware auth
Logging & metrics
Deployable via Docker, Render, Fly.io

📂 Project Structure

backend/       → FastAPI app & core services  
docs/          → Architecture, diagrams, requirements  
docker-compose.yml

🏁 Getting Started (local)

- Install Python 3.11+.  
- Install deps: `pip install -r requirements.txt` (set `PYTHONPATH=backend` when running locally).  
- Run API: `uvicorn app.main:app --app-dir backend --reload`.  
- Or via Docker Compose: `docker-compose up --build` (starts Postgres+PGVector and the API).
- PGVector is enabled automatically via `db/init/01-enable-vector.sql` when the DB is first created. If you already have the volume, run `docker-compose exec db psql -U rag_user -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"`.

🧱 Tech Stack

Python, FastAPI
PostgreSQL + PGVector
sentence-transformers / Groq / OpenAI
Docker + Docker Compose
GitHub Actions (CI/CD)

📘 Documentation

See: /docs/Architecture.md (in progress)

📌 Goal

To build and ship a real-world enterprise-grade RAG service end-to-end as part of a portfolio and practical learning project.
