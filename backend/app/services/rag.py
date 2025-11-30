from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Chunk
from app.schemas.models import RAGSource


class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        # TODO: initialize vector index / PGVector client and LLM client

    def search(self, kb_id: str, top_k: int) -> list[RAGSource]:
        # TODO: replace with PGVector similarity search using embeddings
        chunks = (
            self.db.query(Chunk)
            .filter(Chunk.kb_id == kb_id)
            .order_by(Chunk.created_at.desc())
            .limit(top_k)
            .all()
        )
        return [
            RAGSource(
                document_id=str(chunk.document_id),
                chunk_id=str(chunk.id),
                content=chunk.content,
                metadata=chunk.chunk_metadata,
            )
            for chunk in chunks
        ]
