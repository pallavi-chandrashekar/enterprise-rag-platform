import importlib
import types


def test_models_use_sqlite_fallback_types(monkeypatch):
    # Simulate SQLite DATABASE_URL and reload entities to pick up fallback types.
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    entities = importlib.reload(importlib.import_module("app.models.entities"))

    assert entities.IS_SQLITE is True
    # UUID_TYPE should be String for sqlite
    assert "String" in entities.UUID_TYPE.__class__.__name__
    # Embedding type should fall back to JSON for sqlite
    assert entities.EMBEDDING_TYPE.__class__.__name__ == "JSON"
