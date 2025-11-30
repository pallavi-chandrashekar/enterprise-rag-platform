from typing import Iterable

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        # TODO: initialize local model or client using settings.embedding_model_name

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        # TODO: replace with real embedding model
        return [[0.0] * self.settings.vector_dimension for _ in texts]
