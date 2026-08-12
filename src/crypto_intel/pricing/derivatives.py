"""Binance Futures public derivatives signals (OI + funding)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import httpx

from crypto_intel.logging_ext.session_log import SessionLogger
from crypto_intel.pricing.history import binance_spot_pair, period_to_days
from crypto_intel.settings import get_settings
from crypto_intel.tools.symbols import normalize_symbol

_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
_OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"

# Crowding thresholds on average funding over the window (decimal, e.g. 0.001 = 0.1%).
FUNDING_EXTREME = 0.0005


@dataclass(frozen=True, slots=True)
class DerivativesSnapshot:
    symbol: str
    period: str
    available: bool
    funding_current: float | None
    funding_avg: float | None
    funding_crowded: bool
    oi_start: float | None
    oi_end: float | None
    oi_change_pct: float | None
    note: str


def _mock_derivatives(symbol: str, period: str) -> DerivativesSnapshot:
    return DerivativesSnapshot(
        symbol=symbol,
        period=period,
        available=True,
        funding_current=0.0001,
        funding_avg=0.00008,
        funding_crowded=False,
        oi_start=1_000_000.0,
        oi_end=1_050_000.0,
        oi_change_pct=5.0,
        note="mock derivatives: neutral funding, mild OI build",
    )


def fetch_derivatives_snapshot(
    cryptocurrency: str,
    period: str,
    *,
    session_logger: SessionLogger | None = None,
) -> DerivativesSnapshot:
    symbol = normalize_symbol(cryptocurrency)
    days = period_to_days(period)
    pair = binance_spot_pair(symbol)

    if get_settings().use_mock_tools:
        snap = _mock_derivatives(symbol, period)
        if session_logger is not None:
            session_logger.log(
                kind="derivatives",
                source="mock",
                request={"symbol": symbol, "days": days},
                response=asdict(snap),
            )
        return snap

    try:
        funding_current = None
        premium = httpx.get(_PREMIUM_URL, params={"symbol": pair}, timeout=15.0)
        premium.raise_for_status()
        premium_body = premium.json()
        if isinstance(premium_body, dict) and premium_body.get("lastFundingRate") is not None:
            funding_current = float(premium_body["lastFundingRate"])

        start_ms = int(
            (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
        )
        funding_hist = httpx.get(
            _FUNDING_URL,
            params={"symbol": pair, "startTime": start_ms, "limit": 1000},
            timeout=15.0,
        )
        funding_hist.raise_for_status()
        funding_rows = funding_hist.json()
        rates: list[float] = []
        if isinstance(funding_rows, list):
            for row in funding_rows:
                if isinstance(row, dict) and row.get("fundingRate") is not None:
                    rates.append(float(row["fundingRate"]))
        funding_avg = sum(rates) / len(rates) if rates else funding_current
        crowded = (
            funding_avg is not None and abs(funding_avg) >= FUNDING_EXTREME
        )

        # openInterestHist period units: "5m","15m","30m","1h","2h","4h","6h","12h","1d"
        oi_period = "1h" if days <= 7 else "4h"
        oi_resp = httpx.get(
            _OI_HIST_URL,
            params={
                "symbol": pair,
                "period": oi_period,
                "limit": min(500, max(days * (24 if oi_period == "1h" else 6), 10)),
            },
            timeout=15.0,
        )
        oi_resp.raise_for_status()
        oi_rows = oi_resp.json()
        oi_start = oi_end = oi_change = None
        if isinstance(oi_rows, list) and len(oi_rows) >= 2:
            first = oi_rows[0]
            last = oi_rows[-1]
            if isinstance(first, dict) and isinstance(last, dict):
                oi_start = float(first.get("sumOpenInterest") or first.get("sumOpenInterestValue") or 0)
                oi_end = float(last.get("sumOpenInterest") or last.get("sumOpenInterestValue") or 0)
                if oi_start > 0:
                    oi_change = (oi_end - oi_start) / oi_start * 100.0

        note_parts = []
        if crowded:
            note_parts.append("funding crowded")
        else:
            note_parts.append("funding neutral")
        if oi_change is not None:
            note_parts.append(f"OI Δ {oi_change:.2f}%")
        snap = DerivativesSnapshot(
            symbol=symbol,
            period=period,
            available=True,
            funding_current=funding_current,
            funding_avg=funding_avg,
            funding_crowded=crowded,
            oi_start=oi_start,
            oi_end=oi_end,
            oi_change_pct=oi_change,
            note="; ".join(note_parts),
        )
        if session_logger is not None:
            session_logger.log(
                kind="derivatives",
                source="binance_futures",
                request={"symbol": symbol, "pair": pair, "days": days},
                response=asdict(snap),
            )
        return snap
    except Exception as exc:
        snap = DerivativesSnapshot(
            symbol=symbol,
            period=period,
            available=False,
            funding_current=None,
            funding_avg=None,
            funding_crowded=False,
            oi_start=None,
            oi_end=None,
            oi_change_pct=None,
            note=f"unavailable: {exc}",
        )
        if session_logger is not None:
            session_logger.log(
                kind="derivatives",
                source="binance_futures",
                request={"symbol": symbol, "days": days},
                error=str(exc),
                response=asdict(snap),
            )
        return snap
