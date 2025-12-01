import io
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Chunk, Document
from app.services.embeddings import EmbeddingService


class IngestionPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = EmbeddingService()

    def process_uploaded_file(self, document: Document, file_bytes: bytes) -> None:
        text = self._extract_text(document.filename, file_bytes)
        chunks = self._chunk_text(text)
        if not chunks:
            raise ValueError("No text found in document")
        self.process_document(document, chunks)

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

    def _extract_text(self, filename: str, data: bytes) -> str:
        ext = Path(filename).suffix.lower()
        if ext in {".txt", ".md", ".text"}:
            return data.decode("utf-8", errors="ignore")
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:  # pragma: no cover - runtime guard
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="pypdf not installed") from exc
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if ext == ".docx":
            try:
                import docx
            except ImportError as exc:  # pragma: no cover - runtime guard
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="python-docx not installed") from exc
            doc = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

    def _chunk_text(self, text: str, max_words: int = 220, overlap: int = 40) -> list[str]:
        # Basic word-based chunking with overlap to keep context connected.
        words = text.split()
        if not words:
            return []
        chunks: list[str] = []
        start = 0
        step = max_words - overlap if max_words > overlap else max_words
        while start < len(words):
            end = start + max_words
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks
