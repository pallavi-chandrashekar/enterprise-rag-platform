import importlib
import sys

from sqlalchemy.orm import declarative_base


def test_models_use_sqlite_fallback_types(monkeypatch):
    # Simulate SQLite and use a fresh Base to avoid table redefinition.
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("SKIP_DB_INIT", "1")

    import app.db.session as session

    session.Base = declarative_base()
    sys.modules.pop("app.models.entities", None)
    entities = importlib.import_module("app.models.entities")

    assert entities.IS_SQLITE is True
    assert "String" in entities.UUID_TYPE.__class__.__name__
    assert entities.EMBEDDING_TYPE.__class__.__name__ == "JSON"
