"""Startup / UI dependency probes for external venues."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx


def _probe(name: str, url: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        response = httpx.get(url, params=params, timeout=8.0)
        response.raise_for_status()
        return {"name": name, "ok": True, "detail": f"HTTP {response.status_code}"}
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        return {
            "name": name,
            "ok": False,
            "detail": f"HTTP {code} Unauthorized" if code == 401 else f"HTTP {code}",
        }
    except Exception as exc:
        return {"name": name, "ok": False, "detail": f"request failed: {exc}"}


def check_external_dependencies() -> dict[str, Any]:
    """Ping public venues used by research/forecast."""
    probes = [
        ("binance_spot", "https://api.binance.com/api/v3/ticker/price", {"symbol": "ETHUSDT"}),
        ("kraken_spot", "https://api.kraken.com/0/public/Ticker", {"pair": "ETHUSD"}),
        (
            "coingecko",
            "https://api.coingecko.com/api/v3/simple/price",
            {"ids": "ethereum", "vs_currencies": "usd"},
        ),
        (
            "binance_klines",
            "https://api.binance.com/api/v3/klines",
            {"symbol": "ETHUSDT", "interval": "1h", "limit": "1"},
        ),
        (
            "binance_futures",
            "https://fapi.binance.com/fapi/v1/premiumIndex",
            {"symbol": "ETHUSDT"},
        ),
        (
            "cryptocompare_news",
            "https://min-api.cryptocompare.com/data/v2/news/",
            {"lang": "EN"},
        ),
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [
            pool.submit(_probe, name, url, params=params)
            for name, url, params in probes
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda row: row["name"])
    failed = [row for row in results if not row["ok"]]
    hard_names = {"binance_spot", "kraken_spot", "coingecko", "binance_klines"}
    hard_failed = [row for row in failed if row["name"] in hard_names]
    soft_failed = [row for row in failed if row["name"] not in hard_names]
    if hard_failed:
        ok = False
        level = "error"
        summary = "; ".join(f"{r['name']}: {r['detail']}" for r in hard_failed[:3])
    elif soft_failed:
        ok = True
        level = "warn"
        summary = "; ".join(f"{r['name']}: {r['detail']}" for r in soft_failed[:3])
    else:
        ok = True
        level = "ok"
        summary = "All dependency probes succeeded"
    return {
        "ok": ok,
        "level": level,
        "summary": summary,
        "checks": results,
    }
