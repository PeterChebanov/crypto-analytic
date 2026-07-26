# AI Crypto Intelligence Platform — what it is and why

## One sentence

The system helps you quickly see **what matters for a cryptocurrency right now**, **which facts support that view**, and **what cautious stance is reasonable** — without promising to predict the future price.

## Why it exists

Crypto is noisy: news, project GitHub activity, prices, volumes, rumors. Doing this manually every day is slow and easy to get wrong.

This platform does analyst work:

1. Collects information from multiple sources for a chosen **cryptocurrency** (e.g. Bitcoin or Ethereum).
2. Separates facts from speculation and marks missing data.
3. Produces a clear **research brief**.
4. Gives a **cautious action stance** (accumulate / hold / reduce / avoid) plus **invalidation** conditions — when the thesis should be revisited.

A forecast like “price will be +X% tomorrow” is **not** the goal of this version. Buy/sell decisions stay with the human. The system is responsible for collection quality and argument clarity.

## Domain vocabulary (code names)

| Term in code | Plain meaning |
|--------------|---------------|
| `cryptocurrency` | Which coin to research (e.g. ETH) |
| `period` | How far back to look (e.g. 7d, 30d) — news, market, charts |
| `Fact` | One concrete finding (not a website; many facts can come from one site) |
| `DecisionCard` | Short advice: what to do carefully, why, when to rethink |
| `ResearchReport` | Final document the user reads |
| `Critique` | Internal quality check before publishing the report |

## What you get

For a request like “analyze ETH for the last 7 days”, the system returns:

| Part | In plain language |
|------|-------------------|
| **Research Brief** | Short text: what happened, what matters, what is still unknown |
| **Facts** | Concrete findings with source links |
| **Contradictions & gaps** | Where sources disagree or data is missing |
| **Risks & catalysts** | What *may* move the cryptocurrency (unlocks, hacks, listings, etc.) — no guaranteed direction |
| **Decision Card** | Stance + confidence + why |
| **Invalidation** | Which new facts would kill the thesis |
| **Watchlist** | What to monitor next and when to re-run research |

An experimental price-forecast layer may be added later — it is not the product core.

## How to use it (simple flow)

1. **Start research** for a cryptocurrency and period (e.g. ETH, 7 days) or a question (“any major unlock risk?”).
2. **Wait for the collection cycle**: news, market data, development activity (where applicable).
3. **Read the report**: Brief and Decision Card first; Facts when you want to verify.
4. **Act yourself**: buying/selling is your call. The system is not a trade order.
5. **Re-run on a schedule** (e.g. daily) or on alerts when material facts change.

## Practical value

- Saves hours of manual searching.
- Provides an **audit trail**: you can see what the conclusion rests on.
- Reduces decisions driven by a single emotional headline.
- Strong portfolio piece: a real AI research system, not a chat toy.

## What it deliberately does not do

- Does not guarantee profit.
- Is not formal financial advice.
- Does not replace your own diligence before a large trade.
- Does not promise accurate price prediction in the base version (goal **B**: research + decision support).

## Bottom line

**Input:** cryptocurrency + period (+ optional question).  
**Work:** collect → verify → analyze → critique → report.  
**Output:** clear brief + facts + cautious stance with invalidation.  
**User:** reads, checks what matters, decides.
