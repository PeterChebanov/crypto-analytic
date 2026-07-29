"""Thin LLM client factory (xAI Grok via LangChain)."""
from __future__ import annotations
from langchain_xai import ChatXAI
from crypto_intel.settings import get_settings


def build_xai_chat_model() -> ChatXAI:
    xai = get_settings().xai
    return ChatXAI(
        model=xai.model,
        api_key=xai.api_key.get_secret_value(),
        base_url=xai.base_url,
        temperature=0
    )
    