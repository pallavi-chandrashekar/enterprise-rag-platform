from functools import cached_property
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = settings

    @cached_property
    def model(self) -> SentenceTransformer:
        model = SentenceTransformer(self.settings.EMBEDDING_MODEL_NAME)
        # Validate embedding dimension to match PGVector column.
        dim = model.get_sentence_embedding_dimension()
        if dim != self.settings.VECTOR_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: model={dim} config={self.settings.VECTOR_DIMENSION}. "
                "Update settings.VECTOR_DIMENSION or choose a model with matching dimension."
            )
        return model

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        embeddings = self.model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=self.settings.NORMALIZE_EMBEDDINGS)
        return np.asarray(embeddings, dtype=np.float32).tolist()
