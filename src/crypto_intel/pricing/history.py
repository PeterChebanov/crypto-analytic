"""Lookback OHLCV + TA feature pack (price, volume, ATR, swing S/R)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from crypto_intel.logging_ext.session_log import SessionLogger
from crypto_intel.settings import get_settings
from crypto_intel.tools.symbols import normalize_symbol

_PERIOD_DAYS = {
    "1d": 1,
    "7d": 7,
    "14d": 14,
    "30d": 30,
}

_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

_BINANCE_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "USDT": "USDTUSD",
}

ATR_PERIOD = 14
SWING_LEFT = 2
SWING_RIGHT = 2
ATR_STOP_MULT = 1.0
SR_METHOD = "nearest_swing_pivot"


@dataclass(frozen=True, slots=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class PriceSeriesStats:
    """Deterministic TA inputs for the forecast layer."""

    symbol: str
    period: str
    days: int
    candle_interval: str
    atr_period: int
    start_price: float
    end_price: float
    low: float
    high: float
    change_pct: float
    points: int
    atr: float
    support: float
    resistance: float
    volume_total: float
    volume_avg: float
    volume_last_vs_avg: float
    volume_at_support_ratio: float
    volume_at_resistance_ratio: float
    volume_confirm: bool


def period_to_days(period: str) -> int:
    return _PERIOD_DAYS.get(period.strip().lower(), 7)


def candle_interval_for_days(days: int) -> str:
    """Same rule as live fetch: short windows use 1h, longer use 4h."""
    return "1h" if days <= 7 else "4h"


def binance_spot_pair(symbol: str) -> str:
    return _BINANCE_SYMBOLS.get(symbol, f"{symbol}USDT")


def _true_ranges(candles: list[Candle]) -> list[float]:
    ranges: list[float] = []
    prev_close = candles[0].close
    for candle in candles:
        tr = max(
            candle.high - candle.low,
            abs(candle.high - prev_close),
            abs(candle.low - prev_close),
        )
        ranges.append(tr)
        prev_close = candle.close
    return ranges


def compute_atr(candles: list[Candle], period: int = ATR_PERIOD) -> float:
    if not candles:
        raise ValueError("ATR requires candles")
    ranges = _true_ranges(candles)
    window = ranges[-period:] if len(ranges) >= period else ranges
    return sum(window) / len(window)


def _swing_levels(candles: list[Candle]) -> tuple[float, float]:
    """Nearest swing support/resistance from local pivots (not period high/low)."""
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    last = candles[-1].close

    pivot_highs: list[float] = []
    pivot_lows: list[float] = []
    n = len(candles)
    left, right = SWING_LEFT, SWING_RIGHT
    for i in range(left, n - right):
        window_high = highs[i - left : i + right + 1]
        window_low = lows[i - left : i + right + 1]
        if highs[i] == max(window_high):
            pivot_highs.append(highs[i])
        if lows[i] == min(window_low):
            pivot_lows.append(lows[i])

    supports = [p for p in pivot_lows if p < last] or [min(lows)]
    resistances = [p for p in pivot_highs if p > last] or [max(highs)]
    support = max(supports)  # nearest below
    resistance = min(resistances)  # nearest above
    return support, resistance


def _volume_ratios(
    candles: list[Candle],
    support: float,
    resistance: float,
) -> tuple[float, float, float, float, float, bool]:
    volumes = [c.volume for c in candles]
    total = sum(volumes)
    avg = total / len(volumes) if volumes else 0.0
    last_vs_avg = (volumes[-1] / avg) if avg > 0 else 1.0

    band = max((resistance - support) * 0.05, support * 0.002)
    near_support = [
        c.volume for c in candles if abs(c.low - support) <= band or abs(c.close - support) <= band
    ]
    near_resist = [
        c.volume
        for c in candles
        if abs(c.high - resistance) <= band or abs(c.close - resistance) <= band
    ]
    support_ratio = (sum(near_support) / len(near_support) / avg) if near_support and avg else 1.0
    resist_ratio = (sum(near_resist) / len(near_resist) / avg) if near_resist and avg else 1.0
    # Volume confirms if recent activity >= avg and support zone saw participation.
    confirm = last_vs_avg >= 0.9 and support_ratio >= 0.85
    return total, avg, last_vs_avg, support_ratio, resist_ratio, confirm


def build_stats_from_candles(
    *,
    symbol: str,
    period: str,
    days: int,
    candles: list[Candle],
) -> PriceSeriesStats:
    if len(candles) < 2:
        raise ValueError("insufficient candles for TA feature pack")
    start = candles[0].close
    end = candles[-1].close
    low = min(c.low for c in candles)
    high = max(c.high for c in candles)
    atr = compute_atr(candles, period=ATR_PERIOD)
    support, resistance = _swing_levels(candles)
    (
        volume_total,
        volume_avg,
        volume_last_vs_avg,
        vol_sup,
        vol_res,
        volume_confirm,
    ) = _volume_ratios(candles, support, resistance)
    return PriceSeriesStats(
        symbol=symbol,
        period=period,
        days=days,
        candle_interval=candle_interval_for_days(days),
        atr_period=ATR_PERIOD,
        start_price=start,
        end_price=end,
        low=low,
        high=high,
        change_pct=(end - start) / start * 100.0 if start else 0.0,
        points=len(candles),
        atr=atr,
        support=support,
        resistance=resistance,
        volume_total=volume_total,
        volume_avg=volume_avg,
        volume_last_vs_avg=volume_last_vs_avg,
        volume_at_support_ratio=vol_sup,
        volume_at_resistance_ratio=vol_res,
        volume_confirm=volume_confirm,
    )


def _mock_candles(symbol: str, days: int) -> list[Candle]:
    """Synthetic OHLCV with a clear support/resistance structure for tests/mocks."""
    base = 3200.0 if symbol == "ETH" else 65000.0
    candles: list[Candle] = []
    # Build ~hours-equivalent bars: 24 per day for short windows, else 1d bars.
    bars = max(days * 24, 30) if days <= 7 else max(days, 30)
    for i in range(bars):
        # Mild uptrend with a swing low early and swing high mid-late.
        progress = i / max(bars - 1, 1)
        close = base * (0.97 + 0.04 * progress)
        if i == bars // 5:
            close = base * 0.955
        if i == (bars * 4) // 5:
            close = base * 1.025
        high = close * 1.004
        low = close * 0.996
        open_ = (candles[-1].close if candles else close)
        volume = 1000.0 + (400.0 if i == bars // 5 or i == (bars * 4) // 5 else 0.0)
        candles.append(
            Candle(open=open_, high=high, low=low, close=close, volume=volume)
        )
    return candles


def _parse_binance_klines(rows: list[list[object]]) -> list[Candle]:
    candles: list[Candle] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        candles.append(
            Candle(
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    return candles


def fetch_price_series_stats(
    cryptocurrency: str,
    period: str,
    *,
    session_logger: SessionLogger | None = None,
) -> PriceSeriesStats:
    symbol = normalize_symbol(cryptocurrency)
    days = period_to_days(period)

    if get_settings().use_mock_tools:
        candles = _mock_candles(symbol, days)
        stats = build_stats_from_candles(
            symbol=symbol,
            period=period,
            days=days,
            candles=candles,
        )
        if session_logger is not None:
            session_logger.log(
                kind="price_history",
                source="mock",
                request={"symbol": symbol, "days": days},
                response={
                    "points": stats.points,
                    "atr": stats.atr,
                    "support": stats.support,
                    "resistance": stats.resistance,
                    "volume_confirm": stats.volume_confirm,
                },
            )
        return stats

    pair = binance_spot_pair(symbol)
    # Prefer 1h for short windows, 4h for longer — keeps pivot quality reasonable.
    interval = candle_interval_for_days(days)
    limit = min(1000, max(days * (24 if interval == "1h" else 6), ATR_PERIOD + 10))
    try:
        response = httpx.get(
            _BINANCE_KLINES_URL,
            params={"symbol": pair, "interval": interval, "limit": limit},
            timeout=20.0,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("unexpected klines payload")
        candles = _parse_binance_klines(rows)
        # Trim to approximately the lookback window.
        keep = days * (24 if interval == "1h" else 6)
        if len(candles) > keep:
            candles = candles[-keep:]
        stats = build_stats_from_candles(
            symbol=symbol,
            period=period,
            days=days,
            candles=candles,
        )
        if session_logger is not None:
            session_logger.log(
                kind="price_history",
                source="binance_klines",
                request={
                    "symbol": symbol,
                    "pair": pair,
                    "days": days,
                    "interval": interval,
                },
                response={
                    "points": stats.points,
                    "atr": stats.atr,
                    "support": stats.support,
                    "resistance": stats.resistance,
                    "volume_confirm": stats.volume_confirm,
                    "change_pct": stats.change_pct,
                },
            )
        return stats
    except Exception as exc:
        if session_logger is not None:
            session_logger.log(
                kind="price_history",
                source="binance_klines",
                request={"symbol": symbol, "days": days},
                error=str(exc),
            )
        raise
