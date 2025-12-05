from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.rag import RAGService
from app.services.rerank import RerankingService
from app.schemas.models import RAGSource, SearchType


def test_reranking_service_sorts_indices():
    """Unit test to ensure the reranking service correctly sorts indices based on scores."""
    reranker = RerankingService()
    query = "test query"
    contents = ["doc1", "doc2", "doc3"]
    # Mock scores where doc3 is best, doc1 is second, doc2 is worst.
    mock_scores = [0.2, 0.1, 0.8]

    with patch('app.services.rerank.RerankingService.model', new_callable=PropertyMock) as mock_model:
        mock_model.return_value.predict.return_value = mock_scores
        sorted_indices = reranker.score_and_sort(query, contents)

        # Expect indices to be sorted by score: [2, 0, 1]
        assert sorted_indices == [2, 0, 1]
        mock_model.return_value.predict.assert_called_once()


def test_rag_service_with_rerank():
    """
    Tests that the RAGService calls the reranker and uses its output
    when `use_rerank` is True.
    """
    mock_db = MagicMock()
    rag_service = RAGService(db=mock_db)

    tenant_id = "a-tenant"
    kb_id = "a-kb"
    query = "What is the answer?"
    top_k = 2

    # Mock initial search results
    initial_sources = [
        RAGSource(document_id="doc1", chunk_id="c1", content="content1"),
        RAGSource(document_id="doc2", chunk_id="c2", content="content2"),
        RAGSource(document_id="doc3", chunk_id="c3", content="content3"),
    ]
    # Mock reranked results (reordered)
    reranked_sources = [
        initial_sources[2],  # doc3
        initial_sources[0],  # doc1
    ]

    with patch.object(rag_service, "search", return_value=initial_sources) as mock_search, \
         patch.object(rag_service, "rerank", return_value=reranked_sources) as mock_rerank, \
         patch.object(rag_service.llm, "generate", return_value="The answer.") as mock_llm_generate:

        answer, sources = rag_service.answer(
            tenant_id, kb_id, query, top_k=top_k, use_rerank=True, search_type=SearchType.hybrid
        )

        # Assert initial search was called to get candidates
        mock_search.assert_called_once_with(tenant_id, kb_id, query, top_k * 5, SearchType.hybrid)

        # Assert rerank was called with the initial sources
        mock_rerank.assert_called_once_with(query, initial_sources, top_k)

        # Assert the final sources are the ones from the reranker
        assert sources == reranked_sources

        # Assert the LLM context was built from the reranked sources
        expected_context = "\n\n".join(f"- {src.content}" for src in reranked_sources)
        expected_prompt = f"Answer the question using the context.\n\nContext:\n{expected_context}\n\nQuestion: {query}\nAnswer:"
        mock_llm_generate.assert_called_once_with(expected_prompt, max_tokens=128)
        assert answer == "The answer."


def test_rag_service_without_rerank():
    """
    Tests that the RAGService does NOT call the reranker and uses the initial
    search results when `use_rerank` is False.
    """
    mock_db = MagicMock()
    rag_service = RAGService(db=mock_db)

    tenant_id = "a-tenant"
    kb_id = "a-kb"
    query = "What is the answer?"
    top_k = 2

    initial_sources = [
        RAGSource(document_id="doc1", chunk_id="c1", content="content1"),
        RAGSource(document_id="doc2", chunk_id="c2", content="content2"),
        RAGSource(document_id="doc3", chunk_id="c3", content="content3"),
    ]
    # The final sources should be a simple slice of the initial search
    final_sources = initial_sources[:top_k]

    with patch.object(rag_service, "search", return_value=initial_sources) as mock_search, \
         patch.object(rag_service, "rerank") as mock_rerank, \
         patch.object(rag_service.llm, "generate", return_value="The answer.") as mock_llm_generate:

        answer, sources = rag_service.answer(
            tenant_id, kb_id, query, top_k=top_k, use_rerank=False, search_type=SearchType.hybrid
        )

        mock_search.assert_called_once_with(tenant_id, kb_id, query, top_k * 5, SearchType.hybrid)

        # Assert rerank was NOT called
        mock_rerank.assert_not_called()

        assert sources == final_sources

        expected_context = "\n\n".join(f"- {src.content}" for src in final_sources)
        expected_prompt = f"Answer the question using the context.\n\nContext:\n{expected_context}\n\nQuestion: {query}\nAnswer:"
        mock_llm_generate.assert_called_once_with(expected_prompt, max_tokens=128)
        assert answer == "The answer."
