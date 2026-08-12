"""Analytics Decision Card ↔ forecast enter coherence."""

from __future__ import annotations

from crypto_intel.domain.models import Stance
from crypto_intel.forecast.coherence import (
    decision_allows_add_on,
    decision_allows_new_entry,
    decision_blocks_risk_on,
)


def test_new_entry_only_on_accumulate() -> None:
    assert decision_allows_new_entry(Stance.ACCUMULATE)
    assert not decision_allows_new_entry(Stance.HOLD)
    assert not decision_allows_new_entry(Stance.REDUCE)
    assert not decision_allows_new_entry(Stance.AVOID)


def test_add_on_only_on_accumulate() -> None:
    assert decision_allows_add_on(Stance.ACCUMULATE)
    assert not decision_allows_add_on(Stance.HOLD)
    assert not decision_allows_add_on(Stance.REDUCE)
    assert not decision_allows_add_on(Stance.AVOID)


def test_risk_on_blocked_for_avoid_and_reduce() -> None:
    assert decision_blocks_risk_on(Stance.AVOID)
    assert decision_blocks_risk_on(Stance.REDUCE)
    assert not decision_blocks_risk_on(Stance.HOLD)
    assert not decision_blocks_risk_on(Stance.ACCUMULATE)
