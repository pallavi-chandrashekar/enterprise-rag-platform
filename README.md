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
docker-compose.yml (coming soon)

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
