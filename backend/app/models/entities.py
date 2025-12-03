import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.session import Base

settings = get_settings()

# Basic DB portability: fall back to generic types when not using Postgres/pgvector (e.g., SQLite in tests).
IS_SQLITE = settings.database_url.startswith("sqlite")

if IS_SQLITE:
    from sqlalchemy import JSON

    UUID_TYPE = String(36)
    JSON_TYPE = JSON
    EMBEDDING_TYPE = JSON
else:
    from pgvector.sqlalchemy import Vector

    UUID_TYPE = UUID(as_uuid=True)
    JSON_TYPE = JSONB
    EMBEDDING_TYPE = Vector(dim=settings.vector_dimension)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    knowledge_bases = relationship("KnowledgeBase", back_populates="tenant", cascade="all, delete")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="knowledge_bases")
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete")
    chunks = relationship("Chunk", back_populates="knowledge_base", cascade="all, delete")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    kb_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="UPLOADED")
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="documents")
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete")

    @property
    def failure_reason(self) -> str | None:
        meta_reason = (self.doc_metadata or {}).get("last_error") if self.doc_metadata else None
        if meta_reason:
            return meta_reason
        if self.status.startswith("FAILED"):
            parts = self.status.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
            return "failed"
        return None

    @property
    def ingestion_attempts(self) -> int | None:
        if self.doc_metadata and "ingestion_attempts" in self.doc_metadata:
            try:
                return int(self.doc_metadata["ingestion_attempts"])
            except (TypeError, ValueError):
                return None
        return None


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    kb_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EMBEDDING_TYPE, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")
    knowledge_base = relationship("KnowledgeBase", back_populates="chunks")
