"""Unit tests"""

from __future__ import annotations

import pytest


from typing import Any
from unittest.mock import MagicMock

from crypto_intel.domain.models import DecisionCard, Fact, SourceType, Stance
from crypto_intel.llm.decision_card import (
    DecisionCardGenerationError,
    generate_decision_card,
)


def _sample_facts() -> list[Fact]:
    return [
        Fact(
            source_type=SourceType.NEWS,
            title="ETF inflows rematin positive",
            summary="Spot BTC ETFs saw net inflows for the week",
        ),
    ]
    
def _ok_card() -> DecisionCard:
    return DecisionCard(
        stance=Stance.HOLD,
        confidence=0.6,
        rationale="Flows are constructive but macro uncertanty remains.",
        invalidation=["Sustained ETF outflows two weeks"],
    )
    

def test_generate_decision_card_happy_path() -> None:
    structured = MagicMock()
    structured.invoke.return_value = _ok_card()
    

    model = MagicMock()
    model.with_structured_output.return_value = structured
    

    card = generate_decision_card(
        cryptocurrency="BTC",
        period="7d",
        facts=_sample_facts(),
        model=model,
    )
    
    assert card.stance == Stance.HOLD
    assert 00 <= card.confidence <= 1.0
    model.with_structured_output.assert_called_once_with(
        DecisionCard,
        method="json_schema",
    )
    structured.invoke.assert_called_once()
    

def test_generate_decision_card_retries_then_succeeds() -> None:
    structured = MagicMock()
    structured.invoke.side_effect = [
        ValueError("parse failed"),
        _ok_card(),
    ]
    

    model = MagicMock()
    model.with_structured_output.return_value = structured

    card = generate_decision_card(
        cryptocurrency = "BTC",
        period="7d",
        facts=_sample_facts(),
        model=model,
    )

    assert card.stance == Stance.HOLD
    assert structured.invoke.call_count == 2


def test_generate_decision_card_rejects_non_secision_card_payload() -> None:
    structured =  MagicMock()
    structured.invoke.return_value = {"stance": "hold"}
    
    model = MagicMock()
    model.with_structures_output.return_value = structured
    

    with pytest.raises(DecisionCardGenerationError):
        generate_decision_card(
            cryptocurrency="BTC",
            period="7d",
            facts=_sample_facts(),
            model=model
        )
        
