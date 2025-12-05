from functools import cached_property
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers.cross_encoder import CrossEncoder


class RerankingService:
    def __init__(self) -> None:
        self.settings = settings

    @cached_property
    def model(self) -> "CrossEncoder":
        # CrossEncoder is an optional dependency, so we import it here.
        try:
            from sentence_transformers.cross_encoder import CrossEncoder
        except ImportError as exc:
            raise ImportError("sentence_transformers.cross_encoder is not installed. Please install it with `pip install sentence-transformers`.") from exc

        # Use a default model if not configured, for easier local setup.
        model_name = self.settings.reranker_model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        return CrossEncoder(model_name)

    def score_and_sort(self, query: str, contents: list[str]) -> list[int]:
        """
        Scores document contents against a query and returns the indices of the documents sorted by relevance.
        """
        if not contents:
            return []

        pairs: list[list[str]] = [[query, content] for content in contents]
        scores = self.model.predict(pairs, convert_to_numpy=True)

        # Sort the scores in descending order and return the original indices
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return sorted_indices
