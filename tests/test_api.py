"""API smoke tests (no full research execution)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from crypto_intel.api.app import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ui_index_served() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "CryptoIntel" in response.text
    assert "cryptocurrency" in response.text


def test_get_research_not_found(monkeypatch) -> None:
    from crypto_intel.api import app as api_app

    def _missing(_session, _run_id):
        return None

    monkeypatch.setattr(api_app, "get_run", _missing)
    client = TestClient(app)
    response = client.get(f"/research/{uuid4()}")
    assert response.status_code == 404
