const LAUNCHER = "http://127.0.0.1:7911";
const API = "";

const apiBadge = document.getElementById("apiBadge");
const launcherBadge = document.getElementById("launcherBadge");
const startStackBtn = document.getElementById("startStackBtn");
const form = document.getElementById("researchForm");
const runBtn = document.getElementById("runBtn");
const runStatus = document.getElementById("runStatus");
const runError = document.getElementById("runError");
const reportPanel = document.getElementById("reportPanel");
const priceGatePanel = document.getElementById("priceGatePanel");
const priceGateMessage = document.getElementById("priceGateMessage");
const priceQuotes = document.getElementById("priceQuotes");
const priceYesBtn = document.getElementById("priceYesBtn");
const priceNoBtn = document.getElementById("priceNoBtn");

let activeRunId = null;

function setBadge(el, ok, label) {
  el.classList.toggle("ok", ok === true);
  el.classList.toggle("bad", ok === false);
  el.innerHTML = `<span class="dot"></span> ${label}`;
}

async function refreshHealth() {
  try {
    const res = await fetch(`${API}/health`, { cache: "no-store" });
    setBadge(apiBadge, res.ok, res.ok ? "API: online" : "API: error");
  } catch {
    setBadge(apiBadge, false, "API: offline");
  }

  try {
    const res = await fetch(`${LAUNCHER}/status`, { cache: "no-store" });
    if (!res.ok) throw new Error("bad status");
    const data = await res.json();
    const ok = Boolean(data.launcher);
    setBadge(
      launcherBadge,
      ok,
      ok
        ? `Launcher: online${data.docker ? " · Docker OK" : " · Docker down"}`
        : "Launcher: error",
    );
  } catch {
    setBadge(launcherBadge, false, "Launcher: offline (run Start.command)");
  }
}

startStackBtn.addEventListener("click", async () => {
  runError.textContent = "";
  startStackBtn.disabled = true;
  startStackBtn.textContent = "Starting…";
  try {
    const res = await fetch(`${LAUNCHER}/start`, { method: "POST" });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Start failed (${res.status})`);
    }
    runStatus.textContent = body.message || "Stack started";
    await refreshHealth();
  } catch (err) {
    runError.textContent =
      `${err.message}\n\n` +
      "If launcher is offline: double-click Start.command (or run scripts/start.sh) while Docker Desktop is running.";
  } finally {
    startStackBtn.disabled = false;
    startStackBtn.textContent = "Start local stack";
  }
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
  document.querySelector('.tab[data-tab="result"]').click();

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

  loadLogs(payload.run_id);
}

async function loadLogs(runId) {
  const pre = document.getElementById("logsPre");
  try {
    const res = await fetch(`${API}/research/${runId}/logs`);
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "logs failed");
    pre.textContent = body.entries.length
      ? body.entries.map((e) => JSON.stringify(e)).join("\n")
      : "(no external API log entries yet)";
  } catch (err) {
    pre.textContent = String(err.message || err);
  }
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
  } catch (err) {
    runError.textContent = String(err.message || err);
    runStatus.textContent = "Failed";
  } finally {
    priceYesBtn.disabled = false;
    priceNoBtn.disabled = false;
  }
}

priceYesBtn.addEventListener("click", () => confirmPrice(true));
priceNoBtn.addEventListener("click", () => confirmPrice(false));

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const name = btn.dataset.tab;
    document.getElementById("tab-result").hidden = name !== "result";
    document.getElementById("tab-logs").hidden = name !== "logs";
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  runError.textContent = "";
  reportPanel.hidden = true;
  hidePriceGate();
  runBtn.disabled = true;
  runStatus.textContent = "Starting…";

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
    const finalStatus = await pollUntilDone(activeRunId);
    if (finalStatus.status === "failed") {
      throw new Error(finalStatus.error_message || "Research failed");
    }
    if (finalStatus.status === "awaiting_price_confirmation") {
      showPriceGate(finalStatus);
      runStatus.textContent = "Awaiting price confirmation";
      const reportRes = await fetch(`${API}/research/${activeRunId}/report`);
      const reportBody = await reportRes.json();
      if (reportRes.ok) renderReport(reportBody);
      return;
    }

    const reportRes = await fetch(`${API}/research/${activeRunId}/report`);
    const reportBody = await reportRes.json();
    if (!reportRes.ok) {
      throw new Error(reportBody.detail || "Failed to load report");
    }
    renderReport(reportBody);
    runStatus.textContent = "Completed";
  } catch (err) {
    runError.textContent = String(err.message || err);
    runStatus.textContent = "Failed";
  } finally {
    runBtn.disabled = false;
    refreshHealth();
  }
});

refreshHealth();
setInterval(refreshHealth, 5000);
