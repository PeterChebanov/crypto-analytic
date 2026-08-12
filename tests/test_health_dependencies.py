"""Dependency health probes."""

from __future__ import annotations

from crypto_intel.health.dependencies import check_external_dependencies


def test_check_external_dependencies_shape(monkeypatch) -> None:
    def fake_get(url, params=None, timeout=8.0):  # noqa: ANN001
        class Resp:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

        return Resp()

    monkeypatch.setattr("crypto_intel.health.dependencies.httpx.get", fake_get)
    payload = check_external_dependencies()
    assert payload["ok"] is True
    assert payload["level"] == "ok"
    assert len(payload["checks"]) >= 4
    assert all("name" in row and "ok" in row for row in payload["checks"])
