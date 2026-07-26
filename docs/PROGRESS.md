# Progress log

Living checklist for teacher–student sessions. **Append-only preferred** (newest entries at the top). English only.

**New agent:** read `START_HERE.md` first, then this file. Do not write application code into the repo — chat only, one file at a time.

Template for each entry:

```text
## YYYY-MM-DD — Stage N / Teaching Step K — <title>
- Status: in_progress | done | blocked
- Understood architecture: yes/no
- Understood theory: yes/no
- Implemented: ...
- Tests / security / AI QA: ...
- Verify with: <commands>
- Open questions: ...
- Next: Stage … Step …
```

---

## Current position

- **Stage:** 1 — Domain contracts + PostgreSQL
- **Teaching step:** 3 — Sequential implementation (**in progress**)
- **MVP:** not complete
- **Post-MVP 1 / 2:** locked until MVP DoD

### Resume here (next action)

1. Create empty `src/crypto_intel/db/__init__.py` if missing.
2. Implement **`src/crypto_intel/db/models.py`** (ORM tables) — snippet was given in chat; student had not finished it yet when this log was written.
3. Then: Alembic migration → repository → tests (Stage 1 Teaching Step 4).

### Already in the repo (do not redo)

| Piece | Path | Role |
|-------|------|------|
| Domain models | `src/crypto_intel/domain/models.py` | Pydantic: `ResearchRequest`, `Fact`, `DecisionCard`, `ResearchReport`, `Critique`, enums |
| Domain exports | `src/crypto_intel/domain/__init__.py` | Public imports from `crypto_intel.domain` |
| Settings | `src/crypto_intel/settings.py` | `get_settings()` from `.env` (`DATABASE_URL`, `REDIS_URL`, …) |
| DB pipe | `src/crypto_intel/db/session.py` | Engine + `sessionmaker` + `session_scope()` (`autoflush=False`) |
| Stage 0 foundation | `pyproject.toml`, `uv.lock`, `docker-compose.yml`, `.env.example`, `README.md`, `docs/` | uv-only; Postgres host port **5433→5432**; secrets via `${POSTGRES_*}` |

### Naming locked in code + docs

- `cryptocurrency` (not `asset`)
- `period` (not `horizon`)
- `Fact` (not `EvidenceItem`)
- DB table name planned: `facts` (not `evidence_items`)

### Tooling locked

- **uv** + `pyproject.toml` + `uv.lock` only (no pip)
- Agent never writes app code to the repo; one file at a time in chat

---

## Entries

## 2026-07-26 — Stage 1 / Step 3 — progress checkpoint before ORM

- Status: in_progress
- Understood architecture: yes (layers: domain → settings → session → ORM next)
- Understood theory: yes (session vs engine cache; yield/context manager; flush policy deferred to repository/use-cases)
- Implemented:
  - Stage 0 complete (committed foundation earlier)
  - Stage 1 domain + settings + DB session pipe
- Tests / security / AI QA:
  - `import crypto_intel` / domain import OK
  - `get_settings()` OK
  - `session_scope` + `SELECT 1` OK
  - `.env` gitignored; compose uses env substitution for Postgres creds
- Verify with:
  - `uv run python -c "from crypto_intel.domain import ResearchRequest; print(ResearchRequest(cryptocurrency='ETH', period='7d'))"`
  - `uv run python -c "from crypto_intel.settings import get_settings; s=get_settings(); print(s.database_url.split('@')[-1])"`
  - `uv run python -c "from sqlalchemy import text; from crypto_intel.db.session import session_scope; 
with session_scope() as s: print(s.execute(text('SELECT 1')).scalar())"`
- Open questions: none blocking
- Next: `src/crypto_intel/db/models.py` (ORM), then Alembic

## 2026-07-24..25 — Stage 0 — Repository foundation

- Status: done
- Implemented: git, uv package `crypto_intel`, Compose Postgres/Redis, env template, docs contract
- Next: was Stage 1 domain
