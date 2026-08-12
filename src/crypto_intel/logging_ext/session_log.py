"""Session-scoped external API logging (persisted on disk)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SESSIONS_ROOT = _PROJECT_ROOT / "logs" / "sessions"
_lock = Lock()


def session_dir_for(run_id: UUID, *, created_at: datetime | None = None) -> Path:
    stamp = (created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d_%H%M%S")
    path = _SESSIONS_ROOT / f"session_{stamp}_{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class SessionLogger:
    """Append-only JSONL logger for one research run."""

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        existing = find_session_dir(run_id)
        self.dir = existing if existing is not None else session_dir_for(run_id)
        self.path = self.dir / "external_api.jsonl"

    def log(
        self,
        *,
        kind: str,
        source: str,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | str | None = None,
        error: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": str(self.run_id),
            "kind": kind,
            "source": source,
            "request": request or {},
            "response": response,
            "error": error,
            "meta": meta or {},
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def read_lines(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows


def find_session_dir(run_id: UUID) -> Path | None:
    if not _SESSIONS_ROOT.exists():
        return None
    needle = str(run_id)
    matches = sorted(_SESSIONS_ROOT.glob(f"session_*_{needle}"), reverse=True)
    return matches[0] if matches else None


def read_session_logs(run_id: UUID) -> list[dict[str, Any]]:
    directory = find_session_dir(run_id)
    if directory is None:
        return []
    path = directory / "external_api.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
