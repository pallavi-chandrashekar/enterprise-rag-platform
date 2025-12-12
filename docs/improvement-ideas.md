# Improvement Areas for Enterprise RAG Platform

This document captures actionable improvements across core modules, focusing on reliability, observability, and safety.

## API & Application Layer (FastAPI)
- Split readiness vs. liveness endpoints; wire readiness to dependencies (DB, embeddings) to improve rollout safety.
- Normalize request/tenant labels in Prometheus metrics to avoid high cardinality; add error code labels to timing metrics.
- Add structured exception middleware with error IDs and correlation IDs propagated from incoming headers.
- Provide rate limiting or abuse-protection hooks for public endpoints and admin UI.

## Auth & Multi-Tenancy
- Rotate JWT signing keys via key IDs (kid) in headers; store active keys in configuration for zero-downtime rotation.
- Harden tenant resolution: reject missing/unknown tenants early and add audit logs for token issuance and usage.
- Add per-tenant configuration introspection endpoint gated by admin claims to aid debugging.

## Ingestion Pipeline
- Introduce streaming uploads for large files and enforce configurable size/type limits before extraction.
- Add extraction fallbacks per MIME type with better error surfacing (e.g., PDF image fallback to OCR).
- Implement backoff/retry around external fetch and embedding calls; persist transient failure states for retry.
- Tune chunking heuristics per document type and allow per-tenant overrides; capture chunk-generation metrics.
- Enforce idempotency keys on ingestion requests to prevent duplicate documents on client retries.

## Storage & Metadata
- Add DB migrations for PGVector index normalization and vacuum/maintenance tasks; expose maintenance CLI.
- Validate embedding dimension against model selection at startup and fail fast with actionable errors.
- Ensure document and chunk lifecycle consistency (ingested → indexed → searchable) with status transitions.

## Retrieval & RAG
- Normalize queries (lowercasing/trim/punctuation) before embedding to reduce vector noise.
- Make hybrid search scoring deterministic with documented weight defaults; expose per-request overrides with limits.
- Gate reranking when the rerank model or API key is unavailable; surface structured errors to callers.
- Add guardrails in prompt construction (context truncation, citation counts) to limit token bloat and injection risks.
- Collect search quality feedback endpoints (thumbs up/down) and store signals for future ranking.

## Observability & Operations
- Add OpenTelemetry trace propagation to downstream LLM/embedding clients and database calls.
- Create operational runbooks for common failures (DB connectivity, embedding timeouts, queue backlog).
- Provide feature flags for experimental components (rerankers, hybrid search weights) to allow safe rollout.

## Frontend/Admin UI
- Add health/status surface for ingestion jobs and embeddings; stream progress updates to the UI.
- Improve error banners with correlation IDs and retry guidance; capture client-side telemetry (performance + errors).
- Add docs/sandbox pages that exercise RAG queries with adjustable parameters for demos and debugging.

## Testing & Tooling
- Expand integration tests for end-to-end ingestion → search → RAG flow using ephemeral Postgres/PGVector.
- Add contract tests for provider clients (OpenAI/Azure/Bedrock) using recorded fixtures to avoid network calls.
- Validate settings schema via pydantic with explicit env var documentation and type validation errors.

## Security
- Enforce secure headers (CSP, HSTS, frame options) at the API gateway; sanitize file names and metadata inputs.
- Add optional PII detection and redaction in ingestion and response generation paths.
- Provide dependency scanning and minimal base images; document patch cadence and upgrade process.
