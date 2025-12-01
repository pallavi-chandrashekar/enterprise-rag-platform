from functools import cached_property
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @cached_property
    def model(self) -> SentenceTransformer:
        model = SentenceTransformer(self.settings.embedding_model_name)
        # Validate embedding dimension to match PGVector column.
        dim = model.get_sentence_embedding_dimension()
        if dim != self.settings.vector_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: model={dim} config={self.settings.vector_dimension}. "
                "Update settings.vector_dimension or choose a model with matching dimension."
            )
        return model

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        embeddings = self.model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=self.settings.normalize_embeddings)
        return np.asarray(embeddings, dtype=np.float32).tolist()
