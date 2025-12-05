from unittest.mock import MagicMock, patch

from app.services.ingestion import IngestionPipeline
from app.models.entities import Document


def test_process_uploaded_file_handles_errors():
    """
    Tests that the IngestionPipeline's process_uploaded_file method
    catches exceptions and marks the document as FAILED.
    """
    mock_db = MagicMock()
    pipeline = IngestionPipeline(db=mock_db)

    # Create a mock document object
    mock_document = Document(id="a-doc-id", tenant_id="a-tenant-id")
    file_bytes = b"some file content"
    error_message = "Unsupported file type: .xyz"

    # Patch the _extract_text method to raise a specific error
    with patch.object(pipeline, "_extract_text", side_effect=ValueError(error_message)) as mock_extract, \
         patch.object(pipeline, "mark_failed") as mock_mark_failed:

        pipeline.process_uploaded_file(mock_document, file_bytes)

        # Assert that _extract_text was called
        mock_extract.assert_called_once_with(mock_document.filename, file_bytes)

        # Assert that mark_failed was called with the correct reason
        mock_mark_failed.assert_called_once_with(mock_document.id, error_message)

