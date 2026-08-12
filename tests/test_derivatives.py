"""Unit tests for Binance futures derivatives snapshot (mock path)."""

from __future__ import annotations

from crypto_intel.pricing.derivatives import _mock_derivatives, fetch_derivatives_snapshot
from crypto_intel.settings import get_settings


def test_mock_derivatives_helper() -> None:
    snap = _mock_derivatives("ETH", "7d")
    assert snap.available is True
    assert snap.funding_avg is not None
    assert snap.oi_change_pct is not None


def test_fetch_derivatives_respects_settings(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("USE_MOCK_TOOLS", "true")
    get_settings.cache_clear()
    try:
        snap = fetch_derivatives_snapshot("ETH", "7d")
        assert snap.available is True
        assert "mock" in snap.note.lower() or snap.oi_change_pct is not None
    finally:
        get_settings.cache_clear()
