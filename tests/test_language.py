"""Language policy helpers."""

from __future__ import annotations

from crypto_intel.domain.language import language_instruction, language_note


def test_empty_focus_defaults_to_english() -> None:
    rule = language_instruction(None)
    assert "English" in rule
    assert language_note(None) == "english_default"
    assert language_note("   ") == "english_default"


def test_focus_language_follows_text() -> None:
    rule = language_instruction("купил ETH по 2800")
    assert "SAME language" in rule
    assert "купил ETH" in rule
    assert language_note("hola") == "match_focus"
