import uuid
from collections import defaultdict
from typing import Optional

from sqlalchemy import union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.services.embeddings import EmbeddingService
from app.services.llm import LLMClient
from app.services.rerank import RerankingService
from app.models.entities import Chunk
from app.schemas.models import RAGSource

class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = EmbeddingService()
        self.llm = LLMClient()
        self.reranker = RerankingService()

    def _hybrid_search(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, query_text: str, top_k: int) -> list[RAGSource]:
        query_vec = self.embedder.embed_texts([query_text])[0]

        # Vector search query
        vector_query = (
            self.db.query(
                Chunk.id.label("id"),
                func.rank().over(order_by=Chunk.embedding.cosine_distance(query_vec)).label("rank"),
            )
            .filter(Chunk.tenant_id == tenant_id, Chunk.kb_id == kb_id)
            .limit(top_k)
            .subquery()
        )

        # Full-text search query
        fulltext_query = (
            self.db.query(
                Chunk.id.label("id"),
                func.rank().over(order_by=func.ts_rank_cd(Chunk.content_tsv, func.to_tsquery(query_text)).desc()).label("rank"),
            )
            .filter(Chunk.content_tsv.match(query_text, postgresql_regconfig="english"))
            .filter(Chunk.tenant_id == tenant_id, Chunk.kb_id == kb_id)
            .limit(top_k)
            .subquery()
        )
        
        # Combine the results
        combined_query = union_all(vector_query.select(), fulltext_query.select()).alias("combined_query")
        
        ranked_chunks = self.db.query(combined_query).all()
        
        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        k = 60  # RRF constant
        for id, rank in ranked_chunks:
            rrf_scores[id] += 1 / (k + rank)

        # Sort by RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda id: rrf_scores[id], reverse=True)

        # Fetch the actual Chunk objects for the unique IDs
        chunks = self.db.query(Chunk).filter(Chunk.id.in_(sorted_chunk_ids)).all()
        
        # Create a dictionary for quick lookup
        chunk_map = {chunk.id: chunk for chunk in chunks}
        
        # Create the final list of RAGSource objects, sorted by RRF score
        results = [
            RAGSource(
                document_id=str(chunk_map[chunk_id].document_id),
                chunk_id=str(chunk_id),
                content=chunk_map[chunk_id].content,
                metadata=chunk_map[chunk_id].chunk_metadata,
            )
            for chunk_id in sorted_chunk_ids
        ]

        return results[:top_k]

    def search(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, query_text: str, top_k: int) -> list[RAGSource]:
        return self._hybrid_search(tenant_id, kb_id, query_text, top_k)

    def rerank(self, query_text: str, sources: list[RAGSource], top_k: int) -> list[RAGSource]:
        if not sources:
            return []

        contents = [source.content for source in sources]
        sorted_indices = self.reranker.score_and_sort(query_text, contents)

        # Reorder the original sources based on the reranked indices
        reranked_sources = [sources[i] for i in sorted_indices]
        return reranked_sources[:top_k]

    def answer(
        self,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        query_text: str,
        top_k: int,
        max_tokens: int = 128,
        use_rerank: bool = True,
    ) -> tuple[str, list[RAGSource]]:
        # Initial retrieval gets more documents than required
        retrieval_k = top_k * 5
        sources = self.search(tenant_id, kb_id, query_text, retrieval_k)

        if use_rerank and self.reranker.model:
            final_sources = self.rerank(query_text, sources, top_k)
        else:
            final_sources = sources[:top_k]

        context = "\n\n".join(f"- {src.content}" for src in final_sources)
        prompt = f"Answer the question using the context.\n\nContext:\n{context}\n\nQuestion: {query_text}\nAnswer:"
        answer = self.llm.generate(prompt, max_tokens=max_tokens)
        return answer, final_sources
