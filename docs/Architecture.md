# Enterprise RAG Platform --- Architecture (Short Version)

**Version:** 1.0

## 1. High-Level Overview

The Enterprise RAG Platform is a modular backend service enabling
multi-tenant document ingestion, vector search, and RAG through a REST
API.

## 2. Core Components

-   FastAPI API layer
-   Ingestion pipeline
-   Embedding service
-   PGVector vector store
-   Metadata DB
-   RAG Orchestrator
-   Auth layer
-   Logging & Observability

## 3. Architecture Diagram

See architecture_diagram.png in this folder.

## 4. Design Principles

-   Modular
-   Tenant-safe
-   API-first
-   Free/local friendly
-   Scalable

## 5. Future Extensions

-   Async ingestion
-   Rerankers
-   Hybrid search
-   Agents
