import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://agent_rag_app:test-only@127.0.0.1:5432/agent_rag",
)

from fastapi.testclient import TestClient

from app.main import app


def test_liveness_does_not_require_database():
    response = TestClient(app).get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database(monkeypatch):
    monkeypatch.setattr("app.api.health.database_is_ready", lambda: True)
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}
