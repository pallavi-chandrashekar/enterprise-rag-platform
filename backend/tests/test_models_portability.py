import importlib
import types

import sqlalchemy


def test_models_use_sqlite_fallback_types(monkeypatch):
    # Reload the module in isolation to avoid clobbering the main Base registry.
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    # Use importlib to create a fresh module namespace.
    entities = importlib.import_module("app.models.entities")
    entities = importlib.reload(entities)

    assert entities.IS_SQLITE is True
    # UUID_TYPE should be String for sqlite
    assert "String" in entities.UUID_TYPE.__class__.__name__
    # Embedding type should fall back to JSON for sqlite
    assert entities.EMBEDDING_TYPE.__class__.__name__ == "JSON"
