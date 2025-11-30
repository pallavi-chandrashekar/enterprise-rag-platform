from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import Chunk, Document
from app.services.embeddings import EmbeddingService


class IngestionPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = EmbeddingService()

    def process_document(self, document: Document, chunks: list[str]) -> None:
        embeddings = self.embedder.embed_texts(chunks)
        chunk_records = []
        for content, embedding in zip(chunks, embeddings):
            chunk_records.append(
                Chunk(
                    tenant_id=document.tenant_id,
                    kb_id=document.kb_id,
                    document_id=document.id,
                    content=content,
                    embedding=embedding,
                )
            )
        self.db.add_all(chunk_records)
        document.status = "READY"
        self.db.add(document)
        self.db.commit()

    def mark_failed(self, document_id: UUID, reason: str) -> None:
        doc = self.db.get(Document, document_id)
        if not doc:
            return
        doc.status = f"FAILED: {reason}"
        self.db.add(doc)
        self.db.commit()
