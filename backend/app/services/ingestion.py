import io
import logging
from pathlib import Path
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from bs4 import BeautifulSoup  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from app.models.entities import Chunk, Document
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = EmbeddingService()

    def process_uploaded_file(self, document: Document, file_bytes: bytes) -> None:
        try:
            text = self._extract_text(document.filename, file_bytes)
            chunks = self._chunk_text(text)
            if not chunks:
                raise ValueError("No text found in document")
            self._increment_attempt(document)
            self.process_document(document, chunks)
        except Exception as e:
            logger.error(
                f"Failed to process document {document.id} for tenant {document.tenant_id}: {e}",
                exc_info=True,
            )
            self.mark_failed(document.id, str(e))

    def process_document(self, document: Document, chunks: list[str]) -> None:
        embeddings = self.embedder.embed_texts(chunks)
        with self.db.begin():
            # If retrying, clear prior chunks for this document to avoid duplicates.
            self.db.query(Chunk).filter(Chunk.document_id == document.id, Chunk.tenant_id == document.tenant_id).delete(synchronize_session=False)
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
            self._merge_metadata(document, {"last_error": None})
            self.db.add(document)

    def mark_failed(self, document_id: UUID, reason: str) -> None:
        doc = self.db.get(Document, document_id)
        if not doc:
            return
        with self.db.begin():
            doc.status = "FAILED"
            self._merge_metadata(doc, {"last_error": reason})
            self.db.add(doc)

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
        if ext in {".html", ".htm"}:
            soup = BeautifulSoup(data, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            return " ".join(text.split())
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
            slice_words = words[start:end]
            if not slice_words:
                break
            chunk = " ".join(slice_words).strip()
            if chunk:
                chunks.append(chunk)
            # If this was a short final slice (smaller than overlap), stop.
            if len(slice_words) < overlap and start > 0:
                break
            start += step
        return chunks

    def _increment_attempt(self, document: Document) -> None:
        attempts = 0
        if document.doc_metadata and "ingestion_attempts" in document.doc_metadata:
            try:
                attempts = int(document.doc_metadata["ingestion_attempts"])
            except (TypeError, ValueError):
                attempts = 0
        attempts += 1
        self._merge_metadata(document, {"ingestion_attempts": attempts})
        document.status = "PROCESSING"
        self.db.add(document)

    def _merge_metadata(self, document: Document, updates: dict[str, object]) -> None:
        meta = document.doc_metadata.copy() if document.doc_metadata else {}
        meta.update(updates)
        document.doc_metadata = meta
