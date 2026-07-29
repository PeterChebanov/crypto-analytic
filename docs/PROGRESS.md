# Progress log

Living checklist for teacher–student sessions. **Append-only preferred** (newest entries at the top). English only.

**New agent:** read `START_HERE.md` first, then this file. Do not write application code into the repo — chat only, one file at a time. Announce new deps with explicit `uv add` / `uv add --dev` before implementation. Prefer `uv run` (project `.venv`), not global pyenv binaries.

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

- **Stage:** 2 — LLM fundamentals in-repo
- **Teaching step:** Step 3 — file #1 `settings.py` in chat (xAI / `grok-4.5`); awaiting student apply + confirm
- **Provider:** xAI Grok — `XAI_API_KEY`, `XAI_BASE_URL`, model `grok-4.5`
- **MVP:** not complete (Stages 2–7 remain)
- **Post-MVP 1 / 2:** locked until MVP DoD

### Resume checklist (new chat)

1. Read `docs/START_HERE.md` (teacher rules, uv-only, one-file-at-a-time, deps rule).
2. Read this file + skim `PRODUCT.md` / `ARCHITECTURE.md` if needed.
3. Confirm Stage 1 green: `uv run pytest tests/ -v`
4. Stage 2 next after settings: `llm/client.py` (`ChatXAI`)
5. Provider locked: xAI Grok `grok-4.5` via `langchain-xai`

### What exists in the repo now

| Piece | Path | Notes |
|-------|------|--------|
| Domain (Pydantic) | `src/crypto_intel/domain/models.py` | `cryptocurrency`, `period`, `Fact`, `DecisionCard`, `ResearchReport`, `Critique` |
| Domain exports | `src/crypto_intel/domain/__init__.py` | |
| Settings | `src/crypto_intel/settings.py` | `get_settings()`, `.env`, `SecretStr` for API keys |
| DB session | `src/crypto_intel/db/session.py` | Engine + factory + `session_scope()`, **`autoflush=False`** |
| ORM | `src/crypto_intel/db/models.py` | `ResearchRunORM`, `FactORM`, `ReportORM`; table `facts` |
| Repository | `src/crypto_intel/db/repository.py` | `create_run`, `add_fact`, `save_report`, `get_run`, `set_run_status` |
| Alembic | `alembic/` + `alembic.ini` | Migration applied: `3ec3af084cdb` (research_runs, facts, reports) |
| Unit tests | `tests/test_domain_models.py` | 5 tests, green |
| Integration tests | `tests/test_repository.py` | roundtrip via real Postgres; green |
| Compose | `docker-compose.yml` | Postgres host port **5433→5432**, Redis; creds via `${POSTGRES_*}` |
| Tooling | `pyproject.toml`, `uv.lock` | **uv only**; pytest as **dev** dependency |

### Important lessons locked (do not re-teach from zero)

- **Engineering bar:** `.cursor/rules/engineering-bar.mdc` — layered settings slices + per-integration factories; code first; no crutches.
- **Config flow:** `.env` → `get_settings()` → slices (`xai`, `postgres`, `redis`, …) → factories (`db/session`, `llm/client`, `redis/client` later) → business code uses clients only.
- Layers: domain → settings (root + slices) → integration factories → repository / graph nodes.
- `session_scope`: `yield` pauses for `with` body; success → `commit()` (includes flush) → `close()`.
- `run_id = run.id` does **not** end the `with` block; leaving the indented `with` body does.
- With `autoflush=False`, do not `session.get` / SELECT for a row you just `add`ed in the **same** session without `flush` or without keeping the object reference. Prefer mutate the in-memory object (`run.status = ...`) over mid-session `get`.
- Always `uv run pytest` / `uv run python` so interpreter path contains `.venv` (not bare pyenv `pytest`).
- Pydantic field names must match exactly (`decision`, not `descision`; `model_dump`, not `model.dump`).
- LLM provider: xAI Grok (`XAI_API_KEY`, `XAI_BASE_URL`, model `grok-4.5`); thin client via `build_chat_model`; validation once in settings → typed config (no assert crutches in client).

### Naming locked

- `cryptocurrency` / `period` / `Fact` (not asset / horizon / EvidenceItem)

---

## Entries

## 2026-07-26 — Stage 2 / file #1 done — settings green; delivering client

- Status: in_progress
- Settings: xAI fields + `require_llm_config`; `get_settings` module-level (student fixed indent bug)
- Verify: `uv run pytest tests/ -v` green (student reported)
- Next: file #2 `src/crypto_intel/llm/client.py` (+ empty `llm/__init__.py`)

## 2026-07-26 — Stage 2 / file #1 — settings for xAI

- Status: in_progress
- Model: `grok-4.5`
- Delivered in chat: `src/crypto_intel/settings.py` (xai fields + `require_llm_config`)
- Student: copy by hand; keep `DATABASE_URL`/`REDIS_URL` required; LLM keys optional until require
- Verify with: `uv run pytest tests/ -v` still green; optional `uv run python -c "from crypto_intel.settings import get_settings; s=get_settings(); print(s.llm_model, bool(s.xai_api_key), s.xai_base_url)"`
- Next: after confirm → file #2 `llm/client.py`

## 2026-07-26 — Stage 2 — provider decision: xAI Grok

- Status: in_progress
- Understood architecture: yes
- Provider: **xAI Grok** (`XAI_API_KEY`, `XAI_BASE_URL`) — not OpenAI
- Deps: `uv add langchain langchain-xai` (not langchain-openai)
- Settings plan: `xai_api_key: SecretStr`, `xai_base_url: str`, optional `llm_model`; remove/ignore mistyped `open_api_key` for LLM path
- Client: `ChatXAI` from `langchain_xai` with explicit `api_key` + `base_url` from settings
- Verify with: `uv run python -c "from langchain_xai import ChatXAI; print('ok')"`
- Next: student runs `uv add`; then file #1 settings

## 2026-07-26 — Stage 2 / Teaching Step 1+2 → impl — architecture confirmed; deps next

- Status: in_progress
- Understood architecture: yes (student confirmed)
- Understood theory: teaching alongside implementation (student request)
- Implemented: nothing yet — first block is `uv add` (langchain-openai + langchain-core as needed)
- Tests / security / AI QA: Stage 1 still green
- Verify with: after install, `uv run python -c "from langchain_openai import ChatOpenAI; print('ok')"`
- Open questions: provider = OpenAI for MVP; fix settings field name `open_api_key` → `openai_api_key`
- Next: student runs `uv add`; then file #1 (settings alignment / llm client — order TBD in chat)

## 2026-07-26 — Stage 2 / Teaching Step 1 — LLM fundamentals architecture

- Status: done (superseded by entry above for current work)
- Understood architecture: yes
- Next: was Step 2; student asked to implement with theory in parallel

## 2026-07-26 — Stage 1 complete — domain + Postgres + tests

- Status: done
- Understood architecture: yes
- Understood theory: yes (session/commit/flush; uv vs pyenv; pytest log reading)
- Implemented: full Stage 1 stack listed above
- Tests / security / AI QA:
  - `uv run pytest tests/ -v` → all green
  - Learned: mid-session `set_run_status`+`get` failed under `autoflush=False`; fixed by setting `run.status` on the existing object
  - Secrets: `.env` gitignored; compose uses env substitution
- Verify with:
  - `docker compose ps`
  - `uv run alembic current` → `3ec3af084cdb`
  - `uv run pytest tests/ -v`
  - `uv run which pytest` → must be `.../CryptoAnalitics/.venv/bin/pytest`
- Open questions: none blocking Stage 2
- Next: Stage 2 / Teaching Step 1 — LLM fundamentals architecture

## 2026-07-26 — Stage 1 / Step 3 — checkpoint before ORM (superseded)

- Status: superseded by Stage 1 complete entry above
- Had: domain, settings, session pipe; ORM/Alembic/repository/tests were still pending at that time

## 2026-07-24..25 — Stage 0 — Repository foundation

- Status: done
- Implemented: git, uv package, Compose, env template, docs contract
- Next: was Stage 1 (now done)
