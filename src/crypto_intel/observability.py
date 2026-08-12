"""LangSmith / tracing bootstrap from settings."""

from __future__ import annotations

import logging
import os

from crypto_intel.settings import Settings

logger = logging.getLogger(__name__)


def configure_observability(settings: Settings) -> None:
    """Enable LangSmith tracing via env vars when configured."""
    if not settings.langsmith_tracing:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
        return

    if settings.langsmith_api_key is None:
        logger.warning("langsmith_tracing=true but LANGSMITH_API_KEY is missing")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key.get_secret_value()
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    logger.info("LangSmith tracing enabled project=%s", settings.langsmith_project)
