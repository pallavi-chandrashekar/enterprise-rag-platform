import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.deps import get_current_tenant
from app.core.config import get_settings
from app.models.entities import Document, KnowledgeBase, Tenant
from app.schemas.models import (
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSource,
)
from app.services.ingestion import IngestionPipeline
from app.services.rag import RAGService

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
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    metadata: str | None = Form(None),
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

    document = Document(tenant_id=tenant.id, kb_id=kb.id, filename=file.filename, status="PROCESSING", doc_metadata=metadata_dict)
    db.add(document)
    db.commit()
    db.refresh(document)

    ingestion = IngestionPipeline(db)
    file_bytes = await file.read()
    try:
        ingestion.process_uploaded_file(document, file_bytes)
        db.refresh(document)
    except HTTPException:
        ingestion.mark_failed(document.id, "bad_request")
        raise
    except ValueError as exc:
        ingestion.mark_failed(document.id, str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        ingestion.mark_failed(document.id, "ingestion_error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to ingest document") from exc

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
    rag_service = RAGService(db)
    answer, sources = rag_service.answer(tenant.id, kb_uuid, payload.query, payload.top_k)

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
