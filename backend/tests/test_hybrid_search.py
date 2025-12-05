from unittest.mock import MagicMock, patch
import uuid
from app.models.entities import Chunk

from app.services.rag import RAGService
from app.schemas.models import RAGSource


def test_search_calls_hybrid_search():
    """
    Tests that the search method calls the _hybrid_search method.
    """
    mock_db = MagicMock()
    rag_service = RAGService(db=mock_db)

    tenant_id = "a-tenant"
    kb_id = "a-kb"
    query = "What is the answer?"
    top_k = 2

    with patch.object(rag_service, "_hybrid_search") as mock_hybrid_search:
        rag_service.search(tenant_id, kb_id, query, top_k)
        mock_hybrid_search.assert_called_once_with(tenant_id, kb_id, query, top_k)

def test_hybrid_search_with_rrf():
    """
    Tests the _hybrid_search method with RRF.
    """
    mock_db = MagicMock()

    with patch('app.services.rag.EmbeddingService'), \
         patch('app.services.rag.union_all') as mock_union_all:

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

        results = rag_service._hybrid_search(tenant_id, kb_id, query, top_k)

        # Expected RRF scores and order
        # chunk0: 1/(60+1) + 1/(60+2) = 0.0325
        # chunk1: 1/(60+2) = 0.0161
        # chunk2: 1/(60+1) = 0.0164
        # Expected order: chunk0, chunk2

        assert len(results) == top_k
        assert results[0].chunk_id == str(mock_chunks[0].id)
        assert results[1].chunk_id == str(mock_chunks[2].id)
