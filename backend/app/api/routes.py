import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.deps import get_current_tenant
from app.core.config import get_settings
from app.models.entities import Document, KnowledgeBase, Tenant
from app.schemas.models import (
    DocumentIngestRequest,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSource,
)

router = APIRouter()


@router.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


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
    return kb


@router.get("/kb", response_model=list[KnowledgeBaseRead], tags=["knowledge_bases"])
async def list_kb(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
) -> list[KnowledgeBaseRead]:
    tenant = _get_or_create_tenant(db, tenant_id)
    results = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == tenant.id).order_by(KnowledgeBase.created_at.desc()).all()
    return results


@router.post("/ingest", response_model=DocumentRead, tags=["ingestion"])
async def ingest_document(
    payload: DocumentIngestRequest,
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

    document = Document(tenant_id=tenant.id, kb_id=kb.id, filename=payload.filename, doc_metadata=payload.metadata)
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


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

    # TODO: plug in embedding model, vector search, and LLM call.
    answer = "This is a stubbed answer. Plug in LLM and retrieval logic."
    sources = [
        RAGSource(document_id="stub-doc", chunk_id="stub-chunk", content="example content", metadata=None)
    ] if payload.top_k else []

    latency_ms = int((time.time() - start_time) * 1000)
    return RAGQueryResponse(answer=answer, sources=sources, latency_ms=latency_ms)


settings = get_settings()


@router.get("/settings", tags=["debug"])
async def read_settings() -> dict[str, str | int]:
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "vector_dimension": settings.vector_dimension,
    }
