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

- **Goal:** Full MVP + forecast/language/price-consensus extensions (in progress for real-world testing)
- **How to run:** see root `README.md` / `Start.command`
- **Provider:** xAI Grok
- **Collectors:** `USE_MOCK_TOOLS=true` by default; set `false` for live venues
- **Next:** optional live Forecast retest after Decision Card ↔ enter coherence; CryptoCompare news 401 separately

### Locked: Analytics ↔ Forecast coherence (2026-08-12)

- New entry only if Decision Card stance is **`accumulate`** AND TA R:R ≥ 1:3 AND structure OK.
- `avoid` / `reduce` / `hold` → never open new risk (`hold` = no new risk).
- In-position add-on only on `accumulate`; `avoid`/`reduce` → exit/reduce paths.
- Bundle fields: `final_verdict` (`enter_long` | `do_not_enter`), `trade.blocked_by_decision`.
- Module: `forecast/coherence.py`; enforced in `forecast/engine.py` (rules + LLM finalize).

### Locked: TA number contract (2026-08-12)

- Root guide: `FORECAST_READING.md` (how to run, JSON glossary, LLM open issues).
- Forecast JSON includes `ta_contract` and `trade.take_profit_source`.
- Chart-scale gate: stop ≥ 10% of period H/L (`scale_ok` / `blocked_by_scale`); R:R after rounded levels.
- `estimated_playout` = setup duration estimate; analysis lookback ≠ hold time.
- Read order: Decision Card → coherence → R:R + scale → `final_verdict`.

### MVP DoD checklist

- [x] E2E path: API → graph → brief + decision card + facts in Postgres (`run_id` on finalize)
- [x] LangGraph conditional edges + checkpoint resume (InMemorySaver test)
- [x] LangSmith hook (enable via `LANGSMITH_TRACING` + key)
- [x] Redis cache (market) + daily research lock
- [x] News + Market tools (live behind flag; mock default)
- [x] Critic rejects news without `source_url` (evals)
- [x] Docker Compose + English README + curl demo path
- [x] Docs/PROGRESS updated
- [x] Mode `analytics` | `forecast`; focus language; multi-source price gate; session logs UI

### Resume checklist (new chat)

1. `uv run pytest tests/ -v`
2. `docker compose up -d && uv run alembic upgrade head`
3. `./scripts/start.sh` or `Start.command`, then open UI
4. Try Forecast mode + Russian focus; check Logs tab

### Important lessons locked (do not re-teach from zero)

- **Production-first:** no throwaway demos; ship permanent modules; verify with tests; re-read rules before every step.
- **Engineering bar:** `.cursor/rules/engineering-bar.mdc` — layered settings slices + per-integration factories; code first; no crutches.
- **Config flow:** `.env` → `get_settings()` → slices → factories → business code uses clients only.
- Layers: domain → settings (root + slices) → integration factories → repository / graph nodes.
- `session_scope`: `yield` pauses for `with` body; success → `commit()` → `close()`.
- With `autoflush=False`, prefer mutate in-memory ORM objects over mid-session `get` without flush.
- Always `uv run …` (project `.venv`).
- LLM provider: xAI Grok (`XAI_*`, `llm_model` / `grok-4.5`); factory `build_xai_chat_model()`.
- **Registry** is the single allowlist + `tools_description` source for planner; Stage 5 swaps tool bodies behind the same names.
- **AnalysisDraft** + `DecisionCard` stay separate; `ResearchReport` assembles them later in the graph.
- Field naming must match domain contracts (`gaps`, not typos like `agps`).
- **Price consensus:** ≤0.25% OK, 0.25–1% WARN (UI), >1% HARD skip; 1/3 → await confirm.

### Naming locked

- `cryptocurrency` / `period` / `Fact` (not asset / horizon / EvidenceItem)
- Root settings: `postgres_url` (not generic `database_url`)

---

## Entries

## 2026-08-12 — Forecast TA fundamentals + R:R 1:3 gate

- Status: done
- History: Binance OHLCV → ATR, swing S/R, volume confirm
- Derivatives: Binance futures OI Δ + funding (soft-fail if unavailable)
- Hard gate: `enter` only if reward/risk ≥ 3.0; post-LLM enforce
- `setup_score` confluence (not ML probability); LLM formats only
- Verify: `uv run pytest tests/ -v` → 51 passed

## 2026-08-12 — Forecast mode, language, price consensus, session logs

- Status: done (code)
- Mode dropdown: analytics | forecast (experimental)
- Language: empty focus → English; otherwise match focus language in prompts/DecisionCard/forecast
- Prices: Binance + Kraken + CoinGecko parallel → median; ≤0.25% OK, 0.25–1% WARN (UI), >1% HARD skip; 1/3 → awaiting Yes/No
- Session JSONL under `logs/sessions/` + UI Logs tab
- Verify with: `uv run pytest tests/ -v`

## 2026-08-12 — Minimal UI + one-click local start

- Status: done
- UI: `/` form — cryptocurrency, timeframe, optional focus (`question`); polls report
- Launcher: `scripts/local_launcher.py` on `:7911`; UI button **Start local stack**
- One-click: `Start.command` / `scripts/start.sh` (Docker Desktop must already be running)
- Note: browser cannot cold-start Docker; launcher is the bridge
- Verify: `uv run pytest tests/ -v`; double-click Start.command

## 2026-08-12 — Full MVP ship for real-world testing

- Status: done (MVP code path)
- Ownership: agent implemented application code (student requested)
- Implemented:
  - Stage 4: checkpointer resume, JSON-serializable graph state, logging in nodes, fixed `revision_loops` typo
  - Stage 5: Redis client/locks, `USE_MOCK_TOOLS`, CoinGecko market + cache, CryptoCompare news
  - Stage 6: critique evals, LangSmith bootstrap (`observability.py`)
  - Stage 7: FastAPI `/research`, scheduler skeleton, README curl path
- Tests: `uv run pytest tests/ -v` → **35 passed**
- Verify with: README bootstrap + `uvicorn crypto_intel.api.app:app --reload --port 8000`
- Next: student real-world test; then minimal UI

## 2026-08-12 — Decision: full MVP then minimal UI

- Status: done (superseded by ship entry above)
- Decision: full MVP DoD; UI after API exists

## 2026-08-06 — Stage 4 / checkpointer + resume

- Status: in_progress (re-opened 2026-08-12 — code not landed yet)
- Next: student applies builder + test_graph changes

## 2026-08-06 — Stage 4 / conditional edges + max revision loops

- Status: done
- Implemented: `routing.py`, critique bumps `revision_loops`, conditional edges, `test_routing.py`
- Next: checkpointer

## 2026-08-06 — Stage 4 / file #3 done → test linear graph

- Status: done
- Implemented: `tests/test_graph.py` green (student confirmed)
- Next: conditional edges

## 2026-08-06 — Stage 4 / file #3 — linear graph builder

- Status: done
- Fixed: `model: ... | None = None` (was `:` typo); full builder body restored
- Verify: `build_research_graph()` compiles
- Next: test with fake model

## 2026-08-06 — Stage 4 / file #2 review — node.py blockers

- Status: done (student confirmed checks passed)
- Fixed: turtle/RunnableConfig removed; source_type; fetch_news; market facts list; market invoke args; change_24h_pct
- Note: finalize still typed with `BaseModel` — fix alongside file #3
- Next: was file #3

- Status: in_progress
- File #1: `graph/state.py` fixed (`cryptocurrency` confirmed via import smoke)
- Delivering in chat: `src/crypto_intel/graph/nodes.py` — thin wrappers over chains/tools/llm/db
- Verify with: `uv run python -c "from crypto_intel.graph.nodes import build_research_nodes; print(sorted(build_research_nodes()))"`
- Next: after confirm → file #3 linear `graph/builder.py` (or `graph.py`)

## 2026-08-04 — Stage 4 / file #1 review — state.py needs fix before nodes

- Status: done
- Issue fixed: `cryptocurrency` field present; termios import removed; `__init__.py` added
- Next: file #2 `nodes.py`

## 2026-08-04 — Stage 4 / Teaching Step 3 — deps + file #1 GraphState

- Status: in_progress (file #1 present but needs correction)
- Understood architecture: yes
- Understood theory: yes (Step 2 confirmed)
- Implemented: `langgraph` dep; `graph/__init__.py`; `graph/state.py` (needs typo/import fix)
- Verify with: `uv run python -c "from crypto_intel.graph.state import GraphState; print(sorted(GraphState.__annotations__))"` — must show `cryptocurrency`, not `crtptocurrency`
- Next: fix state → file #2 nodes

## 2026-08-04 — Stage 4 / Teaching Step 1 done → Step 2 theory

- Status: done
- Understood architecture: yes
- Understood theory: yes
- Implemented: nothing (theory only)
- Next: Step 3 — `uv add langgraph` + `graph/state.py`

## 2026-07-31 — Stage 4 / Teaching Step 1 — LangGraph architecture

- Status: done (closed 2026-08-04)
- Understood architecture: yes
- Understood theory: deferred to Step 2
- Implemented: nothing (architecture + product-flow review only)
- Next: was Step 2

## 2026-07-30 — Stage 3 complete — LangChain building blocks

- Status: done
- Understood architecture: yes
- Understood theory: yes (prompt templates, LCEL, tools registry)
- Implemented: `prompts/planner.py`, `prompts/analysis.py`; `tools/news.py`, `tools/registry.py`; `chains/planner.py`, `chains/analysis.py`; domain `AnalysisDraft`
- Tests / security / AI QA: `test_registry`, `test_prompts`, `test_chains`; allowlist-only collectors; no live LLM in unit tests
- Fixed: `AnalysisDraft.agps` → `gaps`; `normalize_question` blank → `"(no specific focus)"`
- Verify with: `uv run pytest tests/ -v` → **25 passed**
- Next: Stage 4 / Teaching Step 1 — LangGraph orchestrator architecture
- Note: student asked agent to own `PROGRESS.md` updates going forward

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
