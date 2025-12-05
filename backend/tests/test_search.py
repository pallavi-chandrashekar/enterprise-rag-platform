from unittest.mock import MagicMock, patch
import uuid
from app.models.entities import Chunk

from app.services.rag import RAGService
from app.schemas.models import RAGSource, SearchType


def test_search_with_hybrid_search():
    """
    Tests the search method with hybrid search.
    """
    mock_db = MagicMock()

    with patch('app.services.rag.EmbeddingService'), \
         patch('app.services.rag.union_all') as mock_union_all, \
         patch('app.services.rag.Chunk.embedding', new_callable=MagicMock) as mock_embedding:
        
        mock_distance = MagicMock()
        mock_embedding.cosine_distance.return_value = mock_distance

        rag_service = RAGService(db=mock_db)

        tenant_id = "a-tenant"
        kb_id = "a-kb"
        query = "What is the answer?"
        top_k = 2

        # Mock data
        mock_chunks = [
            Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk1", chunk_metadata={}),
            Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk2", chunk_metadata={}),
            Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk3", chunk_metadata={}),
        ]

        # Mock ranked results
        ranked_results = [
            (mock_chunks[0].id, 1),
            (mock_chunks[1].id, 2),
            (mock_chunks[2].id, 1),
            (mock_chunks[0].id, 2),
        ]
        
        # Mock the database queries
        mock_db.query.return_value.all.return_value = ranked_results
        mock_db.query.return_value.filter.return_value.all.return_value = mock_chunks

        # Mock the combined query from union_all
        mock_combined_query = MagicMock()
        mock_union_all.return_value.alias.return_value = mock_combined_query

        results = rag_service.search(tenant_id, kb_id, query, top_k, SearchType.hybrid)

        # Expected RRF scores and order
        # chunk0: 1/(60+1) + 1/(60+2) = 0.0325
        # chunk1: 1/(60+2) = 0.0161
        # chunk2: 1/(60+1) = 0.0164
        # Expected order: chunk0, chunk2

        assert len(results) == top_k
        assert results[0].chunk_id == str(mock_chunks[0].id)
        assert results[1].chunk_id == str(mock_chunks[2].id)


def test_search_with_vector_search():
    """
    Tests the search method with vector search.
    """
    mock_db = MagicMock()

    with patch('app.services.rag.EmbeddingService'), \
         patch('app.services.rag.Chunk.embedding', new_callable=MagicMock) as mock_embedding:

        mock_distance = MagicMock()
        mock_distance.label.return_value = "score"
        mock_embedding.cosine_distance.return_value = mock_distance
        
        rag_service = RAGService(db=mock_db)

        tenant_id = "a-tenant"
        kb_id = "a-kb"
        query = "What is the answer?"
        top_k = 2

        # Mock data
        mock_chunks = [
            (Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk1", chunk_metadata={}), 0.1),
            (Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk2", chunk_metadata={}), 0.2),
        ]

        # Mock the database query
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_chunks

        results = rag_service.search(tenant_id, kb_id, query, top_k, SearchType.vector)

        assert len(results) == top_k
        assert results[0].chunk_id == str(mock_chunks[0][0].id)
        assert results[1].chunk_id == str(mock_chunks[1][0].id)


def test_search_with_full_text_search():
    """
    Tests the search method with full-text search.
    """
    mock_db = MagicMock()

    with patch('app.services.rag.EmbeddingService'):
        rag_service = RAGService(db=mock_db)

        tenant_id = "a-tenant"
        kb_id = "a-kb"
        query = "What is the answer?"
        top_k = 2

        # Mock data
        mock_chunks = [
            (Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk1", chunk_metadata={}), 0.8),
            (Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk2", chunk_metadata={}), 0.7),
        ]

        # Mock the database query
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_chunks

        results = rag_service.search(tenant_id, kb_id, query, top_k, SearchType.full_text)

        assert len(results) == top_k
        assert results[0].chunk_id == str(mock_chunks[0][0].id)
        assert results[1].chunk_id == str(mock_chunks[1][0].id)
