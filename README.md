# AI Crypto Intelligence Platform

Production-oriented crypto research system (goal B: research + decision support).

## Docs (start here)

1. [docs/START_HERE.md](docs/START_HERE.md)
2. [docs/PRODUCT.md](docs/PRODUCT.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
5. [docs/PROGRESS.md](docs/PROGRESS.md)

## Tooling

- Python via **uv** + `pyproject.toml` + `uv.lock` (no pip)
- Local deps: Docker Compose (`postgres`, `redis`)

## Quick start (Stage 0)

```bash
uv sync
cp .env.example .env
docker compose up -d
uv run python -c "import crypto_intel"