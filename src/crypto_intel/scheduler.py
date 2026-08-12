"""Lightweight daily watchlist scheduler skeleton."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from crypto_intel.domain.models import ResearchRequest
from crypto_intel.services.research import (
    ResearchConflictError,
    execute_research_run,
    start_research_run,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WatchlistItem:
    cryptocurrency: str
    period: str = "7d"
    question: str | None = None


DEFAULT_WATCHLIST: tuple[WatchlistItem, ...] = (
    WatchlistItem(cryptocurrency="BTC", period="7d"),
    WatchlistItem(cryptocurrency="ETH", period="7d"),
)


def run_watchlist(items: tuple[WatchlistItem, ...] = DEFAULT_WATCHLIST) -> list[str]:
    """Start research for each watchlist item (sync). Returns started run id strings."""
    started: list[str] = []
    for item in items:
        request = ResearchRequest(
            cryptocurrency=item.cryptocurrency,
            period=item.period,
            question=item.question,
        )
        try:
            run_id = start_research_run(request)
            execute_research_run(run_id)
            started.append(str(run_id))
            logger.info(
                "watchlist run completed cryptocurrency=%s run_id=%s",
                item.cryptocurrency,
                run_id,
            )
        except ResearchConflictError:
            logger.warning(
                "watchlist skipped lock conflict cryptocurrency=%s",
                item.cryptocurrency,
            )
        except Exception:
            logger.exception(
                "watchlist run failed cryptocurrency=%s",
                item.cryptocurrency,
            )
    return started


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ids = run_watchlist()
    print(f"started={len(ids)} runs: {ids}")
