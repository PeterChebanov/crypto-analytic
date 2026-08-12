# AI Crypto Intelligence Platform

Production-oriented crypto research system (**goal B**: research + decision support — not price prediction, not financial advice).

## Docs

1. [docs/START_HERE.md](docs/START_HERE.md)
2. [docs/PRODUCT.md](docs/PRODUCT.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
5. [docs/PROGRESS.md](docs/PROGRESS.md)

## Stack

- Python 3.12+ via **uv** (`pyproject.toml` + `uv.lock`)
- LangGraph orchestrator + LangChain + xAI Grok
- PostgreSQL (runs / facts / reports) + Redis (cache / locks)
- FastAPI delivery surface
- Optional LangSmith tracing

## Bootstrap

```bash
uv sync
cp .env.example .env
# Edit .env: set XAI_API_KEY, confirm POSTGRES_URL port (Compose maps 5433→5432)
docker compose up -d
uv run alembic upgrade head
uv run pytest tests/ -v
```

## One-click local start (recommended)

1. Start **Docker Desktop** and wait until it is idle/ready.
2. Double-click **`Start.command`** (macOS) or run:

```bash
./scripts/start.sh
```

This will:
- start Postgres + Redis via Compose
- start a local launcher on `:7911` (UI button talks to it)
- run migrations, start the API on `:8000`, open the UI

UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

In the UI:
- **Start local stack** — calls the launcher (needs Docker Desktop + launcher process)
- **Cryptocurrency / timeframe / optional focus** — focus only steers prompts; Decision Card still comes from the same research pipeline
- **Run research** — polls until completed and shows brief, stance, facts

> Browsers cannot start Docker by themselves. First click is `Start.command`; after that the in-UI button can restart/bring the stack up via the local launcher.

## Run the API manually

```bash
# Mocks for collectors (default). Set USE_MOCK_TOOLS=false for live CoinGecko + CryptoCompare.
uv run uvicorn crypto_intel.api.app:app --reload --host 127.0.0.1 --port 8000
```

### Example curl flow

```bash
# 1) Start research (returns immediately with run_id)
curl -s -X POST http://127.0.0.1:8000/research \
  -H 'Content-Type: application/json' \
  -d '{"cryptocurrency":"ETH","period":"7d","question":"any major unlock risk?"}'

# 2) Poll status
curl -s http://127.0.0.1:8000/research/<run_id>

# 3) Fetch report + facts when status=completed
curl -s http://127.0.0.1:8000/research/<run_id>/report
```

Conflict if the same coin is already locked for today → HTTP **409**.

## Watchlist scheduler (skeleton)

```bash
uv run python -m crypto_intel.scheduler
```

Runs the default BTC/ETH watchlist synchronously (respects Redis locks).

## Real-world testing tips

| Knob | Meaning |
|------|---------|
| `USE_MOCK_TOOLS=true` | Deterministic mock news/market (no external HTTP) |
| `USE_MOCK_TOOLS=false` | Live market (CoinGecko) + news (CryptoCompare); Redis used for market cache |
| `LANGSMITH_TRACING=true` | Send traces when `LANGSMITH_API_KEY` is set |
| `XAI_API_KEY` | Required for planner / analysis / decision card |

## Architecture (runtime)

```
POST /research → lock + create run → background LangGraph
  planner → news → market → analyze → critique ⇄ analyze → finalize → Postgres
GET /research/{id}/report → brief + Decision Card + facts
```

## Disclaimer

Output is research support only. It does **not** guarantee profit and is **not** formal financial advice.
