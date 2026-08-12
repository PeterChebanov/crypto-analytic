"""Coherence between Decision Card analytics and forecast trade gate."""

from __future__ import annotations

from crypto_intel.domain.models import Stance

# Locked product rule: capital preservation first.
# New entries require an accumulate stance from analytics.
# Avoid/reduce always block opening/adding risk.


def decision_allows_new_entry(stance: Stance) -> bool:
    """Whether analytics permits opening a new long."""
    return stance == Stance.ACCUMULATE


def decision_allows_add_on(stance: Stance) -> bool:
    """Whether analytics permits adding to an existing position."""
    return stance == Stance.ACCUMULATE


def decision_blocks_risk_on(stance: Stance) -> bool:
    return stance in (Stance.AVOID, Stance.REDUCE)
