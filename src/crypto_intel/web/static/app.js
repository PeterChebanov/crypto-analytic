const LAUNCHER = "http://127.0.0.1:7911";
const API = "";

const apiBadge = document.getElementById("apiBadge");
const startStackBtn = document.getElementById("startStackBtn");
const logsBtn = document.getElementById("logsBtn");
const logsCloseBtn = document.getElementById("logsCloseBtn");
const logsWindow = document.getElementById("logsWindow");
const sessionLogsView = document.getElementById("sessionLogsView");
const depsError = document.getElementById("depsError");
const depsWarn = document.getElementById("depsWarn");
const form = document.getElementById("researchForm");
const runBtn = document.getElementById("runBtn");
const runStatus = document.getElementById("runStatus");
const runError = document.getElementById("runError");
const reportPanel = document.getElementById("reportPanel");
const loadingPanel = document.getElementById("loadingPanel");
const loadingTitle = document.getElementById("loadingTitle");
const loadingDetail = document.getElementById("loadingDetail");
const loadLampGreen = document.getElementById("loadLampGreen");
const loadLampRed = document.getElementById("loadLampRed");
const priceGatePanel = document.getElementById("priceGatePanel");
const priceGateMessage = document.getElementById("priceGateMessage");
const priceQuotes = document.getElementById("priceQuotes");
const priceYesBtn = document.getElementById("priceYesBtn");
const priceNoBtn = document.getElementById("priceNoBtn");

let activeRunId = null;
const sessionLogs = [];
const SESSION_STARTED = Date.now();

function pushLog(level, message, detail) {
  const entry = {
    ts: new Date().toISOString(),
    level,
    message: String(message || ""),
    detail: detail == null ? null : String(detail),
  };
  sessionLogs.push(entry);
  if (logsWindow && !logsWindow.hidden) {
    renderSessionLogs();
  }
}

function renderSessionLogs() {
  if (!sessionLogs.length) {
    sessionLogsView.innerHTML = `<div class="log-line info">No logs yet (session started ${new Date(SESSION_STARTED).toISOString()}).</div>`;
    return;
  }
  sessionLogsView.innerHTML = sessionLogs
    .map((e) => {
      const extra = e.detail ? `\n${e.detail}` : "";
      return `<div class="log-line ${escapeHtml(e.level)}">[${escapeHtml(e.ts)}] ${escapeHtml(e.level.toUpperCase())} ${escapeHtml(e.message)}${escapeHtml(extra)}</div>`;
    })
    .join("");
  sessionLogsView.scrollTop = sessionLogsView.scrollHeight;
}

function setApiBadge(state, label) {
  apiBadge.classList.remove("ok", "bad", "warn", "blink");
  if (state === "ok") apiBadge.classList.add("ok");
  if (state === "bad") apiBadge.classList.add("bad");
  if (state === "warn") apiBadge.classList.add("warn");
  if (state === "blink") apiBadge.classList.add("blink");
  apiBadge.innerHTML = `<span class="dot"></span> ${label}`;
}

function setLoadingLamps(mode) {
  loadLampGreen.classList.remove("on", "blink");
  loadLampRed.classList.remove("on", "blink");
  if (mode === "loading") {
    loadLampGreen.classList.add("blink");
    loadLampRed.classList.add("blink");
  } else if (mode === "ok") {
    loadLampGreen.classList.add("on");
  } else if (mode === "bad") {
    loadLampRed.classList.add("on");
  }
}

function showLoading(detail) {
  loadingPanel.hidden = false;
  loadingTitle.textContent = "Research in progress";
  loadingDetail.textContent = detail || "Working…";
  setLoadingLamps("loading");
}

function finishLoading(ok, detail) {
  loadingPanel.hidden = false;
  loadingTitle.textContent = ok ? "Research finished" : "Research failed";
  loadingDetail.textContent = detail || (ok ? "Done" : "Failed");
  setLoadingLamps(ok ? "ok" : "bad");
}

function hideLoadingSoon() {
  window.setTimeout(() => {
    if (!runBtn.disabled) loadingPanel.hidden = true;
  }, 1200);
}

function fillStatusBanner(el, label, message, recommendation) {
  el.hidden = false;
  el.innerHTML =
    `<div class="status-banner-label">${escapeHtml(label)}</div>` +
    `<div class="status-banner-body">${escapeHtml(message)}</div>` +
    `<div class="status-banner-action">${escapeHtml(recommendation)}</div>`;
}

function recommendationForDeps(body) {
  const failed = (body.checks || []).filter((c) => !c.ok).map((c) => c.name);
  const tips = [];
  if (failed.includes("cryptocompare_news")) {
    tips.push(
      "News feed is unauthorized (401). Research can continue with mock/limited news; add a valid CryptoCompare key in .env when you need live headlines, or ignore this for price-only runs.",
    );
  }
  if (failed.includes("binance_futures")) {
    tips.push(
      "Futures data is unavailable. Spot research still works; forecast derivatives notes will show N/A until Binance Futures is reachable.",
    );
  }
  const hard = ["binance_spot", "kraken_spot", "coingecko", "binance_klines"];
  if (failed.some((name) => hard.includes(name))) {
    tips.push(
      "Required price venue failed. Check internet/VPN, retry in a minute, or restart the local stack (Start.command / scripts/start.sh). Do not trust forecast levels until spot probes are green.",
    );
  }
  if (!tips.length) {
    tips.push("Retry the page refresh. If it persists, open Logs and restart the local stack.");
  }
  return `What to do: ${tips.join(" ")}`;
}

async function refreshHealth() {
  depsError.hidden = true;
  depsWarn.hidden = true;
  depsError.innerHTML = "";
  depsWarn.innerHTML = "";
  setApiBadge("blink", "API: checking…");

  let localOk = false;
  try {
    const res = await fetch(`${API}/health`, { cache: "no-store" });
    localOk = res.ok;
    if (!localOk) {
      pushLog("error", "Local API /health failed", `status=${res.status}`);
    }
  } catch (err) {
    localOk = false;
    pushLog("error", "Local API offline", err.message || String(err));
  }

  if (!localOk) {
    setApiBadge("bad", "API: offline");
    fillStatusBanner(
      depsError,
      "Error",
      "Local API is offline.",
      "What to do: keep Docker Desktop running, then click Start local stack (or run Start.command / scripts/start.sh). Refresh this page after the API is up.",
    );
    return;
  }

  try {
    const res = await fetch(`${API}/health/dependencies`, { cache: "no-store" });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `deps ${res.status}`);

    for (const check of body.checks || []) {
      pushLog(
        check.ok ? "info" : "error",
        `Dependency ${check.name}: ${check.ok ? "ok" : "fail"}`,
        check.detail,
      );
    }

    if (!body.ok || body.level === "error") {
      setApiBadge("bad", "API: degraded");
      fillStatusBanner(
        depsError,
        "Error",
        body.summary || "One or more required venues failed",
        recommendationForDeps(body),
      );
      pushLog("error", "Dependency probe failed", body.summary);
      return;
    }

    if (body.level === "warn") {
      setApiBadge("ok", "API: online");
      fillStatusBanner(
        depsWarn,
        "Warning",
        body.summary || "Optional venue warning",
        recommendationForDeps(body),
      );
      pushLog("warn", "Dependency warning", body.summary);
      return;
    }

    setApiBadge("ok", "API: online");
    pushLog("info", "Dependency probe ok", body.summary);
  } catch (err) {
    setApiBadge("bad", "API: error");
    fillStatusBanner(
      depsError,
      "Error",
      String(err.message || err),
      "What to do: refresh the page. If it continues, restart the API (Start.command / scripts/start.sh) and open Logs for details.",
    );
    pushLog("error", "Dependency probe request failed", err.message || String(err));
  }
}

startStackBtn.addEventListener("click", async () => {
  runError.textContent = "";
  startStackBtn.disabled = true;
  startStackBtn.textContent = "Starting…";
  pushLog("info", "Start local stack requested");
  try {
    const res = await fetch(`${LAUNCHER}/start`, { method: "POST" });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Start failed (${res.status})`);
    }
    runStatus.textContent = body.message || "Stack started";
    pushLog("info", "Start local stack ok", body.message || "");
    await refreshHealth();
  } catch (err) {
    runError.textContent = String(err.message || err);
    pushLog("error", "Start local stack failed", err.message || String(err));
  } finally {
    startStackBtn.disabled = false;
    startStackBtn.textContent = "Start local stack";
  }
});

logsBtn.addEventListener("click", () => {
  logsWindow.hidden = false;
  renderSessionLogs();
});

logsCloseBtn.addEventListener("click", () => {
  logsWindow.hidden = true;
});

logsWindow.addEventListener("click", (event) => {
  if (event.target === logsWindow) logsWindow.hidden = true;
});

function listHtml(items) {
  if (!items || !items.length) return "<li>—</li>";
  return items.map((x) => `<li>${escapeHtml(String(x))}</li>`).join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderPriceBadge(consensus, forecast) {
  const row = document.getElementById("priceBadgeRow");
  row.innerHTML = "";
  row.hidden = true;
  const level = forecast?.price_status || consensus?.level;
  if (!level) return;
  row.hidden = false;
  const msg =
    forecast?.price_warning ||
    consensus?.message ||
    `Price status: ${level}`;
  const el = document.createElement("div");
  el.className = `price-pill ${level}`;
  el.textContent =
    level === "ok"
      ? `Price OK · ${consensus?.dispersion_pct?.toFixed?.(3) ?? forecast?.price_dispersion_pct ?? "—"}%`
      : level === "warn"
        ? `Price WARN · ${msg}`
        : `Price HARD · ${msg}`;
  row.appendChild(el);
}

function renderForecast(report) {
  const block = document.getElementById("forecastBlock");
  const cardRoot = document.getElementById("forecastCard");
  const horizons = document.getElementById("forecastHorizons");
  const jsonPre = document.getElementById("forecastJson");
  const forecast = report.forecast;
  if (!forecast) {
    block.hidden = true;
    return;
  }
  block.hidden = false;

  const trade = forecast.trade || {};
  const tendency = forecast.tendency || {};
  const sources = forecast.sources || [];
  const enterLabel = trade.enter ? "YES — enter" : "NO — do not enter";
  const enterClass = trade.enter ? "enter-yes" : "enter-no";

  const sourceHtml = sources.length
    ? `<ul class="source-list">${sources
        .map(
          (s) =>
            `<li><strong>${escapeHtml(s.kind)}</strong>: ${escapeHtml(s.detail)} ` +
            `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">source</a></li>`,
        )
        .join("")}</ul>`
    : "<p class='hint'>No sources listed</p>";

  cardRoot.innerHTML = `
    <div class="forecast-line"><span>instrument</span> ${escapeHtml(forecast.instrument || "?")}</div>
    <div class="forecast-line"><span>period</span> ${escapeHtml(forecast.period || "?")}</div>
    <div class="forecast-line"><span>as_of_price_usd</span> ${forecast.as_of_price_usd ?? forecast.reference_price_usd ?? "—"}</div>
    <div class="forecast-line"><span>ta_contract</span> ${escapeHtml(forecast.ta_contract?.candle_interval || "?")} · ATR(${forecast.ta_contract?.atr_period ?? "?"}) · ${escapeHtml(forecast.ta_contract?.sr_method || "nearest_swing")}</div>
    <div class="forecast-line"><span>period H/L</span> ${forecast.ta_contract?.period_high ?? "—"} / ${forecast.ta_contract?.period_low ?? "—"}</div>
    <div class="forecast-line"><span>swing S/R</span> ${forecast.ta_contract?.swing_support ?? trade.support ?? forecast.support ?? "—"} / ${forecast.ta_contract?.swing_resistance ?? trade.resistance ?? forecast.resistance ?? "—"}</div>
    <div class="forecast-line"><span>final_verdict</span> ${escapeHtml(forecast.final_verdict || (trade.enter ? "enter_long" : "do_not_enter"))}</div>
    <div class="forecast-line ${enterClass}"><span>enter</span> ${enterLabel}${trade.side ? ` · ${escapeHtml(trade.side)}` : ""}</div>
    <div class="forecast-line"><span>why</span> ${escapeHtml(trade.why_enter_or_skip || forecast.summary || "")}</div>
    <div class="forecast-line"><span>tendency</span> ${escapeHtml(tendency.direction || "—")} · ${tendency.change_pct ?? "—"}% · ${escapeHtml(tendency.price_basis || "first_close_to_last_close")} · ${escapeHtml(tendency.one_liner || "")}</div>
    <div class="forecast-line"><span>entry</span> ${trade.entry_price ?? "—"}</div>
    <div class="forecast-line"><span>stop_loss</span> ${trade.stop_loss ?? "—"}</div>
    <div class="forecast-line"><span>take_profit</span> ${trade.take_profit ?? "—"} <em>(${escapeHtml(trade.take_profit_source || "?")})</em></div>
    <div class="forecast-line"><span>reward_risk</span> ${trade.reward_risk ?? "—"} (min ${trade.min_reward_risk ?? 3}, preferred ${trade.preferred_reward_risk ?? 5})</div>
    <div class="forecast-line"><span>risk% / reward% / chart_range%</span> ${trade.risk_pct ?? "—"} / ${trade.reward_pct ?? "—"} / ${trade.chart_range_pct ?? "—"}</div>
    <div class="forecast-line"><span>scale_ok</span> ${trade.scale_ok ? "yes" : "no"}${trade.blocked_by_scale ? " · blocked_by_scale" : ""}</div>
    <div class="forecast-line"><span>estimated_playout</span> ${escapeHtml(forecast.estimated_playout || trade.estimated_playout || "—")}</div>
    <div class="forecast-line"><span>stop_rationale</span> ${escapeHtml(trade.stop_rationale || "—")}</div>
    <div class="forecast-line"><span>exit_rationale</span> ${escapeHtml(trade.exit_rationale || "—")}</div>
    <div class="forecast-line"><span>setup_score</span> ${forecast.setup_score ?? forecast.risk?.setup_score ?? "—"}</div>
    <div class="forecast-line"><span>decision_card</span> ${escapeHtml(forecast.decision_card_ref?.stance || report.decision?.stance || "—")}</div>
    <h4>Sources</h4>
    ${sourceHtml}
  `;

  horizons.innerHTML = "";
  for (const h of forecast.horizons || []) {
    const article = document.createElement("article");
    const rrLabel =
      h.reward_risk != null ? `R:R ${Number(h.reward_risk).toFixed(2)}` : "R:R —";
    const gateNote =
      h.action === "wait" && (h.reward_risk == null || h.reward_risk < 3)
        ? `<p class="meta warn-text">No enter: need R:R ≥ 1:3</p>`
        : "";
    article.innerHTML = `
      <h4>${escapeHtml(h.horizon)} · ${escapeHtml(h.action)} · score ${h.setup_score ?? "—"} · ${rrLabel}</h4>
      <p>${escapeHtml(h.rationale || "")}</p>
      <p class="meta">
        entry ${h.entry_price ?? "—"} · stop ${h.stop_price ?? "—"} · TP ${h.take_profit_price ?? "—"}
      </p>
      ${gateNote}
    `;
    horizons.appendChild(article);
  }

  jsonPre.textContent = JSON.stringify(
    {
      instrument: forecast.instrument,
      period: forecast.period,
      as_of_price_usd: forecast.as_of_price_usd ?? forecast.reference_price_usd,
      ta_contract: forecast.ta_contract,
      sources: forecast.sources,
      tendency: forecast.tendency,
      trade: forecast.trade,
      risk: forecast.risk,
      final_verdict: forecast.final_verdict,
      estimated_playout: forecast.estimated_playout,
      decision_card_ref: forecast.decision_card_ref,
      setup_score: forecast.setup_score,
      atr: forecast.atr,
      summary: forecast.summary,
    },
    null,
    2,
  );
}

function renderReport(payload) {
  const report = payload.report;
  if (!report) {
    reportPanel.hidden = true;
    return;
  }
  reportPanel.hidden = false;

  const decision = report.decision || {};
  document.getElementById("stance").textContent =
    `${decision.stance || "?"} · confidence ${decision.confidence ?? "?"}`;
  document.getElementById("reportMeta").textContent =
    `run ${payload.run_id} · status ${payload.status} · facts ${payload.facts?.length ?? 0}`;
  document.getElementById("brief").textContent = report.brief || "";
  document.getElementById("rationale").textContent = decision.rationale || "";
  document.getElementById("invalidation").innerHTML = listHtml(decision.invalidation);
  document.getElementById("gaps").innerHTML = listHtml(report.gaps);
  document.getElementById("risks").innerHTML = listHtml(report.risks_and_catalysts);
  document.getElementById("watchlist").innerHTML = listHtml(report.watchlist);
  renderForecast(report);
  renderPriceBadge(payload.price_consensus, report.forecast);

  const factsRoot = document.getElementById("facts");
  factsRoot.innerHTML = "";
  for (const fact of payload.facts || []) {
    const article = document.createElement("article");
    const url = fact.source_url
      ? `<p><a href="${escapeHtml(fact.source_url)}" target="_blank" rel="noopener">${escapeHtml(fact.source_url)}</a></p>`
      : "";
    article.innerHTML = `
      <h3>[${escapeHtml(fact.source_type)}] ${escapeHtml(fact.title)}</h3>
      <p>${escapeHtml(fact.summary)}</p>
      ${url}
    `;
    factsRoot.appendChild(article);
  }

  fetch(`${API}/research/${payload.run_id}/logs`)
    .then((res) => res.json())
    .then((body) => {
      for (const entry of body.entries || []) {
        pushLog("info", `run ${payload.run_id} · ${entry.kind || "log"}`, JSON.stringify(entry));
      }
    })
    .catch((err) => pushLog("warn", "Could not load run logs", err.message || String(err)));
}

function showPriceGate(status) {
  priceGatePanel.hidden = false;
  const c = status.price_consensus;
  priceGateMessage.textContent =
    status.error_message ||
    c?.message ||
    "Only one price source succeeded. Continue with degraded price?";
  priceQuotes.innerHTML = "";
  for (const q of c?.quotes || []) {
    const row = document.createElement("div");
    row.className = q.ok ? "ok" : "bad";
    row.textContent = q.ok
      ? `${q.source}: $${q.price_usd}`
      : `${q.source}: FAILED (${q.error || "error"})`;
    priceQuotes.appendChild(row);
  }
}

function hidePriceGate() {
  priceGatePanel.hidden = true;
}

async function pollUntilDone(runId) {
  const started = Date.now();
  while (Date.now() - started < 10 * 60 * 1000) {
    const res = await fetch(`${API}/research/${runId}`);
    if (!res.ok) throw new Error(`Status check failed (${res.status})`);
    const data = await res.json();
    runStatus.textContent = `Status: ${data.status}`;
    loadingDetail.textContent = `Status: ${data.status}`;
    pushLog("info", `Research status ${data.status}`, runId);
    if (data.status === "awaiting_price_confirmation") {
      return data;
    }
    if (data.status === "completed" || data.status === "failed") {
      return data;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error("Timed out waiting for research to finish");
}

async function confirmPrice(accept) {
  if (!activeRunId) return;
  priceYesBtn.disabled = true;
  priceNoBtn.disabled = true;
  showLoading(accept ? "Continuing with degraded price…" : "Skipping forecast…");
  runStatus.textContent = accept ? "Continuing with degraded price…" : "Skipping forecast…";
  try {
    const res = await fetch(`${API}/research/${activeRunId}/confirm-price`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accept }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Confirm failed (${res.status})`);
    hidePriceGate();
    if (body.status === "failed") {
      throw new Error(body.error_message || "Confirmation failed");
    }
    const reportRes = await fetch(`${API}/research/${activeRunId}/report`);
    const reportBody = await reportRes.json();
    if (!reportRes.ok) throw new Error(reportBody.detail || "Failed to load report");
    renderReport(reportBody);
    runStatus.textContent = "Completed";
    finishLoading(true, "Completed");
    hideLoadingSoon();
  } catch (err) {
    runError.textContent = String(err.message || err);
    runStatus.textContent = "Failed";
    pushLog("error", "Price confirm failed", err.message || String(err));
    finishLoading(false, String(err.message || err));
  } finally {
    priceYesBtn.disabled = false;
    priceNoBtn.disabled = false;
  }
}

priceYesBtn.addEventListener("click", () => confirmPrice(true));
priceNoBtn.addEventListener("click", () => confirmPrice(false));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  runError.textContent = "";
  reportPanel.hidden = true;
  hidePriceGate();
  runBtn.disabled = true;
  showLoading("Starting research…");
  runStatus.textContent = "Starting…";
  pushLog("info", "Research started");

  const cryptocurrency = document.getElementById("cryptocurrency").value.trim();
  const period = document.getElementById("period").value;
  const mode = document.getElementById("mode").value;
  const questionRaw = document.getElementById("question").value.trim();
  const body = {
    cryptocurrency,
    period,
    mode,
    question: questionRaw ? questionRaw : null,
    accept_degraded_price: false,
  };

  try {
    const createRes = await fetch(`${API}/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const createBody = await createRes.json().catch(() => ({}));
    if (!createRes.ok) {
      throw new Error(createBody.detail || `Create failed (${createRes.status})`);
    }

    activeRunId = createBody.run_id;
    runStatus.textContent = `Queued ${activeRunId}`;
    loadingDetail.textContent = `Queued ${activeRunId}`;
    pushLog("info", "Research queued", activeRunId);

    const finalStatus = await pollUntilDone(activeRunId);
    if (finalStatus.status === "failed") {
      throw new Error(finalStatus.error_message || "Research failed");
    }
    if (finalStatus.status === "awaiting_price_confirmation") {
      showPriceGate(finalStatus);
      runStatus.textContent = "Awaiting price confirmation";
      finishLoading(true, "Awaiting price confirmation");
      const reportRes = await fetch(`${API}/research/${activeRunId}/report`);
      const reportBody = await reportRes.json();
      if (reportRes.ok) renderReport(reportBody);
      pushLog("warn", "Awaiting price confirmation", activeRunId);
      return;
    }

    const reportRes = await fetch(`${API}/research/${activeRunId}/report`);
    const reportBody = await reportRes.json();
    if (!reportRes.ok) {
      throw new Error(reportBody.detail || "Failed to load report");
    }
    renderReport(reportBody);
    runStatus.textContent = "Completed";
    finishLoading(true, "Completed");
    hideLoadingSoon();
    pushLog("info", "Research completed", activeRunId);
  } catch (err) {
    runError.textContent = String(err.message || err);
    runStatus.textContent = "Failed";
    finishLoading(false, String(err.message || err));
    pushLog("error", "Research failed", err.message || String(err));
  } finally {
    runBtn.disabled = false;
    refreshHealth();
  }
});

pushLog("info", "UI session started");
refreshHealth();
