# Enterprise RAG Platform - Architecture Reference

**Version:** 2.0

## 1. High-Level Design Pattern
The platform follows a **Split Architecture** enabling scalable RAG for enterprise workloads. It decouples the resource-intensive **Data Processing (Ingestion)** from the latency-sensitive **Query Serving (RAG)**.

### Architecture Diagram
![Architecture Diagram](./architecture_diagram-v2.png)

## 2. Core Subsystems

### A. The Ingestion Engine (Data Pipeline)
*Responsible for transforming raw documents into searchable vectors.*

* **Flow:** `Document Upload` -> `Text Extraction` -> `Semantic Chunking` -> `Embedding` -> `Postgres (PGVector)`
* **Key Features:**
    * **Idempotency:** Prevents duplicate vectors via hash checks or clearing prior chunks on re-ingestion.
    * **Hierarchy-Aware Chunking:** Preserves document structure (headers/paragraphs) for better context.
    * **Metadata Enrichment:** Extracts and stores file metadata for filtering.
    * **Atomic Transactions:** Uses database transactions to ensure document and vector consistency.

### B. The Hybrid Storage Layer
*Unified persistence for vectors and relational data.*

* **Technology:** PostgreSQL 16+ with `pgvector`.
* **Why Postgres?**
    * **ACID Compliance:** Guarantees data integrity during updates/deletes.
    * **Row-Level Security (RLS):** Capable of enforcing tenant isolation at the database level.
    * **Operational Simplicity:** No need for a separate specialized vector database.
    * **Hybrid Querying:** Enables single-query execution for vector similarity + relational filtering (e.g., `WHERE tenant_id = ...`).

### C. The Orchestration API (Serving Layer)
*FastAPI-based router that coordinates retrieval and generation.*

* **Retrieval Strategy:**
    1.  **Parallel Search:** Executes `Vector Search` (semantic) and `Full-Text Search` (keyword) concurrently.
    2.  **Reciprocal Rank Fusion (RRF):** Merges results to balance semantic understanding with exact keyword matches.
    3.  **Reranking:** (Optional) Uses a Cross-Encoder to deeply analyze and re-score the top candidates for precision.
* **Generation:**
    * Constructs a prompt with the highest-scored chunks.
    * Streams the LLM response back to the client.

## 3. Detailed Data Flow

### Ingestion Flow
1.  **Upload:** User sends file/URL to `/ingest`.
2.  **Extraction:** System parses PDF/Docx/HTML (via `pypdf`, `python-docx`, `beautifulsoup4`).
3.  **Chunking:** Text is split using a sliding window with overlap (see `services/ingestion.py`).
4.  **Embedding:** Chunks are converted to vectors (e.g., via OpenAI or HuggingFace).
5.  **Storage:** Vectors + Text + Metadata stored in the `chunks` table.

### RAG Query Flow
1.  **Query:** User sends query to `/rag/query`.
2.  **Hybrid Retrieval:**
    * *Vector Path:* Query -> Embedding -> Cosine Similarity Search.
    * *Keyword Path:* Query -> `tsquery` -> Full-Text Rank.
3.  **Fusion:** Results combined via Reciprocal Rank Fusion (RRF) in `services/rag.py`.
4.  **Rerank:** Top K results re-scored by Reranker model (if enabled).
5.  **Synthesis:** LLM generates answer using retrieved context.

## 4. Key Design Decisions

* **FastAPI:** For high-performance async I/O.
* **PGVector:** To avoid infrastructure bloat and maintain strong data consistency.
* **Multi-Tenancy:** Implemented via `tenant_id` column on all major tables (`documents`, `chunks`), ensuring strict logical isolation.