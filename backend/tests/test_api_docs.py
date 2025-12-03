import os

from fastapi.testclient import TestClient

# Use an in-memory SQLite DB for this simple healthcheck test and skip DB init to avoid pgvector/JSONB.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SKIP_DB_INIT"] = "1"

from app.main import app

client = TestClient(app)


def test_healthcheck():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
