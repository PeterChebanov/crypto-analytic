# Architecture: AI Crypto Intelligence Platform

Read `START_HERE.md` first (teaching contract, language policy, no agent-written app code).

Engineering + learning map. Product goal **B** (research + decision support) — see `PRODUCT.md`.

Mental model: not “the agent went”; **the orchestrator ran the next cycle step**. The LLM proposed an action only where the graph allowed it; Python + tools executed it. **State** lives between steps.

All project docs and code: **English only**. Chat with the teacher agent: **Russian**.

---

## 1. Target logical flow

```
Scheduler / API request
        │
        ▼
 Orchestrator (LangGraph)
        │
   Planner node
        │
 ┌──────┼──────────────┐
 ▼      ▼              ▼
News  Market        GitHub/Dev
Agent Agent         Agent
 └──────┼──────────────┘
        ▼
 Research Storage (facts + raw + embeddings)
        ▼
 Analysis node
        ▼
 Critic node
        ▼
 Final Report + Decision Card
        │
        ▼
 Observability (LangSmith) + optional alerts
```

Each “agent” = node/subgraph: its tools, its slice of state, its structured outputs. The shared orchestrator owns the cycle and persistence.

---

## 2. System layers

| Layer | Purpose | Target technologies |
|-------|---------|---------------------|
| **API / Trigger** | On-demand and scheduled research | FastAPI, APScheduler or cron worker |
| **Orchestration** | Graph, state, branching, retry, HITL later | **LangGraph** (+ checkpointing) |
| **LLM glue** | Models, prompts, parsers, tools | **LangChain** |
| **Observability / Evals** | Tracing, debugging, brief quality | **LangSmith** |
| **Tools / Integrations** | Outside world | HTTP APIs (news, market), GitHub API |
| **Primary data** | Runs, reports, sources | **PostgreSQL** |
| **Cache / locks / light queues** | Quote cache, idempotency, rate limits | **Redis** |
| **Vectors** | Semantic search over evidence/briefs | **pgvector** first (or dedicated store later) |
| **Async pipeline (post-MVP 2)** | Heavy/background event delivery | **Kafka** (or Redis Streams first) |
| **Analytics OLAP (optional)** | Historical aggregates | **ClickHouse** only if needed |
| **Runtime** | Service, workers, local repro | Python 3.12+, **uv** + `pyproject.toml` + `uv.lock` (no pip), Docker Compose, pydantic, httpx, SQLAlchemy/Alembic |

---

## 3. Data and artifacts

**Run state (in graph):** `asset`, `horizon`, `question`, `plan`, `collected_evidence[]`, `gaps[]`, `analysis`, `critique`, `report`, `decision_card`, `status`, `errors`.

**Postgres (minimum):**

- `research_runs` — status, input, timestamps
- `evidence_items` — fact, source_url, source_type, raw_ref, run_id
- `reports` — brief JSON/Markdown, decision card, version
- `source_snapshots` — raw audit material (or object storage later)

**Redis:** market snapshot cache, debounce duplicate starts, distributed lock on `asset+day`.

**Vectors:** embeddings of evidence/chunks for dedupe and “similar past research”.

---

## 4. Technology rollout priority

### P0 — must for MVP demo (~2.5–3 weeks)

1. Python + FastAPI (or CLI-first + thin API)
2. LangChain: Chat Model, Prompt Templates, Tools, Structured Output, Runnables
3. LangGraph: State, nodes, conditional edges, checkpointing
4. LangSmith: tracing (+ simple evals on brief/evidence)
5. PostgreSQL + schema + indexes for run/evidence queries
6. Redis: cache + lock
7. Collectors: **News** + **Market** (GitHub right after if time)
8. Analysis + Critic + Final Report (structured)
9. Docker Compose for Postgres/Redis

### P1 — Post-MVP Stage 1 (strongly desired)

- GitHub/Dev agent
- pgvector + retrieval over past evidence
- Scheduler (daily re-research)
- Human-in-the-loop interrupt (approve plan)
- Run idempotency, solid error handling, structured logging

### P2 — Post-MVP Stage 2 (after solid core)

- Kafka (or Redis Streams → Kafka) for event-driven source updates
- ClickHouse for heavy market analytics
- Dedicated vector DB if pgvector becomes a bottleneck
- Experimental forecast layer (goal C) — separate from Decision Card

---

## 5. Interview topics → where they live

| Topic | Why interviews care | Where in product |
|-------|---------------------|------------------|
| Tokens, context, streaming | LLM basics | Prompt budgets, stream brief via API |
| Tool / function calling | Agent core | All collectors call HTTP/SQL tools |
| Structured output | Reliable contracts | Plan, evidence, decision card, report |
| Prompt templates / runnables | LangChain baseline | Shared node style |
| LangGraph State | Orchestration | Entire run state |
| Conditional edges | Routing | More collect / re-analyze loops |
| Checkpointing | Resilience | Resume after failure |
| HITL / interrupt | Production agents | Approve plan |
| LangSmith tracing | Debug | Every run |
| LangSmith evals | Quality | Citations, no invented URLs |
| Postgres + indexes | Data eng | Run/evidence queries, FKs |
| Redis | Infra | Cache, locks |
| Embeddings / vector search | RAG-lite | Dedupe + research memory |
| Kafka (P2) | Event systems | Async news/market events |
| Async Python, retries, timeouts | Production | All tools |
| Logs/metrics | Ops | Correlate with `trace_id` |

---

## 6. MVP boundary

**In MVP:** one LangGraph orchestrator; News + Market collectors; Postgres storage; Analysis + Critic; Decision Card + Brief; LangSmith tracing; Redis cache/lock; Docker Compose; README demo path.

**Out of MVP:** trading/PnL guarantees, ClickHouse, Kafka-as-must, many sources, heavy UI (CLI/API + Markdown report is enough).

---

## 7. Evolution principle

Correct **cycle + data contracts** first; scale infrastructure later.  
Add Kafka/ClickHouse only when there is real pain (event volume / analytical queries), not “for the resume”.
