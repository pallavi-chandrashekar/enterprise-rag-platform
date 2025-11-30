from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True


class DocumentIngestRequest(BaseModel):
    kb_id: str
    filename: str
    metadata: dict[str, Any] | None = None


class DocumentRead(BaseModel):
    id: str
    kb_id: str
    filename: str
    status: str
    metadata: dict[str, Any] | None = Field(None, alias="doc_metadata")
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class RAGQueryRequest(BaseModel):
    kb_id: str
    query: str = Field(..., min_length=1)
    top_k: int = 5


class RAGSource(BaseModel):
    document_id: str
    chunk_id: str
    content: str
    metadata: dict[str, Any] | None = Field(None, alias="chunk_metadata")


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    latency_ms: int
