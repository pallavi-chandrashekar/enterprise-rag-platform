import uuid

import pytest
from fastapi import HTTPException

from app.api.routes import _parse_metadata
from app.services.ingestion import IngestionPipeline


class DummyDB:
    """Minimal stub to satisfy pipeline constructor for unit-only tests."""


def test_chunk_text_overlaps():
    text = " ".join(str(i) for i in range(1, 26))  # 25 words
    pipeline = IngestionPipeline(db=DummyDB())

    chunks = pipeline._chunk_text(text, max_words=10, overlap=2)

    assert len(chunks) == 3
    # Overlap should preserve some words across adjacent chunks.
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_extract_text_plain_text():
    pipeline = IngestionPipeline(db=DummyDB())
    content = "Hello world\nthis is a test."
    extracted = pipeline._extract_text("sample.txt", content.encode("utf-8"))
    assert "Hello world" in extracted
    assert "this is a test." in extracted


def test_parse_metadata_valid_and_invalid():
    assert _parse_metadata('{"a":1}') == {"a": 1}
    assert _parse_metadata("") is None
    with pytest.raises(HTTPException):
        _parse_metadata("not-json")

