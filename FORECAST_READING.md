# Forecast system — snapshot & change log

Experimental forecast mode for personal testing. **Not financial advice.**

---

## System now (short)

**Modes:** `analytics` | `forecast` (analytics first, then TA layer).

**Pipeline:**

```text
facts/brief (LLM) → Decision Card stance (LLM)
                 → coherence (code): new enter only if accumulate
                 → TA (code): OHLCV, swing S/R, ATR, R:R, chart-scale, volume, OI
                 → final_verdict / trade.enter (code; LLM only polishes text)
```

**Enter gates (all required):** stance=`accumulate` · R:R≥1:3 · chart-scale (stop≥10% of period H/L) · structure ok.

**Read order:** `decision.stance` → `final_verdict` → `ta_contract` → levels / R:R / `estimated_playout`.

**Important:** `period` = analysis chart lookback. `estimated_playout` = how long *this* setup may take. They are not the same. Dual inputs (`analysis_period` + `forecast_horizon`) are still TODO.

**Run:** `./scripts/start.sh` or `Start.command` → http://127.0.0.1:8000/

**Field glossary / open items:** see sections below if needed; full history of LLM debates summarized in the change log.

---

## Change log — three LLM review cycles (2026-08-12)

### Iteration 1 — ETH 7d (`avoid` vs `enter`)

| | |
|--|--|
| **Problem** | Analytics `avoid`, forecast still `enter` (R:R-only gate). |
| **Found by** | Live run + human/LLM review of contradictory JSON. |
| **Change** | `forecast/coherence.py`; enter only if `accumulate`; `final_verdict`, `blocked_by_decision`; finalize overwrites LLM. |
| **Where** | `forecast/coherence.py`, `forecast/engine.py`, `domain/models.py`, tests, UI. |

### Iteration 2 — Number clarity (ETH / multi-LLM audit)

| | |
|--|--|
| **Problem** | Swing S/R read as weekly levels; ATR TF unclear; TP≠resistance; R:R audited wrong vs rounded prices. |
| **Found by** | Three LLMs disagreed on S/R, ATR, TP 1943 vs R 1882. |
| **Change** | `ta_contract` (interval, ATR period, period H/L vs swing); `take_profit_source`; R:R after `round(4)`; tendency `price_basis`. |
| **Where** | `domain/models.py`, `pricing/history.py`, `forecast/engine.py`, `web/static/app.js`, this doc. |

### Iteration 3 — Scale / anti-scalp (USDT, SOL, USDT 30d)

| | |
|--|--|
| **Problem** | Formal 1:3 on micro peg noise (USDT) → false `enter_long`; scalping vs chart window. |
| **Found by** | USDT live JSON + LLM reviews; confirmed on SOL (`scale_ok=false`) and USDT 30d (`R:R&lt;3` → no enter). |
| **Change** | Chart-scale gate: stop ≥10% of period H/L; `scale_ok` / `blocked_by_scale`; `%` fields; `estimated_playout` (lookback ≠ hold). No stablecoin special case — same rules for all assets. USDT pair map `USDTUSD` / Kraken / CoinGecko. |
| **Where** | `forecast/scoring.py`, `forecast/engine.py`, `pricing/quotes.py`, `pricing/history.py`, `tools/symbols.py`, UI, tests. |

---

## How to use (minimal)

1. Docker up → `./scripts/start.sh`
2. UI: asset, period, mode `forecast`
3. Trust **code gates** over narrative; check `ta_contract` before judging S/R or ATR
4. Logs: UI Logs tab / `logs/sessions/`

---

## Still open (next after manual QA)

- Dual inputs: `analysis_period` + `forecast_horizon`
- Spot trade URL from real pair (fix `USDT_USDT` template)
- News quality (CryptoCompare 401 / mock fallback)
- Optional: volume hard-gate; richer playout vs user horizon

---

## Abbreviations

OHLCV · S/R (Support/Resistance) · ATR (Average True Range) · R:R (Reward:Risk) · TP (Take Profit) · OI (Open Interest) · TA · LLM
