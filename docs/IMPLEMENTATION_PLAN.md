# Implementation Plan (stage-by-stage)

**Read first:** `START_HERE.md` (career goal, language policy, no repo code from agent, 4-step teaching protocol, senior+ code bar).  
**Product:** goal B — `PRODUCT.md`  
**Architecture / priorities:** `ARCHITECTURE.md`  
**Progress log:** `PROGRESS.md` (update after every teaching step and implementation chunk)

**Timeline guide:** ~2.5–3 weeks × 5–6 h/day for MVP (Stages 0–7). Post-MVP Stage 1 (P1) and Stage 2 (P2) follow after MVP is green. If behind schedule, cut P1/P2 — never break P0.

**Mental model:** orchestrator advances the cycle; LLM proposes actions only where the graph allows; Python runs tools; state persists between steps.

**How each stage is taught (mandatory order):**

| Teaching step | Agent does | Student does |
|---------------|------------|--------------|
| **1. Architecture** | Explains what this stage builds, how it works alone, how it plugs into the full system | Asks until clear; logs notes in `PROGRESS.md` |
| **2. Technologies & theory** | Lists stack + theory prerequisites; web-research if APIs/docs may have changed | Studies / asks; no coding until clear |
| **3. Sequential implementation** | Ordered checklist including git, folders, env, commands, tiny commits | Implements by hand; may request chat snippets |
| **4. Testing / AI Security / AI QA** | Defines test levels, security checks, eval ideas | Writes tests; asks until clear |

Do not start Teaching Step 3 of a stage until Steps 1–2 are understood. Do not start the next stage until Step 4 of the current stage is done (or explicitly deferred with a note in `PROGRESS.md`).

---

## Stage map

| Stage | Name | Scope |
|-------|------|--------|
| 0 | Repository foundation | Git, project layout, Docker, tooling |
| 1 | Domain contracts + Postgres | Models, migrations, indexes |
| 2 | LLM fundamentals in-repo | Call, stream, structured output, manual tool loop |
| 3 | LangChain building blocks | Prompts, runnables, tools registry |
| 4 | LangGraph orchestrator MVP core | State, nodes, edges, checkpoints, DB persist |
| 5 | Real collectors + Redis | Market, News, cache, locks |
| 6 | Quality loop | Critic, LangSmith, evals |
| 7 | Delivery surface (MVP complete) | FastAPI, scheduler skeleton, README demo |
| **Post-MVP 1** | Hardening + memory + HITL + GitHub | P1 |
| **Post-MVP 2** | Events + analytics + optional forecast | P2 |

---

# Stage 0 — Repository foundation

### Teaching Step 1 — Architecture

**What we build:** an empty but professional skeleton: versioned repo, installable Python package, local Postgres/Redis via Compose, secrets pattern, English README pointing at docs.

**Alone:** you can clone, create venv, `docker compose up`, import `crypto_intel` — no LLM yet.

**In the system:** every later stage lands inside this layout. Bad foundation = painful refactors. Interview angle: reproducible local env, 12-factor-ish config, clear package boundaries.

### Teaching Step 2 — Technologies & theory

Know before coding:

- Git basics: `init`, `.gitignore`, commits, branches (local is enough at first)
- Python packaging: `src/` layout, `pyproject.toml`, editable install via **uv**
- **uv only** for Python envs/deps — **no pip / requirements.txt / Poetry / pipenv**
- `uv.lock` is committed (reproducible installs)
- Docker Compose concepts (services, volumes, ports)
- Why secrets never enter git (`.env` vs `.env.example`)
- Project English-only rule for code/docs

Stack: Python 3.12+, Git, Docker Compose, **uv** + `pyproject.toml` + `uv.lock`, Ruff/pytest via `uv add --dev` OK.

### Teaching Step 3 — Sequential implementation

Do in order:

1. `cd` to project root; `git init` if not already a repo.
2. Create `.gitignore` (Python, `.venv`, `.env`, `__pycache__`, IDE, `.pytest_cache`, coverage, `uv` caches if any).
3. Ensure root `README.md` (English) links to `docs/START_HERE.md` (`docs/` already present).
4. Ensure **uv** is installed (`uv --version`). Initialize as a **package** project in this non-empty repo (`uv init --package` with project/package name aligned to `crypto_intel`, or hand-write equivalent `pyproject.toml` + `[build-system]` + `src/crypto_intel/` if `uv init` refuses a non-empty dir). Goal: `uv sync` installs the local package editable.
5. Pin Python: `uv python pin 3.12` (or 3.12+ as agreed). Commit `.python-version` if created.
6. `uv sync` — creates `.venv` + `uv.lock`. **Commit `uv.lock`.** Never use `pip` / `requirements.txt`.
7. Create `.env.example` with placeholder keys (`DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY` or provider of choice, `LANGSMITH_*`) — no real secrets.
8. Create local `.env` from example (gitignored).
9. Add `docker-compose.yml`: `postgres` (with volume), `redis`; documented ports.
10. Verify import: `uv run python -c "import crypto_intel"`.
11. Optional: `uv add --dev pytest ruff`.
12. `docker compose up -d`; verify Postgres/Redis reachable.
13. First commit: `chore: initialize repository foundation`.
14. Update `PROGRESS.md`.

**Done when:** Compose is up; package imports; first commit exists; README points to docs.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** smoke test that package imports; optional Compose health check script.
- **Security:** confirm `.env` not tracked (`git status`); no API keys in example files; Compose not exposing DB to public internet unbound in production notes.
- **QA:** document “fresh machine” bootstrap steps in README; student runs them once from scratch mentally or on a clean shell.

---

# Stage 1 — Domain contracts + PostgreSQL

### Teaching Step 1 — Architecture

**What we build:** language of the product in code — pydantic domain models + relational schema for runs/evidence/reports. No LLM.

**Alone:** you can insert a fake run and evidence row and read them back.

**In the system:** LangGraph state and API payloads map to these contracts; Critic/evals validate against them; interview topic: schema-first design, indexes for query patterns.

### Teaching Step 2 — Technologies & theory

- Pydantic v2 models, enums, validation
- Domain vs API schema separation (even if thin at first)
- SQLAlchemy 2.x + Alembic migrations
- Postgres types, PK/FK, **why indexes** (B-tree, composite `(asset, created_at)`, uniqueness for dedupe)
- Transactions and idempotent inserts (conceptual)

### Teaching Step 3 — Sequential implementation

1. Add deps: `pydantic`, `sqlalchemy`, `alembic`, `psycopg` (or async driver — pick one and stay consistent; sync is fine for MVP).
2. Create `src/crypto_intel/domain/` models: `ResearchRequest`, `EvidenceItem`, `DecisionCard`, `ResearchReport`, `RunStatus`, `Critique` stub.
3. Create `src/crypto_intel/db/` engine/session factory reading `DATABASE_URL`.
4. Define ORM tables: `research_runs`, `evidence_items`, `reports` (+ optional `source_snapshots`).
5. `alembic init`; configure to use app metadata; write first migration with indexes:
   - `research_runs(asset, created_at)`
   - `evidence_items(run_id)` FK
   - unique or fingerprint constraint for dedupe if designed
6. Apply migration against Compose Postgres.
7. Small repository/DAO functions: `create_run`, `add_evidence`, `save_report`, `get_run`.
8. Unit tests for pydantic round-trip; integration test for insert/select (pytest + test DB or Compose).
9. Commit: `feat: add domain models and postgres schema`.
10. Update `PROGRESS.md`.

**Done when:** migration applies; tests pass; can CRUD a run with evidence.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Unit:** model validation (invalid stance rejected; URL fields required where needed).
- **Integration:** migration + repository against real Postgres.
- **Security:** SQL injection avoided via ORM/bound params; no raw string-concat SQL; DB creds only in env.
- **AI QA preview:** decide which fields are “citation-critical” (`source_url`) for later Critic — document in model docstrings.

---

# Stage 2 — LLM fundamentals (in our codebase)

### Teaching Step 1 — Architecture

**What we build:** thin LLM adapter + demos of streaming, structured output, and a **manual** tool-call loop (no LangGraph yet).

**Alone:** scripts prove model I/O contracts.

**In the system:** same adapter used by Planner/Analysis/Critic later; mental model of “LLM proposes → program executes” is established here for interviews.

### Teaching Step 2 — Technologies & theory

- Tokens, context window, temperature, streaming
- Messages vs completions mental model
- Tool/function calling protocol
- Structured outputs / JSON schema + validation failures
- Provider keys, rate limits (high level)
- LangChain Chat Model wrapper (or official SDK first — prefer LangChain if that is the interview target; confirm current API via web research)

### Teaching Step 3 — Sequential implementation

1. Add LLM deps (`langchain`, provider package, `langchain-openai` or chosen provider).
2. Config module loads API keys from env; fail fast if missing in non-test.
3. `llm/client.py`: build chat model from settings.
4. Script/module: sync invoke with a fixed prompt about a stub asset.
5. Script/module: streaming tokens to stdout.
6. `structured/decision_card.py`: generate `DecisionCard` from stub evidence; validate with pydantic; retry once on parse failure.
7. `tools/manual_loop.py`: one tool (`get_mock_price` or live simple price HTTP); loop: model → tool_call → execute → observe → final answer; log each phase clearly.
8. Commit(s) with clear messages.
9. Update `PROGRESS.md`.

**Done when:** three demos work; logs show proposal → execute → answer; no secrets in repo.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** mock the LLM where possible; test pydantic parse failures; test tool executor with fake tool.
- **Security:** never log full API keys; redact secrets in error traces; sandbox tool allowlist (only registered tools).
- **AI QA:** assert structured output enum membership; assert tool args schema validation before execution (prevents prompt-injection-driven crazy tool args at basic level).

---

# Stage 3 — LangChain building blocks

### Teaching Step 1 — Architecture

**What we build:** reusable prompt templates + runnable chains + a **tools registry** shared by future graph nodes.

**Alone:** `plan_chain` / `analysis_chain` run on stubs without a graph.

**In the system:** nodes become thin wrappers over these runnables; interview focus: LCEL/runnables, tool descriptions as contracts.

### Teaching Step 2 — Technologies & theory

- Prompt templates (system/human), variables
- Runnables / LCEL composition (`prompt | model | parser`)
- Tool abstractions and binding tools to models
- Error propagation from tools
- Web-research current LangChain patterns (APIs change)

### Teaching Step 3 — Sequential implementation

1. `prompts/` for planner and analysis (English prompts).
2. Build runnables returning structured types where applicable.
3. Implement tools: `fetch_news`, `fetch_market` — **mocks first** with identical signatures to future real tools.
4. `tools/registry.py`: name → callable + JSON schema/description for the model.
5. Wire a small “bind tools + one-shot” demo using registry.
6. Unit tests for registry lookup and mock tools.
7. Commit: `feat: add langchain prompts runnables and tool registry`.
8. Update `PROGRESS.md`.

**Done when:** runnable pipeline tests pass; registry is the single place to add tools.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** prompt variable rendering; mock tool outputs; registry unknown-tool error.
- **Security:** tool descriptions must not instruct the model to exfiltrate env secrets; deny dangerous tools (shell, arbitrary file write) by design.
- **AI QA:** snapshot/golden strings optional; prefer schema tests over brittle full-text LLM asserts.

---

# Stage 4 — LangGraph orchestrator (MVP core)

### Teaching Step 1 — Architecture

**What we build:** the heart — a LangGraph with Planner → collect nodes → Analysis → Critic → Finalize; state; conditional edges; checkpointing; persist results to Postgres.

**Alone:** one thread_id run produces a report artifact (memory/file then DB).

**In the system:** this *is* the product runtime; Scheduler/API only trigger it. Interview gold: state, edges, checkpoints, HITL later.

### Teaching Step 2 — Technologies & theory

- Graph vs free-form agent loop (developer-defined control)
- `StateGraph`, reducers for list fields (evidence append)
- Nodes as pure-ish `(state) -> partial state`
- Conditional edges and **max iteration guards**
- Checkpointers (SQLite/Postgres), `thread_id`, resume
- Mapping graph state ↔ DB entities
- Web-research current LangGraph APIs

### Teaching Step 3 — Sequential implementation

1. Add `langgraph` (+ checkpointer deps).
2. Define `GraphState` (TypedDict or pydantic) matching Architecture §3.
3. Implement nodes with stubs/mocks: `planner`, `news_collect`, `market_collect`, `analyze`, `critique`, `finalize`.
4. Wire **linear** graph first; run end-to-end once.
5. Add conditional edges: low evidence → collect again; critic fail → analyze again; enforce `max_loops`.
6. Add checkpointer; write resume test procedure (kill mid-run / resume).
7. On finalize (and optionally mid-collect): persist run, evidence, report via Stage 1 repos.
8. Structured logging with `run_id` / `thread_id`.
9. Commits preferred per milestone (linear graph → edges → checkpoint → DB).
10. Update `PROGRESS.md`.

**Done when:** E2E graph run persists to Postgres; resume documented; max_loops prevents infinite cycles.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Unit:** reducers; routing functions with fake state; max_loops.
- **Integration:** graph with mocked LLM/tools; checkpoint resume.
- **Security:** untrusted tool output treated as data, not instructions when writing prompts for later nodes (context hygiene); limit evidence size to protect context/cost.
- **AI QA:** critic must fail if news evidence lacks URLs (even with mocks); store prompts/model names in trace metadata later.

---

# Stage 5 — Real collectors + Redis

### Teaching Step 1 — Architecture

**What we build:** production-shaped News + Market tools (real HTTP), Redis cache for market snapshots, distributed lock for idempotent runs. GitHub agent may be stubbed until Post-MVP 1.

**Alone:** calling tools returns real (or realistically shaped) evidence with citations.

**In the system:** replaces mocks inside graph nodes; Redis protects rate limits and duplicate daily work.

### Teaching Step 2 — Technologies & theory

- `httpx` timeouts, retries, backoff
- API rate limits and caching TTL
- Redis: GET/SET/EXPIRE, distributed locks (token + NX + TTL)
- Idempotency keys `research:{asset}:{date}`
- Normalizing market units; always storing `source_url` / provider ref for news
- Provider ToS / key rotation basics

### Teaching Step 3 — Sequential implementation

1. Add Redis client config from `REDIS_URL`.
2. Implement Market tool(s): fetch snapshot; cache under TTL; map to `EvidenceItem`.
3. Implement News tool(s): headlines + URLs; filter empties; map to `EvidenceItem`.
4. Swap mocks in graph for real tools behind settings flag (`USE_MOCK_TOOLS=false`).
5. Implement lock around run start; second concurrent start fails or no-ops cleanly.
6. Error handling: classify retryable vs fatal; write errors into state.
7. Manual E2E run on one asset (e.g. BTC or ETH).
8. Commits; update `PROGRESS.md`.

**Done when:** cache hit on second market call; lock works; evidence in DB has real URLs/fields; graph still completes.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** cache hit/miss with fakeredis or testcontainers; lock contention test; HTTP mock adapters for news/market.
- **Security:** API keys only in env; validate/escape URLs before rendering in reports (basic); SSRF awareness — do not let model choose arbitrary fetch URLs without allowlist/provider endpoints.
- **AI QA:** reject evidence without `source_url` for news type; log provider response sizes; never put raw secrets into evidence blobs.

---

# Stage 6 — Quality: Critic, LangSmith, evals

### Teaching Step 1 — Architecture

**What we build:** measurable research quality — strict Critic structured output, LangSmith tracing on every run, small offline eval suite.

**Alone:** eval command fails a “hallucinated” fixture report.

**In the system:** Critic gates Finalize; traces debug production issues; evals guard regressions — interview narrative for AI QA.

### Teaching Step 2 — Technologies & theory

- What is measurable: citations present, stance in enum, invalidation present, unsupported claims
- LangSmith: projects, traces, metadata (`run_id`, `asset`)
- Offline evals vs online vibe checks
- Prompt versioning mindset (even if simple constants first)
- Web-research current LangSmith setup

### Teaching Step 3 — Sequential implementation

1. Harden `Critique` model: `pass`, `issues[]`, `needs_revision`.
2. Critic node uses structured output + deterministic checks (URL presence) combined with LLM judgment.
3. Enable LangSmith env vars; ensure graph/LLM calls are traced; document how to open a trace in README.
4. Create `evals/` or `tests/evals/` with 5–10 fixtures (good / missing citations / bad stance).
5. Add `make eval` or `pytest -m eval`.
6. Commit; update `PROGRESS.md`.

**Done when:** missing-citation fixture fails; one full real run visible in LangSmith; eval command documented.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** deterministic critic rules without LLM; LLM critic mocked.
- **Security:** do not send secrets to LangSmith payloads; scrub API keys from traced inputs if needed; be aware of PII in prompts (crypto news usually low PII — still policy-aware).
- **AI QA:** define “definition of good brief”; track hallucination-style failures (invented URLs); optional faithfulness check: every claim string must fuzzy-match some evidence text (stretch goal).

---

# Stage 7 — API + scheduler skeleton (MVP complete)

### Teaching Step 1 — Architecture

**What we build:** human/machine entrypoints — FastAPI to start/fetch research; optional lightweight scheduler for watchlist; README demo path. This **closes MVP**.

**Alone:** `curl` starts a run and fetches a report Markdown/JSON.

**In the system:** API/Scheduler are triggers; graph remains the brain. Interview: sync vs background jobs, run status model.

### Teaching Step 2 — Technologies & theory

- FastAPI routes, pydantic request/response models
- Background tasks / worker pattern (start simple: background task or sync for demo; note production queue later)
- Idempotency with Redis lock at API boundary
- APScheduler or cron semantics
- OpenAPI as free documentation

### Teaching Step 3 — Sequential implementation

1. `api/app.py`: `POST /research`, `GET /research/{id}`, `GET /research/{id}/report`.
2. Map HTTP errors cleanly (404, 409 lock conflict, 500 with correlation id).
3. Wire settings + lifespan (DB pool).
4. Add scheduler module reading watchlist from config/YAML; document enabling it.
5. README: architecture blurb, bootstrap, curl demo, example report screenshot/file, product goal B disclaimer.
6. Full MVP checklist pass (below).
7. Tag or commit: `feat: mvp api and demo path`.
8. Update `PROGRESS.md` — mark MVP complete.

**Done when:** stranger can follow README and get a report in <30 minutes; MVP checklist all checked.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** API tests with TestClient; auth deferred — if no auth, document “local only”; add note for future API key middleware.
- **Security:** no debug stack traces to clients in prod mode; rate-limit note; CORS locked down; financial disclaimer in responses/README.
- **AI QA:** API returns `run_id` usable to find LangSmith trace; status lifecycle tested (`pending|running|failed|completed`).

---

# MVP Definition of Done

- [ ] E2E: request → brief + decision card + evidence in Postgres
- [ ] LangGraph conditional edges + checkpoint resume
- [ ] LangSmith trace on a successful run
- [ ] Redis cache + lock
- [ ] News + Market tools (not mocks-only)
- [ ] Critic rejects reports without evidence/citations
- [ ] Docker Compose + English README + sample report
- [ ] Docs (`START_HERE`, `PRODUCT`, `ARCHITECTURE`, this plan, `PROGRESS`) up to date

---

# Post-MVP Stage 1 — Hardening, memory, HITL, GitHub (P1)

### Teaching Step 1 — Architecture

**What we build:** production hardening and research memory — GitHub/Dev collector, pgvector similarity over past evidence, HITL plan approval, stronger logging/idempotency, scheduler used seriously.

**Alone:** approve a plan via API; retrieve similar past evidence; ingest GitHub signals.

**In the system:** improves recall and safety before scaling event infrastructure in Stage 2.

### Teaching Step 2 — Technologies & theory

- GitHub API auth, rate limits, what is a valid “dev signal” (avoid overclaiming)
- Embeddings + pgvector indexes (`ivfflat`/`hnsw` concepts)
- LangGraph interrupt / human-in-the-loop patterns (verify current API via web research)
- Structured logging (JSON), correlation IDs
- Idempotent consumers at run level

### Teaching Step 3 — Sequential implementation

1. GitHub tools + graph node (or enable stub → real).
2. Migration: embedding column / pgvector extension; embed evidence on write.
3. Query helper: top-k similar evidence for asset/question; feed into Analysis context carefully (budgeted).
4. HITL: interrupt after Planner; `POST /research/{id}/approve`; resume from checkpoint.
5. Harden errors/retries/metrics counters (even simple).
6. Scheduler daily watchlist documented and tested once.
7. Commits; update `PROGRESS.md`.

**Done when:** HITL demo works; similarity query returns past rows; GitHub evidence optional but real or explicitly disabled.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** HITL resume; vector search with known fixture embeddings; GitHub client mocked.
- **Security:** GitHub token scopes least privilege; never embed secrets; interrupt endpoints must not be open on public net without auth (add API key if exposed).
- **AI QA:** retrieved chunks cited; prevent context stuffing; eval that Analysis does not ignore Critic issues after HITL path.

---

# Post-MVP Stage 2 — Events, analytics, optional forecast (P2)

### Teaching Step 1 — Architecture

**What we build:** scale/async path — event backbone (Redis Streams first **or** Kafka), optional ClickHouse for heavy history, optional **experimental forecast module** (goal C) that **does not replace** Decision Card.

**Alone:** a market/news event can enqueue a re-research; analytics query runs on history; forecast module returns a clearly labeled experimental artifact.

**In the system:** decouples slow collectors from API; enables near-real-time refresh — classic Integration Engineer territory. Only build when MVP+P1 pain is real.

### Teaching Step 2 — Technologies & theory

- Events vs cron: when to choose
- Kafka fundamentals (topics, consumer groups, at-least-once) **or** Redis Streams as stepping stone
- ClickHouse when OLTP Postgres is wrong for analytics scans
- Separating decision support (B) from forecasting (C) in product language and APIs
- Exactly-once illusions; idempotent consumers
- Web-research current ops practices

### Teaching Step 3 — Sequential implementation

1. Write an ADR in `docs/` (English): Streams vs Kafka decision for *this* repo.
2. Implement producer from Market/News (or webhook) → stream/topic `research.triggers`.
3. Consumer worker: lock + start graph run idempotently.
4. (Optional) ClickHouse table for market ticks / run metrics; batch sync job from Postgres or direct publish.
5. (Optional) `forecast/` module: inputs = completed brief + features; output = `ExperimentalForecast` with disclaimer; never overwrite Decision Card.
6. Dashboards/notes in README: how to run worker.
7. Commits; update `PROGRESS.md`.

**Done when:** one event-driven re-research works end-to-end; if forecast exists, API labels it experimental; ClickHouse only if used by a real query.

### Teaching Step 4 — Testing / AI Security / AI QA

- **Tests:** consumer idempotency (duplicate events → one run); schema evolution note for events; forecast unit tests with frozen inputs.
- **Security:** authenticate webhooks; validate event payloads; isolate forecast so it cannot silently change stance fields.
- **AI QA:** evaluate forecast **separately** (calibration later); research evals remain source of truth for product B; chaos: kill consumer mid-message and prove resume/idempotency.

---

## Progress documentation rule

After **every** Teaching Step (1–4) session, append to `PROGRESS.md`:

- date, stage, teaching step
- status: `done | in_progress | blocked`
- what was implemented / learned
- open questions
- commands to re-verify
- “not clear yet → revisit theory of stage X step Y”

---

## Hint for a new agent

1. Read `START_HERE.md` completely (rules at top).  
2. Reply in **Russian**; keep repo docs/code **English**.  
3. **Never** write application code into the repo — chat only; self-review snippets for senior+ quality.  
4. Open `PROGRESS.md`; continue the first incomplete Teaching Step.  
5. Follow Stage → Steps 1→2→3→4; check understanding; web-research when freshness matters.  
6. Do not start Post-MVP 2 until MVP DoD is green; treat Post-MVP 1 as the default next after MVP.
