"""Local-only control plane: start Docker services + API from the UI button."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PID_FILE = PROJECT_ROOT / ".api.pid"
API_URL = "http://127.0.0.1:8000/health"
LAUNCHER_HOST = "127.0.0.1"
LAUNCHER_PORT = 7911

app = FastAPI(title="CryptoIntel Local Launcher", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def _docker_available() -> bool:
    try:
        result = _run(["docker", "info"], check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _api_healthy() -> bool:
    try:
        response = httpx.get(API_URL, timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def _read_api_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _stop_api() -> None:
    pid = _read_api_pid()
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)


def _start_api() -> None:
    if _api_healthy():
        return
    _stop_api()
    log_path = PROJECT_ROOT / ".api.log"
    log_file = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "crypto_intel.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=PROJECT_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    PID_FILE.write_text(str(process.pid), encoding="utf-8")


def _wait_api(timeout_seconds: float = 60.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _api_healthy():
            return True
        time.sleep(0.5)
    return False


@app.get("/status")
def status() -> dict[str, object]:
    return {
        "docker": _docker_available(),
        "api": _api_healthy(),
        "launcher": True,
        "api_url": "http://127.0.0.1:8000",
        "ui_url": "http://127.0.0.1:8000/",
    }


@app.post("/start")
def start_stack() -> dict[str, object]:
    if not _docker_available():
        raise HTTPException(
            status_code=503,
            detail="Docker Desktop is not running or docker CLI is unavailable",
        )

    up = _run(["docker", "compose", "up", "-d", "postgres", "redis"], check=False)
    if up.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"docker compose failed: {up.stderr or up.stdout}",
        )

    # Wait for postgres readiness via compose health roughly.
    time.sleep(2.0)
    migrate = _run(["uv", "run", "alembic", "upgrade", "head"], check=False)
    if migrate.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"alembic failed: {migrate.stderr or migrate.stdout}",
        )

    try:
        _start_api()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to start API: {exc}") from exc

    if not _wait_api():
        raise HTTPException(status_code=504, detail="API did not become healthy in time")

    return {
        "ok": True,
        "docker": True,
        "api": True,
        "ui_url": "http://127.0.0.1:8000/",
        "message": "Stack is up",
    }


@app.post("/stop-api")
def stop_api() -> dict[str, str]:
    _stop_api()
    return {"status": "stopped"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=LAUNCHER_HOST, port=LAUNCHER_PORT, log_level="info")


if __name__ == "__main__":
    main()
