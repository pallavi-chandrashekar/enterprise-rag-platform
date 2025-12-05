import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.deps import get_current_tenant
from app.core.config import settings
from app.models.entities import Chunk, Document, KnowledgeBase, Tenant
from app.observability import http_request_latency_ms, http_requests_total, metrics
from app.schemas.models import (
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSource,
    URLIngestRequest,
)
from app.services.ingestion import IngestionPipeline
from app.services.rag import RAGService

router = APIRouter()


@router.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", response_class=PlainTextResponse, tags=["health"])
async def metrics_endpoint() -> PlainTextResponse:
    from prometheus_client import generate_latest

    return PlainTextResponse(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


def _get_or_create_tenant(db: Session, tenant_id: str) -> Tenant:
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id is not a valid UUID")

    tenant = db.get(Tenant, tenant_uuid)
    if tenant:
        return tenant

    tenant = Tenant(id=tenant_uuid, name=f"tenant-{tenant_id}")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/kb", response_model=KnowledgeBaseRead, tags=["knowledge_bases"])
async def create_kb(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> KnowledgeBaseRead:
    tenant = _get_or_create_tenant(db, tenant_id)
    kb = KnowledgeBase(tenant_id=tenant.id, name=payload.name, description=payload.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    metrics.inc("kb_created")
    return kb


@router.get("/kb", response_model=list[KnowledgeBaseRead], tags=["knowledge_bases"])
async def list_kb(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> list[KnowledgeBaseRead]:
    tenant = _get_or_create_tenant(db, tenant_id)
    results = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == tenant.id).order_by(KnowledgeBase.created_at.desc()).all()
    return results


@router.delete("/kb/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["knowledge_bases"])
async def delete_kb(
    kb_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> None:
    tenant = _get_or_create_tenant(db, tenant_id)
    try:
        kb_uuid = uuid.UUID(kb_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kb_id is not a valid UUID")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_uuid, KnowledgeBase.tenant_id == tenant.id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found for tenant")

    db.delete(kb)
    db.commit()
    metrics.inc("kb_deleted")


def _parse_metadata(metadata_json: str | None) -> dict[str, Any] | None:
    if metadata_json is None or metadata_json == "":
        return None
    try:
        value = json.loads(metadata_json)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("metadata must be a JSON object")
        return value
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid metadata JSON: {exc.msg}")


@router.post("/ingest", response_model=DocumentRead, tags=["ingestion"])
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    metadata: str | None = Form(None),
    idempotency_key: str | None = Form(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> DocumentRead:
    tenant = _get_or_create_tenant(db, tenant_id)
    metadata_dict = _parse_metadata(metadata)

    try:
        kb_uuid = uuid.UUID(kb_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kb_id is not a valid UUID")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_uuid, KnowledgeBase.tenant_id == tenant.id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found for tenant")

    # Idempotency: if key provided, reuse or retry the same document for this tenant/kb.
    document: Document
    if idempotency_key:
        existing = (
            db.query(Document)
            .filter(
                Document.tenant_id == tenant.id,
                Document.kb_id == kb.id,
                Document.doc_metadata["idempotency_key"].astext == idempotency_key,  # type: ignore[index]
            )
            .order_by(Document.created_at.desc())
            .first()
        )
        if existing and existing.status == "READY":
            return existing
        if existing:
            document = existing
            document.filename = file.filename
            document.status = "PROCESSING"
            document.doc_metadata = (document.doc_metadata or {}) | {"idempotency_key": idempotency_key}
        else:
            merged_meta = (metadata_dict or {}) | {"idempotency_key": idempotency_key, "ingestion_attempts": 0}
            document = Document(tenant_id=tenant.id, kb_id=kb.id, filename=file.filename, status="PROCESSING", doc_metadata=merged_meta)
            db.add(document)
            db.commit()
            db.refresh(document)
    else:
        merged_meta = (metadata_dict or {}) | {"ingestion_attempts": 0}
        document = Document(tenant_id=tenant.id, kb_id=kb.id, filename=file.filename, status="PROCESSING", doc_metadata=merged_meta)
        db.add(document)
        db.commit()
        db.refresh(document)

    ingestion = IngestionPipeline(db)
    file_bytes = await file.read()
    metrics.inc("ingest_requests")

    background_tasks.add_task(ingestion.process_uploaded_file, document, file_bytes)

    return document


@router.post("/ingest_url", response_model=DocumentRead, tags=["ingestion"])
async def ingest_url(
    payload: URLIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> DocumentRead:
    tenant = _get_or_create_tenant(db, tenant_id)

    try:
        kb_uuid = uuid.UUID(payload.kb_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kb_id is not a valid UUID")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_uuid, KnowledgeBase.tenant_id == tenant.id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found for tenant")

    document = Document(tenant_id=tenant.id, kb_id=kb.id, filename=payload.url, status="PROCESSING", doc_metadata=payload.metadata)
    db.add(document)
    db.commit()
    db.refresh(document)

    ingestion = IngestionPipeline(db)
    metrics.inc("ingest_requests")

    background_tasks.add_task(ingestion.process_url, document)

    return document


@router.get("/documents", response_model=list[DocumentRead], tags=["ingestion"])
async def list_documents(
    kb_id: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> list[DocumentRead]:
    tenant = _get_or_create_tenant(db, tenant_id)
    query = db.query(Document).filter(Document.tenant_id == tenant.id)
    if kb_id:
        try:
            kb_uuid = uuid.UUID(kb_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kb_id is not a valid UUID")
        query = query.filter(Document.kb_id == kb_uuid)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/documents/{document_id}", response_model=DocumentRead, tags=["ingestion"])
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> DocumentRead:
    tenant = _get_or_create_tenant(db, tenant_id)
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document_id is not a valid UUID")

    doc = (
        db.query(Document)
        .filter(Document.id == doc_uuid, Document.tenant_id == tenant.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for tenant")
    return doc


@router.get("/documents/{document_id}/chunks", tags=["ingestion"])
async def list_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> list[dict[str, str | dict | None]]:
    tenant = _get_or_create_tenant(db, tenant_id)
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document_id is not a valid UUID")

    doc = (
        db.query(Document)
        .filter(Document.id == doc_uuid, Document.tenant_id == tenant.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for tenant")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc_uuid, Chunk.tenant_id == tenant.id)
        .order_by(Chunk.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(ch.id),
            "kb_id": str(ch.kb_id),
            "document_id": str(ch.document_id),
            "content": ch.content,
            "metadata": ch.chunk_metadata,
        }
        for ch in chunks
    ]


@router.post("/rag/query", response_model=RAGQueryResponse, tags=["rag"])
async def rag_query(
    payload: RAGQueryRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> RAGQueryResponse:
    tenant = _get_or_create_tenant(db, tenant_id)
    try:
        kb_uuid = uuid.UUID(payload.kb_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kb_id is not a valid UUID")

    kb_exists = db.query(KnowledgeBase.id).filter(KnowledgeBase.id == kb_uuid, KnowledgeBase.tenant_id == tenant.id).first()
    if not kb_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found for tenant")

    start_time = time.time()
    request_start = start_time
    rag_service = RAGService(db)
    metrics.inc("rag_requests")
    answer, sources = rag_service.answer(
        tenant.id,
        kb_uuid,
        payload.query,
        payload.top_k,
        payload.max_tokens,
        payload.use_rerank,
        payload.search_type,
    )

    latency_ms = int((time.time() - start_time) * 1000)
    metrics.observe_latency("rag_total_ms", latency_ms)
    http_requests_total.labels("POST", "/rag/query", "200").inc()
    http_request_latency_ms.labels("POST", "/rag/query").observe(latency_ms)
    return RAGQueryResponse(answer=answer, sources=sources, latency_ms=latency_ms)


@router.get("/settings", tags=["debug"])
async def read_settings() -> dict[str, str | int]:
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "vector_dimension": settings.vector_dimension,
        "metrics": metrics.snapshot(),
    }
