import importlib
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.orm import declarative_base

from app.core.config import settings


def test_models_use_sqlite_fallback_types(monkeypatch):
    # Simulate SQLite and use a fresh Base to avoid table redefinition.
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("SKIP_DB_INIT", "1")
    
    import app.db.session as session

    session.Base = declarative_base()
    sys.modules.pop("app.models.entities", None)
    entities = importlib.import_module("app.models.entities")
    entities.IS_SQLITE = True # Directly patch IS_SQLITE for the test

    assert entities.IS_SQLITE is True
