import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.entities import Chunk
from app.schemas.models import RAGSource, SearchType
from app.services.rag import RAGService


@pytest.fixture
def mock_rag_service():
    db = MagicMock() # Make db a MagicMock directly
    with patch('app.services.rag.EmbeddingService') as MockEmbeddingService, \
         patch('app.services.rag.RerankingService') as MockRerankingService, \
         patch('app.services.rag.LLMClient') as MockLLMClient:

        mock_embedder_instance = MockEmbeddingService.return_value
        mock_embedder_instance.embed_texts.return_value = [[0.1] * 384] * 2  # Default embedding

        mock_reranker_instance = MockRerankingService.return_value
        mock_reranker_instance.model.predict.return_value = [0.9, 0.1] # Default rerank scores

        mock_llm_instance = MockLLMClient.return_value
        mock_llm_instance.generate.return_value = "Mocked LLM answer"

        service = RAGService(db)
        service.embedder = mock_embedder_instance
        service.reranker = mock_reranker_instance
        service.llm = mock_llm_instance
        return service


def create_mock_chunk(content: str, id: uuid.UUID, document_id: uuid.UUID) -> Chunk:
    return Chunk(
        id=id,
        tenant_id=uuid.uuid4(),
        kb_id=uuid.uuid4(),
        document_id=document_id,
        content=content,
        embedding=[0.1] * 384, # Default embedding
        chunk_metadata={},
    )


def test_hybrid_search_low_semantic_high_keyword(mock_rag_service):
    """
    Test case: Query has low semantic similarity to chunks but high keyword overlap.
    Expected: Full-text search should bring these documents up, and RRF should combine.
    """
    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    query_text = "specific product code XYZ123"

    # Mock chunks
    doc_id_1 = uuid.uuid4()
    doc_id_2 = uuid.uuid4()
    chunk_id_1 = uuid.uuid4()
    chunk_id_2 = uuid.uuid4()

    mock_chunk_1 = create_mock_chunk(
        "The quick brown fox jumps over the lazy dog. Product code is XYZ123.", chunk_id_1, doc_id_1
    )
    mock_chunk_2 = create_mock_chunk(
        "Another document with general information. No product code mentioned.", chunk_id_2, doc_id_2
    )

    # Mock database query results
    # Simulate vector search ranking chunk_2 higher due to general semantic similarity,
    # but full-text search ranking chunk_1 higher due to exact keyword match.
    mock_vector_query_builder = MagicMock()
    mock_fulltext_query_builder = MagicMock()
    mock_combined_query_executor = MagicMock()
    mock_chunk_fetcher = MagicMock()

    mock_rag_service.db.query.side_effect = [
        mock_vector_query_builder,
        mock_fulltext_query_builder,
        mock_combined_query_executor,
        mock_chunk_fetcher,
    ]
    
    # Configure mock_vector_query_builder chain
    mock_vector_query_builder.filter.return_value.limit.return_value.subquery.return_value.select.return_value = MagicMock()

    # Configure mock_fulltext_query_builder chain
    mock_fulltext_query_builder.filter.return_value.filter.return_value.limit.return_value.subquery.return_value.select.return_value = MagicMock()

    # Configure mock_combined_query_executor
    # Ranks set to ensure chunk_id_1 wins with RRF: 1/(60+1) + 1/(60+10) > 1/(60+2) + 1/(60+10)
    mock_combined_query_executor.all.return_value = [
        (chunk_id_1, 1),  # Full-text (high keyword)
        (chunk_id_2, 2),  # Vector (some semantic)
        (chunk_id_1, 10), # Vector (low semantic for keyword)
        (chunk_id_2, 10), # Full-text (low keyword for general)
    ]
    
    # Configure mock_chunk_fetcher
    mock_chunk_fetcher.filter.return_value.all.return_value = [mock_chunk_1, mock_chunk_2]

    # Patch the direct call to cosine_distance
    with patch('app.services.rag.Chunk.embedding', new_callable=MagicMock) as mock_embedding_attr, \
         patch('app.services.rag.union_all', return_value=MagicMock(alias=MagicMock())) as mock_union_all: # Mock union_all

        mock_distance_obj = MagicMock()
        mock_distance_obj.label.return_value = "score" # mock the label method
        mock_embedding_attr.cosine_distance.return_value = mock_distance_obj

        # Explicitly mock func.ts_rank_cd and func.to_tsquery for the full-text query
        with patch('app.services.rag.func.ts_rank_cd', return_value=MagicMock(label=MagicMock(return_value="score"))), \
             patch('app.services.rag.func.to_tsquery', return_value="query_tsquery"):

            results = mock_rag_service.search(tenant_id, kb_id, query_text, top_k=1, search_type=SearchType.hybrid)

            # Expect chunk_1 to be the top result due to RRF combining strong full-text signal
            assert len(results) == 1
            assert results[0].chunk_id == str(mock_chunk_1.id)
            assert results[0].content == mock_chunk_1.content


def test_hybrid_search_semantically_rich_no_keywords(mock_rag_service):
    """
    Test case: Query is semantically rich but has no exact keyword overlap with top vector results.
    Expected: Vector search should prioritize these, and RRF should ensure they are ranked high.
    """
    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    query_text = "information about advanced machine learning techniques"

    # Mock chunks
    doc_id_1 = uuid.uuid4()
    doc_id_2 = uuid.uuid4()
    chunk_id_1 = uuid.uuid4()
    chunk_id_2 = uuid.uuid4()

    mock_chunk_1 = create_mock_chunk(
        "This document discusses deep learning and neural networks.", chunk_id_1, doc_id_1
    )
    mock_chunk_2 = create_mock_chunk(
        "A recipe for apple pie, with baking instructions.", chunk_id_2, doc_id_2
    )

    # Mock database query results
    # Simulate vector search ranking chunk_1 higher, but full-text search ranking chunk_2 higher due to some common words (e.g., "information").
    mock_vector_query_builder = MagicMock()
    mock_fulltext_query_builder = MagicMock()
    mock_combined_query_executor = MagicMock()
    mock_chunk_fetcher = MagicMock()

    mock_rag_service.db.query.side_effect = [
        mock_vector_query_builder,
        mock_fulltext_query_builder,
        mock_combined_query_executor,
        mock_chunk_fetcher,
    ]
    
    # Configure mock_vector_query_builder chain
    mock_vector_query_builder.filter.return_value.limit.return_value.subquery.return_value.select.return_value = MagicMock()

    # Configure mock_fulltext_query_builder chain
    mock_fulltext_query_builder.filter.return_value.filter.return_value.limit.return_value.subquery.return_value.select.return_value = MagicMock()

    # Configure mock_combined_query_executor
    # Ranks set to ensure chunk_id_1 wins with RRF: 1/(60+1) + 1/(60+10) > 1/(60+2) + 1/(60+10)
    mock_combined_query_executor.all.return_value = [
        (chunk_id_1, 1),  # Vector (high semantic)
        (chunk_id_2, 2),  # Full-text (some keyword)
        (chunk_id_1, 10), # Full-text (low keyword for semantic)
        (chunk_id_2, 10), # Vector (low semantic for general)
    ]

    # Configure mock_chunk_fetcher
    mock_chunk_fetcher.filter.return_value.all.return_value = [mock_chunk_1, mock_chunk_2]

    # Patch the direct call to cosine_distance
    with patch('app.services.rag.Chunk.embedding', new_callable=MagicMock) as mock_embedding_attr, \
         patch('app.services.rag.union_all', return_value=MagicMock(alias=MagicMock())) as mock_union_all: # Mock union_all

        mock_distance_obj = MagicMock()
        mock_distance_obj.label.return_value = "score" # mock the label method
        mock_embedding_attr.cosine_distance.return_value = mock_distance_obj

        # Explicitly mock func.ts_rank_cd and func.to_tsquery for the full-text query
        with patch('app.services.rag.func.ts_rank_cd', return_value=MagicMock(label=MagicMock(return_value="score"))), \
             patch('app.services.rag.func.to_tsquery', return_value="query_tsquery"):

            results = mock_rag_service.search(tenant_id, kb_id, query_text, top_k=1, search_type=SearchType.hybrid)

            # Expect chunk_1 to be the top result due to RRF combining strong vector signal
            assert len(results) == 1
            assert results[0].chunk_id == str(mock_chunk_1.id)
            assert results[0].content == mock_chunk_1.content
