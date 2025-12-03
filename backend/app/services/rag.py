import uuid

from sqlalchemy.orm import Session

from app.services.embeddings import EmbeddingService
from app.services.llm import LLMClient
from app.models.entities import Chunk
from app.schemas.models import RAGSource


class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = EmbeddingService()
        self.llm = LLMClient()

    def search(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, query_text: str, top_k: int) -> list[RAGSource]:
        query_vec = self.embedder.embed_texts([query_text])[0]
        distance = Chunk.embedding.cosine_distance(query_vec)

        results = (
            self.db.query(Chunk, distance.label("score"))
            .filter(Chunk.tenant_id == tenant_id, Chunk.kb_id == kb_id)
            .order_by(distance)
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
            for chunk, _score in results
        ]

    def answer(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, query_text: str, top_k: int, max_tokens: int = 128) -> tuple[str, list[RAGSource]]:
        sources = self.search(tenant_id, kb_id, query_text, top_k)
        context = "\n\n".join(f"- {src.content}" for src in sources)
        prompt = f"Answer the question using the context.\n\nContext:\n{context}\n\nQuestion: {query_text}\nAnswer:"
        answer = self.llm.generate(prompt, max_tokens=max_tokens)
        return answer, sources
