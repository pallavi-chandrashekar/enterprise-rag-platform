import os

# Use lightweight SQLite for tests to avoid Postgres dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
