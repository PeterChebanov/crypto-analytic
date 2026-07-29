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

- **Stage:** 2 — LLM integration layer → **DONE**
- **Next stage:** 3 — LangChain building blocks (prompts, runnables, tools registry)
- **Provider:** xAI Grok — `XAI_API_KEY`, `XAI_BASE_URL`, model `grok-4.5`
- **MVP:** not complete (Stages 3–7 remain)
- **Post-MVP 1 / 2:** locked until MVP DoD
- **Policy:** production-first (no throwaway demos)

### Resume checklist (new chat)

1. Read `docs/START_HERE.md` — Production-first policy.
2. Re-read `.cursor/rules/engineering-bar.mdc`.
3. Confirm green: `uv run pytest tests/ -v` (13 passed as of Stage 2 close).
4. Start **Stage 3 / Teaching Step 1** (architecture of prompts + registry).

### What exists in the repo now

| Piece | Path | Notes |
|-------|------|--------|
| Domain | `src/crypto_intel/domain/` | contracts |
| Settings | `src/crypto_intel/settings.py` | slices: `postgres`, `redis`, `xai` |
| DB | `src/crypto_intel/db/` | session, ORM, repository |
| LLM client | `src/crypto_intel/llm/client.py` | `build_xai_chat_model()` |
| DecisionCard gen | `src/crypto_intel/llm/decision_card.py` | structured output + retry |
| Tools | `src/crypto_intel/tools/` | `market.get_market_snapshot` (mock), `executor.ToolExecutor` + `run_tool_loop` |
| Tests | `tests/` | domain, repository, decision_card, tool_executor — **13 passed** |

### Important lessons locked (do not re-teach from zero)

- **Production-first:** no throwaway demos; ship permanent modules; verify with tests; re-read rules before every step.
- **Engineering bar:** `.cursor/rules/engineering-bar.mdc` — layered settings slices + per-integration factories; code first; no crutches.
- **Config flow:** `.env` → `get_settings()` → slices → factories → business code uses clients only.
- Layers: domain → settings (root + slices) → integration factories → repository / graph nodes.
- `session_scope`: `yield` pauses for `with` body; success → `commit()` → `close()`.
- With `autoflush=False`, prefer mutate in-memory ORM objects over mid-session `get` without flush.
- Always `uv run …` (project `.venv`).
- LLM provider: xAI Grok (`XAI_*`, `llm_model` / `grok-4.5`); factory `build_xai_chat_model()`.

### Naming locked

- `cryptocurrency` / `period` / `Fact` (not asset / horizon / EvidenceItem)
- Root settings: `postgres_url` (not generic `database_url`)

---

## Entries

## 2026-07-29 — Stage 2 complete — LLM integration layer

- Status: done
- Implemented: settings slices; `build_xai_chat_model`; `generate_decision_card` + tests; `ToolExecutor` / `run_tool_loop` + mock `get_market_snapshot` + tests
- Fixed: market arg typo `cryptocurrncy` → `cryptocurrency`; tool-loop test list-mutation assert
- Verify: `uv run pytest tests/ -v` → 13 passed
- Next: Stage 3 — prompts, runnables, tools registry

## 2026-07-29 — Policy lock: production-first (no throwaway demos)

- Status: done (docs/rules)
- Changed: `START_HERE.md`, `IMPLEMENTATION_PLAN.md` (Stage 2–3+), `.cursor/rules/engineering-bar.mdc`, this file
- Rule: build only permanent product modules + tests; no sandbox CLIs / prove-library scripts; theory only for shipped code
- Keep existing implemented code as-is (including legacy `chat_demo` until student removes it)
- Next: Stage 2 product path — structured `DecisionCard` module, then tool executor, then tests

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
