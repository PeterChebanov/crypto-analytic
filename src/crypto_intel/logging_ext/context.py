"""Context-scoped session logger for external API calls."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from crypto_intel.logging_ext.session_log import SessionLogger

_current: ContextVar[SessionLogger | None] = ContextVar(
    "session_logger",
    default=None,
)


def get_session_logger() -> SessionLogger | None:
    return _current.get()


@contextmanager
def bind_session_logger(logger: SessionLogger) -> Iterator[SessionLogger]:
    token = _current.set(logger)
    try:
        yield logger
    finally:
        _current.reset(token)
