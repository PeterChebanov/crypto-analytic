"""Output language policy: follow Focus text; default English."""

from __future__ import annotations


def language_instruction(question: str | None) -> str:
    """Build a prompt rule for LLM user-facing text language."""
    if question is None or not question.strip():
        return (
            "Language: write ALL user-facing text in English "
            "(focus was empty)."
        )
    return (
        "Language: write ALL user-facing text in the SAME language as this focus text. "
        "If the focus is Russian, answer in Russian; if Spanish, in Spanish; etc. "
        f"Focus text:\n{question.strip()}"
    )


def language_note(question: str | None) -> str:
    if question is None or not question.strip():
        return "english_default"
    return "match_focus"
