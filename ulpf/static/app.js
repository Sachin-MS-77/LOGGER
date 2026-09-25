"use strict";
const savedTheme = localStorage.getItem("logflux-interface-theme") || "midnight";
document.documentElement.dataset.theme = ["daylight", "midnight", "crimson"].includes(savedTheme) ? savedTheme : "midnight";
document.querySelector("#theme-select").value = document.documentElement.dataset.theme;
document.querySelector("#theme-select").addEventListener("change", (event) => {
  document.documentElement.dataset.theme = event.target.value;
  localStorage.setItem("logflux-interface-theme", event.target.value);
});
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const fmt = (v) => Number(v || 0).toLocaleString();
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const short = (v, n = 14) =>
  String(v || "").length > n ? String(v).slice(0, n) + "…" : String(v || "—");
const date = (v) =>
  v
    ? new Date(v).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "Not yet received";
const clock = (v) =>
  v ? new Date(v).toLocaleTimeString([], { hour12: false }) : "—";
const bytes = (v) =>
  v >= 1e6
    ? (v / 1e6).toFixed(1) + " MB"
    : v >= 1e3
      ? (v / 1e3).toFixed(1) + " KB"
      : v + " B";
const icons = {
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  stream: "M3 7h18 M3 12h12 M3 17h15",
  sources: "M4 3h16v6H4z M4 15h16v6H4z M7 6h.01 M7 18h.01 M12 9v6",
  lab: "M9 3h6 M10 3v7L4 20h16l-6-10V3 M8 15h8",
  shield: "M12 3 3 6v6c0 5 9 9 9 9s9-4 9-9V6l-9-3z M8 12l3 3 5-6",
  graph:
    "M8 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M22 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M10 20a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M8 6l8 5 M8 18l8-5 M5 8l1 9",
  settings:
    "M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2",
  arrow: "M5 12h14 M14 7l5 5-5 5",
  down: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
  plus: "M12 5v14 M5 12h14",
  play: "m8 4 12 8-12 8z",
  check: "M5 12l4 4L19 6",
  x: "M6 6l12 12 M18 6 6 18",
  refresh: "M20 7v5h-5 M4 17v-5h5 M19 8a8 8 0 0 0-14-3 M5 16a8 8 0 0 0 14 3",
  activity: "M2 12h5l3-8 4 16 3-8h5",
  database:
    "M20 5c0 2-16 2-16 0s16-2 16 0v14c0 2-16 2-16 0V5 M4 12c0 2 16 2 16 0",
  info: "M12 10v7 M12 7h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  upload: "M12 16V3 M7 8l5-5 5 5 M4 17v4h16v-4",
  external: "M14 3h7v7 M10 14 21 3 M10 3H3v18h18v-7",
  time: "M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  file: "M14 2H4v20h16V8l-6-6z M14 2v6h6 M8 12h8 M8 16h6",
  bolt: "m13 2-9 12h7l-1 8 10-13h-7z",
  search: "M17 17l5 5 M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  lock: "M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4",
  chevron: "m9 5 7 7-7 7",
  network: "M9 2h6v6H9z M2 16h6v6H2z M16 16h6v6h-6z M12 8v4 M5 16v-4h14v4",
};
const icon = (name, cls = "") =>
  `<svg class="${cls}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.file}"/></svg>`;
const nav = [
  ["overview", "Command center", "overview"],
  ["events", "Event stream", "stream"],
  ["sources", "Sources", "sources"],
  ["lab", "Parser lab", "lab"],
  ["evidence", "Evidence vault", "shield"],
  ["investigate", "Investigation", "graph"],
  ["system", "System & outputs", "settings"],
];
const S = {
  page: "overview",
  token: sessionStorage.getItem("logflux-token") || "",
  stats: null,
  system: null,
  candidateId: null,
  candidate: null,
  labTab: "mapping",
  eventId: null,
  eventTab: "event",
  event: null,
  modal: null,
  filters: { q: "", status: "", mode: "", source: "", offset: 0 },
  ip: "",
  graphSource: "",
  graphMinutes: "0",
  graphZoom: 1,
  analyticsTab: "events",
  graph: null,
  busy: false,
  paused: false,
  expectations: {},
  renderSeq: 0,
};
const badge = (v, kind) =>
  `<span class="badge ${kind || { normalized: "green", partial: "amber", unparsed: "amber", drifted: "red", failed: "red", queued: "blue", allow: "green", deny: "red", alert: "amber", live: "green", replay: "blue", lab: "amber", approved: "green", validated: "blue", draft: "amber", high: "red", critical: "red", medium: "amber" }[v] || ""}">${esc(v)}</span>`;
const button = (text, action, ic = "", cls = "", attrs = "") =>
  `<button class="button ${cls}" data-action="${action}" ${attrs}>${ic ? icon(ic) : ""}${text}</button>`;
const empty = (title, text, action = "") =>
  `<div class="empty">${icon("database")}<h3>${title}</h3><p>${text}</p>${action}</div>`;
const notice = (text, kind = "") =>
  `<div class="notice ${kind}">${icon("info")}<div>${text}</div></div>`;
const header = (eyebrow, title, description, actions = "") =>
  `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${description}</p></div><div class="button-group">${actions}</div></div>`;
const panel = (title, body, right = "", description = "") =>
  `<section class="panel"><div class="panel-head"><div><h2>${title}</h2>${description ? `<p>${description}</p>` : ""}</div>${right}</div>${body}</section>`;
function toast(message, error = false) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), 6500);
}
async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    ...options,
    headers: {
      Authorization: "Bearer " + S.token,
      ...(options.body && typeof options.body === "string"
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
  });
  if (response.status === 401) {
    $("#login").hidden = false;
    $("#connection").className = "connection";
    throw new Error("Your access token is required.");
  }
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = { detail: response.statusText };
    }
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  }
  return options.raw ? response : response.json();
}
const post = (path, body = {}) =>
  api(path, { method: "POST", body: JSON.stringify(body) });
async function download(path, name) {
  const response = await api(path, { raw: true });
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function navRender() {
  $("#navigation").innerHTML = nav
    .map(
      ([id, title, ic]) =>
        `<a class="nav-item ${S.page === id ? "active" : ""}" href="#${id}" title="${title}">${icon(ic)}<span>${title}</span>${id === "lab" && S.stats?.pending_review ? `<span class="nav-count">${S.stats.pending_review}</span>` : ""}</a>`,
    )
    .join("");
  $("#crumb").textContent = nav.find((n) => n[0] === S.page)?.[1] || "Overview";
}
function showConnection(ok) {
  $("#connection").className = "connection" + (ok ? " connected" : "");
  $("#connection").innerHTML =
    `<i></i>${ok ? "Connected locally" : "Connection lost"}`;
}
async function refresh(force = false) {
  if (!S.token || S.busy || (S.paused && !force)) return;
  const seq = ++S.renderSeq;
  try {
    const [stats, system] = await Promise.all([api("/stats"), api("/status")]);
    if (seq !== S.renderSeq) return;
    S.stats = stats;
    S.system = system;
    showConnection(true);
    navRender();
    if (
      force ||
      (!S.modal &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(
          document.activeElement.tagName,
        ) &&
        ["overview", "events"].includes(S.page))
    )
      await render();
  } catch (e) {
    showConnection(false);
    if (force) toast(e.message, true);
  }
}
function metric(label, value, unit, foot, ic, extra = "") {
  return `<div class="metric ${extra}"><div class="metric-head">${label}${icon(ic)}</div><div class="metric-value">${value}${unit ? `<span>${unit}</span>` : ""}</div><div class="metric-foot">${foot}</div></div>`;
}
function chart(data = S.stats.timeline) {
  if (!data.length)
    return empty(
      "Your telemetry starts here",
      "Connect a device or run the labeled replay to see incoming events.",
    );
  const W = 650,
    H = 150,
    p = 20,
    max = Math.max(...data.map((d) => d.count), 1);
  const points = data.map((d, i) => [
    p +
      (data.length === 1
        ? (W - 2 * p) / 2
        : (i / (data.length - 1)) * (W - 2 * p)),
    H - 18 - (d.count / max) * (H - 40),
  ]);
  const line = points.map(([x, y]) => `${x},${y}`).join(" ");
  const area = `${points[0][0]},${H - 18} ${line} ${points.at(-1)[0]},${H - 18}`;
  return `<div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Actual events received per minute"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#60d6ed" stop-opacity=".23"/><stop offset="100%" stop-color="#60d6ed" stop-opacity=".015"/></linearGradient></defs>${[0, 1, 2, 3].map((i) => `<line x1="${p}" y1="${22 + i * 36}" x2="${W - p}" y2="${22 + i * 36}" stroke="#edf1f5" stroke-dasharray="3 5"/><text x="${W - 5}" y="${25 + i * 36}" text-anchor="end" fill="#a7b2c0" font-size="9">${Math.round(max * (1 - i / 3))}</text>`).join("")}<polygon points="${area}" fill="url(#chart-fill)"/><polyline points="${line}" fill="none" stroke="#60d6ed" stroke-width="2.5" stroke-linejoin="round"/>${points.map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="3.2" fill="#102737" stroke="#60d6ed" stroke-width="2"><title>${data[i].minute}: ${data[i].count} events</title></circle>`).join("")}</svg></div><div class="chart-caption"><span>${esc(data[0].minute.slice(11))}</span><span>Events / minute · receipt time</span><span>${esc(data.at(-1).minute.slice(11))}</span></div>`;
}
function eventTable(items, { compact = false } = {}) {
  if (!items.length)
    return empty(
      "No events to show",
      "Incoming device logs appear here. You can also import a file or run the synthetic replay.",
      button("Connect a source", "add-source", "plus", "small"),
    );
  return `<div class="table-scroll"><table class="event-table"><thead><tr><th>Received</th><th>Source</th><th>Source → destination</th><th>Action</th><th>Processing</th>${compact ? "" : "<th>Format</th>"}<th></th></tr></thead><tbody>${items
    .map((e) => {
      const n = e.normalized || {};
      return `<tr><td><span class="mono tiny">${clock(e.received_at)}</span><span class="source-sub">${esc(new Date(e.received_at).toLocaleDateString([], { month: "short", day: "numeric" }))}</span></td><td><div class="table-source"><span class="source-icon">${icon(e.source.includes("Suricata") ? "shield" : e.source.includes("Router") ? "network" : "sources")}</span><div><button class="row-button" data-action="event" data-id="${e.id}">${esc(short(e.source, 25))}</button><span class="source-sub">${esc(e.mode)} · ${esc(e.transport)}</span></div></div></td><td><div class="endpoint mono">${esc(n.source_ip || "—")} <small>→</small> ${esc(n.destination_ip || "—")}</div><span class="source-sub">${esc(n.protocol?.toUpperCase() || "Unmapped")}${n.destination_port !== undefined && n.destination_port !== null ? " / " + n.destination_port : ""}</span></td><td>${badge(n.action || "unknown")}</td><td>${badge(e.status)}</td>${compact ? "" : `<td><span class="badge outline">${esc(e.format)}</span></td>`}<td><button class="icon-button" data-action="event" data-id="${e.id}" title="Inspect event" aria-label="Inspect event ${esc(e.id)}">${icon("chevron")}</button></td></tr>`;
    })
    .join("")}</tbody></table></div>`;
}
function spark(values) {
  const max = Math.max(1,...values);
  return `<svg class="spark" viewBox="0 0 100 30" role="img" aria-label="Observed activity, last 30 minutes">${values.filter((_,i)=>i%2===0).map((v,i)=>`<line x1="${4+i*6.5}" x2="${4+i*6.5}" y1="28" y2="${28-v/max*24}" opacity="${v?1:.2}"/>`).join("")}</svg>`;
}
function activityBins(items, field, unique) {
  return S.stats.timeline.map(bin=>({minute:bin.minute,count:unique ? new Set(items.filter(x=>String(x[field]||"").slice(0,16)===bin.minute).map(x=>x[unique])).size : items.filter(x=>String(x[field]||"").slice(0,16)===bin.minute).length}));
}
function signalFeed(alerts, limit=4) {
  return `<div class="signal-feed">${alerts.slice(0,limit).map(a=>`<div class="signal-item"><span class="signal-symbol ${(a.severity||"").toLowerCase()}">${icon("bolt")}</span><div class="signal-content"><div class="signal-title">${badge(a.severity)}<span class="tiny muted">Rule match</span></div><button class="row-button" data-action="event" data-id="${esc(a.event_id)}">${esc(a.title)}</button><div class="signal-meta"><span>${esc(a.rule)}</span><span>· ${esc(a.source)}</span><span>· ${esc(a.mode)}</span></div><div class="signal-meta"><span>${date(a.created_at)}</span><span>· Observed</span></div></div></div>`).join("") || `<div class="empty"><p>No detection rules matched in this scope.</p></div>`}</div>`;
}
function distribution(rows) {
  const total=rows.reduce((sum,x)=>sum+x.count,0);
  return `<div class="distribution">${rows.map(x=>`<div class="dist-row"><span title="${esc(x.name)}">${esc(x.name)}</span><div class="progress"><span style="width:${pct(x.count,total)}%"></span></div><strong>${fmt(x.count)}</strong></div>`).join("") || '<p class="muted tiny">No observations yet.</p>'}</div>`;
}
async function overview() {
  const s=S.stats;
  const [recent,g,alerts,cases]=await Promise.all([api("/events?limit=5"),api("/graph"),api("/alerts"),api("/cases")]);
  const graphBins=activityBins(g.timeline,"received_at");
  const series={events:s.timeline,signals:activityBins(alerts,"created_at"),cases:activityBins(cases,"created_at"),sources:activityBins(g.timeline,"received_at","source"),relationships:graphBins};
  const names={events:"Events",signals:"Detection signals",cases:"Investigations",sources:"Sources",relationships:"Relationships"};
  const relationships=new Set(g.edges.map(e=>e.source+"|"+e.target)).size;
  const values=[s.total,cases.length,s.alerts,relationships,s.source_count];
  const labels=["Total events","Saved investigations","Detection signals","Observed relationships","Data sources"];
  const desc=["All received events","All saved cases · no closure workflow","All rule matches", "Unique IP pairs · latest 1,000 events", "All registered sources"];
  const symbols=["database","file","bolt","graph","sources"];
  const trends=[series.events,series.cases,series.signals,series.relationships,series.sources];
  const current=series[S.analyticsTab];
  const activityTotal=current.reduce((n,x)=>n+x.count,0);
  const live=s.modes.find(x=>x.mode==="live")?.count||0;
  const listeners=Object.values(S.system.listeners).filter(x=>x.listening).length;
  const colors=["#ba92ed","#ee9ac4","#83cde7","#e4c581","#8dd9b0"];
  const severity=Object.entries(alerts.reduce((o,a)=>(o[a.severity]=(o[a.severity]||0)+1,o),{})).map(([name,count])=>({name,count}));
  return header("LOGFLUX / SECURITY OPERATIONS","Command center","Your telemetry. Connected, traceable, ready to investigate.",button("Connect source","add-source","plus")+button(S.system.demo.running?"Replay running…":"Run demo replay","demo","play","primary",S.system.demo.running?"disabled":""))+
   `<div class="status-strip"><span class="pulse">${listeners?"COLLECTOR ONLINE":"COLLECTOR OFFLINE"}</span><span>${listeners} listening transports</span><span>${fmt(s.plugins)} signed parsers</span><span class="right">${fmt(live)} live · ${fmt(s.total-live)} replay / lab events</span></div>`+
   `<div class="metrics five">${values.map((v,i)=>`<article class="metric"><div class="metric-head"><span>${labels[i]}</span>${icon(symbols[i])}</div><div class="metric-topline"><div class="metric-value">${fmt(v)}</div>${spark(trends[i].map(x=>x.count))}</div><div class="metric-foot">${desc[i]}<br><span class="muted">Bars: last 30 min${i===3?" · pair events":i===4?" · observed sources":""}</span></div></article>`).join("")}</div>`+
   `<div class="intelligence-grid">${panel("Investigation intelligence",`<div class="analytics-tabs">${Object.entries(names).map(([key,name])=>`<button class="analytics-tab ${S.analyticsTab===key?"active":""}" data-action="analytics-tab" data-tab="${key}" aria-pressed="${S.analyticsTab===key}">${name}</button>`).join("")}</div><div class="analytics-summary"><div><strong>${fmt(activityTotal)}</strong><small>${S.analyticsTab==="sources"?"Sum of source-minute observations":names[S.analyticsTab]+" in this window"}</small></div><div><strong>${fmt(Math.max(0,...current.map(x=>x.count)))}</strong><small>Peak per minute</small></div></div>${chart(current)}<div class="table-footer"><span>${S.analyticsTab==="events"?"All received events":S.analyticsTab==="signals"?"Latest 100 detection records":S.analyticsTab==="cases"?"Saved case creation times":"Latest 1,000 matching events · receipt time"} · UTC</span><span class="chart-legend"><i class="legend-dot"></i>Observed activity</span></div>`,`<span class="range-button">${icon("time")}Last 30 minutes</span>`)}${panel("Normalization coverage",`<div class="coverage-ring"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="51" fill="none" stroke="var(--line)" stroke-width="9"/><circle cx="60" cy="60" r="51" fill="none" stroke="var(--accent)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${s.coverage*3.204} 321"/></svg><div class="ring-label"><strong>${s.coverage}%</strong><small>Mapped · partials included</small></div></div><div class="health-details"><div><span>Normalized / partial</span><b>${fmt(s.normalized)} / ${fmt(s.total)}</b></div><div><span>Evidence sealed</span><b>${fmt(s.sealed)} events</b></div><div><span>Parser review queue</span><b>${fmt(s.pending_review)} candidates</b></div><div><span>Processing p95</span><b>${s.p95_ms ?? "—"} ms</b></div></div>`,badge("PIPELINE HEALTH","green"))}</div>`+
   `<div class="overview-bottom">${panel("Latest detection signals",signalFeed(alerts,3),button("View all","nav","arrow","small ghost",'data-page="investigate"'))}${panel("Source distribution",distribution(s.sources.slice().sort((a,b)=>b.events-a.events).slice(0,6).map(x=>({name:x.name,count:x.events}))),badge("Top 6 · all time","outline"))}${panel("Signal severity",distribution(severity)+`<div class="table-footer"><span>Latest ${alerts.length} rule matches · not ML predictions</span></div>`,badge("Observed","outline"))}</div>`+
   panel("Latest telemetry",eventTable(recent.items,{compact:true})+`<div class="table-footer"><span>Latest ${recent.items.length} of ${fmt(recent.total)} events · auto refresh / 4s</span><button class="link-button" data-action="nav" data-page="events">Open event stream →</button></div>`,badge("EVIDENCE LINKED","green"));
}
async function eventsPage() {
  const f = S.filters;
  const params = new URLSearchParams({ ...f, limit: 40 });
  const data = await api("/events?" + params);
  return (
    header(
      "TELEMETRY / EVENT STREAM",
      "Every event, accounted for.",
      "Search the received data and inspect its normalized fields, raw bytes, and lineage.",
      button(S.paused ? "Resume stream" : "Pause stream", "pause-stream", S.paused ? "play" : "time") + button("Import logs", "import", "upload") +
        button("Export", "export", "down", "primary"),
    ) +
    `<section class="panel"><div class="filters"><input class="search-input" id="event-search" aria-label="Search events" placeholder="Search IP, source, message…" value="${esc(f.q)}"><select id="status-filter" aria-label="Processing status">${[["", "All statuses"], ...["normalized", "partial", "unparsed", "drifted", "failed", "queued"].map((x) => [x, x])].map(([v, l]) => `<option value="${v}" ${f.status === v ? "selected" : ""}>${l}</option>`).join("")}</select><select id="mode-filter" aria-label="Traffic mode">${[
      ["", "All traffic"],
      ["live", "Live devices"],
      ["replay", "Synthetic / file replay"],
      ["lab", "Lab devices"],
    ]
      .map(
        ([v, l]) =>
          `<option value="${v}" ${f.mode === v ? "selected" : ""}>${l}</option>`,
      )
      .join(
        "",
      )}</select><select id="source-filter" aria-label="Event source"><option value="">All sources</option>${S.stats.sources.map(src=>`<option value="${src.id}" ${f.source===src.id?"selected":""}>${esc(src.name)}</option>`).join("")}</select>${button("Refresh", "refresh", "refresh", "small")}</div>${eventTable(data.items)}<div class="table-footer"><span>${data.total ? f.offset + 1 : 0}–${Math.min(f.offset + 40, data.total)} of ${fmt(data.total)} events</span><div class="button-group">${button("Previous", "previous", "", "small", f.offset === 0 ? "disabled" : "")}${button("Next", "next", "", "small", f.offset + 40 >= data.total ? "disabled" : "")}</div></div></section>`
  );
}
async function sourcesPage() {
  const sources = S.stats.sources;
  return (
    header(
      "CONNECT / SOURCES",
      "One perimeter. Many sources.",
      "Standard transports bring device logs into a single processing pipeline.",
      button("Import a file", "import", "upload") +
        button("Add source", "add-source", "plus", "primary"),
    ) +
    notice(
      "<strong>Real connection, explicit compatibility.</strong> Devices must export logs to this collector. Supported formats are parsed; unfamiliar formats are preserved for onboarding.",
    ) +
    notice(`Controlled socket lab: TCP / UDP <code>127.0.0.1:5515</code>. Records received on this dedicated listener are labeled <strong>lab</strong>. Use <code>lab/socket_range.py</code> for a safe, synthetic network demonstration.`) +
    panel(
      "Collector endpoints",
      `<div class="connection-card"><h3>Point your device’s remote logging configuration here</h3><p>For another device to reach this machine, bind the collector to its network interface and allow the selected port.</p><div class="transport-list">${Object.entries(
        S.system.listeners,
      )
        .map(
          ([kind, v]) =>
            `<div class="transport-pill">${badge(kind.toUpperCase(), v.listening ? "green" : "outline")}<span class="mono">${v.listening ? esc(v.host) + ":" + v.port : "Not enabled"}</span></div>`,
        )
        .join("")}</div></div>`,
      button("Setup guide", "connect-guide", "external", "small"),
    ) +
    `<div class="source-cards section-gap">${sources.map((src) => `<section class="panel device-card"><div class="device-card-top"><span class="source-icon">${icon(src.kind === "ids" ? "shield" : src.kind === "router" ? "network" : "sources")}</span>${badge(src.mode)}</div><h3>${esc(src.name)}</h3><p>${esc(src.kind)} · ${esc(src.peer || "Replay / HTTP input")}</p><div class="device-card-bottom"><span><strong>${fmt(src.events)}</strong> events stored</span><span>${src.last_seen ? clock(src.last_seen) : "Awaiting logs"}</span></div><div class="mt">${button("Inspect events", "source-events", "", "small ghost", `data-id="${src.id}"`)}${button("Edit", "edit-source", "", "small ghost", `data-id="${src.id}"`)}</div></section>`).join("") || empty("No sources yet", "Register a device by name and sender IP, or import a log file.")}</div>`
  );
}
async function labPage() {
  const candidates = await api("/candidates");
  if (!S.candidateId && candidates.length)
    S.candidateId =
      candidates.find((c) => c.status !== "approved")?.id || candidates[0].id;
  let c = S.candidateId ? await api("/candidates/" + S.candidateId) : null;
  S.candidate = c;
  const approved = c?.status === "approved";
  let detail = empty(
    "Ready for unfamiliar formats",
    "When a new format arrives, LOGFLUX preserves it and creates a review candidate. Run the replay to try onboarding.",
    button("Run replay", "demo", "play", "primary"),
  );
  if (c) {
    let body = "";
    if (S.labTab === "mapping") {
      body = `<table class="mapping-table"><thead><tr><th>Common field</th><th></th><th>Source field</th></tr></thead><tbody>${S.system.schema.fields.map((target) => `<tr><td class="mono">${target}</td><td>→</td><td><select class="mapping-select" data-field="${target}" aria-label="Map ${target}" ${approved ? "disabled" : ""}><option value="">Leave unmapped</option>${c.keys.map((key) => `<option value="${esc(key)}" ${c.mapping[target] === key ? "selected" : ""}>${esc(key)}${c.samples[0]?.attributes[key] !== undefined ? " · " + esc(short(c.samples[0].attributes[key],32)) : ""}</option>`).join("")}</select></td></tr>`).join("")}</tbody></table>`;
    } else if (S.labTab === "samples") {
      body = `<div class="panel-body"><h3>Original event</h3><pre class="code dark-code">${esc(c.samples[0]?.raw_text || "No sample")}</pre><h3 class="mt">Extracted attributes</h3><pre class="code">${esc(JSON.stringify(c.samples[0]?.attributes || {}, null, 2))}</pre></div>`;
    } else {
      body = `<div class="panel-body"><h3>Discovered structure</h3><pre class="code">${esc(c.template)}</pre><div class="mt">${notice("Drain3 finds repeated structure. A matching template does not establish field meaning. Source and destination roles still require review.")}</div><h3>Fingerprint</h3><p class="mono break">${esc(c.fingerprint)}</p><h3 class="mt">Proposal origin</h3><p class="muted tiny">${esc(c.proposal_source)}</p></div>`;
    }
    const r = c.report;
    detail = `<section class="panel"><div class="panel-head"><div><h2>${esc(c.source)}</h2><p>${esc(c.format)} · ${c.samples.length} recent sample${c.samples.length === 1 ? "" : "s"}</p></div>${badge(c.status)}</div><div class="tabs">${[
      ["mapping", "Field mapping"],
      ["samples", "Raw sample"],
      ["structure", "Discovery"],
    ]
      .map(
        ([id, label]) =>
          `<button class="tab ${S.labTab === id ? "active" : ""}" data-action="lab-tab" data-tab="${id}">${label}</button>`,
      )
      .join("")}</div>${body}${!approved ? `<details class="semantic-editor"><summary>Semantic assertions · verify source / destination meaning</summary><p class="field-help mt">Enter expected normalized values for a sample. This catches valid-looking but swapped fields.</p><p class="mono tiny mt">Sample ID: ${esc(c.samples[0]?.id || "")}</p><textarea id="semantic-expectations" aria-label="Semantic assertions" placeholder='[{"event_id":"sample ID","fields":{"source_ip":"192.0.2.1"}}]'>${esc(S.expectations[c.id] || "[]")}</textarea></details>` : ""}${
      r
        ? `<div class="validation-results ${r.passed ? "" : "failed"}"><div class="flex between"><strong class="tiny">${r.passed ? "Validation passed · review semantics before approval" : "Validation needs attention"}</strong>${badge(r.passed ? "passed" : "failed")}</div><div class="stats-row"><div><strong>${r.samples}</strong><span>REPLAYED SAMPLES</span></div><div><strong>${r.mutations}</strong><span>MUTATED INPUTS</span></div><div><strong>${r.semantic_assertions}</strong><span>SEMANTIC ASSERTIONS</span></div></div><p class="field-help">No host imports · 64 KiB WASM memory · 10,000 fuel. ${r.confidence_note || ""}</p><div class="confidence-line"><span class="tiny">Review score ${r.confidence ?? 0}/100</span><div class="progress"><span style="width:${r.confidence ?? 0}%"></span></div></div>${
            !r.passed
              ? `<pre class="code mt">${esc(
                  JSON.stringify(
                    r.results
                      ?.filter((x) => !x.passed)
                      .map((x) => x.issues)
                      .slice(0, 3),
                    null,
                    2,
                  ),
                )}</pre>`
              : ""
          }</div>`
        : ""
    }<div class="review-actions">${approved ? button("New parser version", "revise", "plus", "small") + button("Replay retained events", "replay", "refresh", "primary") : `<div class="button-group">${button("Local AI proposal", "llm", "bolt", "small")}${button("Save & validate", "validate", "check", "small")}</div>${button("Review & approve", "approve", "shield", "primary", r?.passed ? "" : "disabled")}`}</div></section>`;
  }
  return (
    header(
      "ONBOARD / PARSER LAB",
      "New formats, under control.",
      "Discover the structure. Verify the meaning. Approve a signed parser.",
      button("Trigger sample drift", "drift", "activity") +
        button("Plugin registry", "plugins", "lock"),
    ) +
    notice(
      "Unknown and drifted events remain in the vault. Approval deploys a versioned parser; replay creates new normalized revisions without changing the originals.",
    ) +
    `<div class="lab-layout">${panel("Review queue", `<div class="candidate-list">${candidates.map((item) => `<button class="candidate ${item.id === S.candidateId ? "active" : ""}" data-action="candidate" data-id="${item.id}"><div class="flex">${badge(item.status)}<span class="tiny muted">${fmt(item.affected)} events</span></div><strong>${esc(item.source)}</strong><p>${esc(item.format)} · ${esc(short(item.fingerprint, 12))}</p></button>`).join("") || '<div class="empty">No formats awaiting review.</div>'}</div>`, badge(candidates.filter((x) => x.status !== "approved").length + " open", "amber"))}${detail}</div>`
  );
}
async function evidencePage() {
  const [batches, recent, evidenceCases] = await Promise.all([
    api("/integrity/batches"),
    api("/events?limit=6"),
    api("/cases"),
  ]);
  const anchored = batches.filter((b) => b.anchoring.anchored).length;
  return (
    header(
      "VERIFY / EVIDENCE VAULT",
      "The original is always there.",
      "Trace stored bytes to a Merkle root and a signed ledger checkpoint.",
      button("Seal pending events", "seal", "shield", "primary"),
    ) +
    `<div class="metrics">${metric("Original evidence", bytes(S.stats.raw_bytes), "", `${fmt(S.stats.total)} events retained`, "database")}${metric("Events sealed", fmt(S.stats.sealed), "", `${fmt(S.stats.total - S.stats.sealed)} awaiting a batch`, "shield")}${metric("Recent checkpoints", fmt(anchored), "", `${batches.length} batches shown · quorum signed`, "lock")}${metric("Witness quorum", "2 / 3", "", `Local permissioned validators`, "network")}</div>` +
    notice(
      S.system.ledger_mode,
      "amber",
    ) +
    panel(
      "Signed checkpoints",
      batches.length
        ? `<div class="table-scroll"><table><thead><tr><th>Batch</th><th>Merkle root</th><th>Events</th><th>Witnesses</th><th>Created</th><th></th></tr></thead><tbody>${batches
            .slice(0, 8)
            .map(
              (b) =>
                `<tr><td class="mono">#${String(b.seq).padStart(4, "0")}</td><td><div class="batch-root mono">${esc(b.root)}</div></td><td>${b.checkpoint.event_count}</td><td>${badge(b.anchoring.anchored ? "Quorum signed" : "Pending quorum", b.anchoring.anchored ? "green" : "amber")}</td><td>${clock(b.created_at)}</td><td>${button("Inspect", "batch", "", "small ghost", `data-id="${b.id}"`)}</td></tr>`,
            )
            .join("")}</tbody></table></div>`
        : empty(
            "No sealed batches",
            "Events are sealed automatically. You can also seal pending events manually.",
          ),
      badge("Ed25519", "outline"),
    ) +
    `<div class="section-gap">${panel("Inspect original evidence", `<div class="table-scroll"><table><thead><tr><th>Evidence ID / received</th><th>Source / event</th><th>SHA-256</th><th>Processing</th><th>Related case</th><th></th></tr></thead><tbody>${recent.items.map(e=>`<tr><td><span class="evidence-id" title="${esc(e.id)}">${esc(short(e.id,16))}</span><span class="source-sub">${date(e.received_at)}</span></td><td>${esc(e.source)}<span class="source-sub">${esc(e.normalized?.action||e.status)} · ${esc(e.mode)}</span></td><td class="hash-cell mono" title="${esc(e.raw_hash)}">${esc(e.raw_hash)}</td><td>${badge(e.status)}</td><td>${evidenceCases.filter(c=>c.event_ids.includes(e.id)).map(c=>`<button class="link-button" data-action="case" data-id="${esc(c.id)}">${esc(c.title)}</button>`).join("<br>")||'<span class="muted">Unassigned</span>'}</td><td>${button("Verify / inspect","event","shield","small",`data-id="${esc(e.id)}"`)}</td></tr>`).join("")}</tbody></table></div>`, '<span class="tiny muted">Open an event → Verify evidence</span>')}</div>`
  );
}
function graphSvg(data) {
  const counts=new Map();
  for(const e of data.edges){const key=e.source+"|"+e.target;counts.set(key,(counts.get(key)||0)+1);}
  const all=[...data.nodes].sort((a,b)=>(b.id===S.ip)-(a.id===S.ip)||b.events-a.events).slice(0,18);
  if(!all.length)return empty("No mapped relationships","Try another time range or source. Logs need source and destination IPs to appear here.");
  const pos={}; const width=760,height=410;
  all.forEach((n,i)=>{const angle=(i-1)/Math.max(1,all.length-1)*Math.PI*2;pos[n.id]=i===0?[380,200]:[380+Math.cos(angle)*270,200+Math.sin(angle)*145];});
  return `<div class="graph"><svg viewBox="0 0 ${width} ${height}" style="width:${S.graphZoom*100}%" role="img" aria-label="Network addresses and observed connections"><defs><radialGradient id="graph-halo"><stop stop-color="#ad77f5" stop-opacity=".12"/><stop offset="1" stop-color="#ad77f5" stop-opacity="0"/></radialGradient></defs><circle cx="380" cy="200" r="180" fill="url(#graph-halo)"/><circle cx="380" cy="200" r="118" fill="none" stroke="var(--line)" stroke-dasharray="3 8"/>${[...counts.entries()].filter(([key])=>key.split("|").every(k=>pos[k])).map(([key,n])=>{const[a,b]=key.split("|");return `<path d="M${pos[a]} Q380 200 ${pos[b]}" fill="none" stroke="${a===S.ip||b===S.ip?'#bd92ee':'#736382'}" opacity=".65" stroke-width="${Math.min(3,1+n/30)}"><title>${esc(a)} → ${esc(b)} · ${n} events</title></path>`;}).join("")}${all.map((n,i)=>`<g class="node" data-action="graph-ip" data-ip="${esc(n.id)}" tabindex="0" role="button" aria-label="Investigate ${esc(n.id)}"><circle cx="${pos[n.id][0]}" cy="${pos[n.id][1]}" r="${i===0?27:18}" fill="${n.id===S.ip?'#6b4991':'#30283d'}" stroke="${i===0?'#c49bea':'#9a83b1'}" stroke-width="1.5"/><path d="M${pos[n.id][0]-7} ${pos[n.id][1]-5}h14v10h-14z M${pos[n.id][0]-3} ${pos[n.id][1]+8}h6" stroke="#d2b7ec" fill="none" stroke-width="1.2"/><text x="${pos[n.id][0]}" y="${pos[n.id][1]+(i===0?44:34)}" text-anchor="middle">${esc(n.id)}</text><title>${n.events} event endpoints · select to focus</title></g>`).join("")}</svg></div>`;
}
function investigationRisk(g) {
  const denies=g.timeline.filter(t=>t.action==="deny"||t.action==="alert").length;
  const sourceTimes=g.timeline.filter(t=>t.time_basis==="source").length;
  const dests=g.behavior.unique_destinations||0;
  const parts=[
    {label:"Taint",value:0,max:100,note:"No wallet or taint dataset connected.",color:"#a78bfa"},
    {label:"Behavior",value:Math.min(denies*8,100),max:100,note:`${denies} denied/alerted events in scope.`,color:"#fb7185"},
    {label:"Timing",value:Math.min(sourceTimes*5,100),max:100,note:`${sourceTimes} source-timestamped events.`,color:"#fbbf24"},
    {label:"Network",value:Math.min(dests*6,100),max:100,note:`${dests} observed destinations.`,color:"#22d3ee"},
  ];
  const totalScore=Math.round(parts.reduce((s,p)=>s+p.value,0)/4);
  const r=54; const cx=70; const cy=62; const circ=2*Math.PI*r;
  const gaugeColor="#a78bfa";
  const gaugeSvg=`<div class="risk-gauge"><div class="risk-gauge-wrap" style="width:140px;height:78px">
    <svg width="140" height="78" viewBox="0 0 140 78" overflow="visible">
      <path d="M ${cx-r},${cy} A ${r},${r} 0 0,1 ${cx+r},${cy}" fill="none" stroke="#1e1b38" stroke-width="9" stroke-linecap="round"/>
      <path d="M ${cx-r},${cy} A ${r},${r} 0 0,1 ${cx+r},${cy}" fill="none" stroke="${gaugeColor}" stroke-width="9" stroke-linecap="round"
        stroke-dasharray="${(totalScore/100)*circ/2} ${circ}" opacity=".85"
        style="filter:drop-shadow(0 0 6px ${gaugeColor}60);transition:stroke-dasharray .6s ease"/>
    </svg>
    <div class="risk-gauge-label">
      <strong style="color:${gaugeColor}">${totalScore}</strong>
      <small>/ 100</small>
    </div>
  </div></div>`;
  return panel("Fracture Index · Activity heuristic",
    `${gaugeSvg}<p class="graph-note">Formula: [min(8 × deny/alert events, 100) + min(5 × source timestamps, 100) + min(6 × destinations, 100)] / 4. Counts rise with traffic volume; this is not validated detection accuracy.</p><div class="risk-breakdown">${parts.map(p=>`<div class="risk-part"><div><span>${p.label}</span><strong>${p.label === "Taint" ? "N/A" : p.value}</strong></div><div class="risk-bar"><span style="width:${p.value}%;background:linear-gradient(90deg,${p.color}80,${p.color})"></span></div><p>${p.note}</p></div>`).join("")}</div><div class="table-footer"><span>Uncalibrated activity score · not threat probability. Taint is missing; formula maximum is 75.</span></div>`,
    badge("UNCALIBRATED","amber"));
}
async function investigatePage() {
  const [g, alerts, cases] = await Promise.all([
    api("/graph?" + new URLSearchParams({ip:S.ip,source:S.graphSource,minutes:S.graphMinutes})),
    api("/alerts"),
    api("/cases"),
  ]);
  S.graph = g;
  const ids=new Set(g.timeline.map(t=>t.id));
  const scopedAlerts=alerts.filter(a=>ids.has(a.event_id));
  return (
    header(
      "CORRELATE / INVESTIGATION",
      "Follow the evidence.",
      "Explore observed relationships and build a case from the underlying events.",
      button(
        "Create case",
        "create-case",
        "plus",
        "primary",
        g.timeline.length ? "" : "disabled",
      ),
    ) +
    `<div class="filters panel mb"><input id="graph-search" class="search-input" placeholder="Focus on an IP address, or leave blank for all" aria-label="Investigation IP" value="${esc(S.ip)}"><select id="graph-source" aria-label="Investigation source"><option value="">All sources</option>${S.stats.sources.map(src=>`<option value="${src.id}" ${S.graphSource===src.id?"selected":""}>${esc(src.name)}</option>`).join("")}</select><select id="graph-time" aria-label="Investigation time range">${[["0","All receipt times"],["30","Last 30 minutes"],["1440","Last 24 hours"],["10080","Last 7 days"]].map(([v,n])=>`<option value="${v}" ${S.graphMinutes===v?"selected":""}>${n}</option>`).join("")}</select>${button("Investigate", "investigate-search", "search")}${S.ip ? button("Clear", "clear-ip", "", "small") : ""}<span class="tiny muted">${g.behavior.observing_sources} observing sources · ${g.behavior.unique_destinations} destinations</span></div>` +
    `<div class="investigation-layout">${panel("Observed relationships", graphSvg(g)+`<div class="table-footer"><span>Select an IP to focus · showing ${Math.min(g.nodes.length,18)} of ${g.nodes.length} addresses</span><div class="graph-controls">${button("−","graph-zoom-out","","small",'aria-label="Zoom out"')}${button(`${Math.round(S.graphZoom*100)}%`,"graph-zoom-reset","","small",'aria-label="Reset graph zoom"')}${button("+","graph-zoom-in","","small",'aria-label="Zoom in"')}</div></div><div class="graph-note">${esc(g.scope)} ${g.corroborated_pairs.length} pairs observed across multiple sources. Nodes represent IPs; hosts, users and wallets are not inferred.</div>`,badge(`${g.edges.length} connection events`,"outline"))}${investigationRisk(g)}</div>`+
    panel("Detection signals",signalFeed(scopedAlerts,8),badge(`${scopedAlerts.length} in scope · latest 100 searched`,"amber"))+
    notice(
      "The timeline shows observations, not a confirmed attack narrative. Shared addresses and timing are corroborating signals; NAT, clock differences, and replay traffic require analyst judgment.",
    ) +
    `<div class="two-column">${panel(
      "Evidence timeline",
      `<div class="timeline">${
        g.timeline
          .slice(-20)
          .reverse()
          .map(
            (t) =>
              `<div class="timeline-item"><span class="timeline-dot ${t.action}"></span><div class="timeline-content"><div class="meta">${clock(t.time)} · ${t.time_basis === "source" ? "source time" : "receipt time"} ${badge(t.mode)}</div><h3><button class="row-button" data-action="event" data-id="${t.id}">${esc(t.source_ip)} → ${esc(t.destination_ip)}${t.port ? ":" + t.port : ""}</button></h3><p>${esc(t.source)} · ${esc(t.action)}${t.message ? " · " + esc(short(t.message, 70)) : ""}</p></div></div>`,
          )
          .join("") || '<p class="tiny muted">No events match this address.</p>'
      }</div>`,
      '<span class="tiny muted">Latest 20 observations</span>',
    )}${panel(
      "Saved cases",
      `<div class="panel-body">${cases.map((c) => `<div class="source-row"><span class="source-icon">${icon("file")}</span><div><button class="row-button" data-action="case" data-id="${c.id}">${esc(c.title)}</button><small>${c.event_ids.length} linked events · ${date(c.created_at)}</small></div></div>`).join("") || '<p class="tiny muted">Create a case to retain the selected timeline and your investigation notes.</p>'}<div class="mt">${
        g.corroborated_pairs.length
          ? `<h3>Cross-source corroboration</h3>${g.corroborated_pairs
              .slice(0, 5)
              .map(
                (p) =>
                  `<div class="source-row"><div><strong class="mono">${esc(p.source)} → ${esc(p.destination)}</strong><small>${p.devices.map(esc).join(" · ")}</small></div></div>`,
              )
              .join("")}`
          : ""
      }</div></div>`,
    )}</div>`
  );
}
async function systemPage() {
  const [llm, sinks, outbox] = await Promise.all([
    api("/llm/status"),
    api("/sinks"),
    api("/outbox"),
  ]);
  return (
    header(
      "OPERATE / SYSTEM & OUTPUTS",
      "Local by design. Observable throughout.",
      "Inspect runtime capabilities, delivery status, and offline processing dependencies.",
      button("Export events", "export", "down") +
        button("Add output", "add-sink", "plus", "primary"),
    ) +
    `<div class="runtime-grid">${[
      [
        "Durable storage",
        "SQLite WAL",
        "Raw commits precede parsing. Single-node demonstration storage.",
        "database",
      ],
      [
        "Parser execution",
        "WASM sandbox",
        "No host imports, 64 KiB memory, and an execution fuel limit.",
        "lock",
      ],
      [
        "Semantic assistant",
        llm.available ? "Local model ready" : "Model not loaded",
        `${llm.model} · ${llm.available ? "Available on the local endpoint." : "Install or import the model to enable AI proposals."}`,
        "bolt",
      ],
    ]
      .map(
        ([title, value, text, ic]) =>
          `<div class="panel runtime-card"><div class="flex between">${icon(ic)}${badge(title === "Semantic assistant" ? (llm.available ? "available" : "setup required") : "local", title === "Semantic assistant" && !llm.available ? "amber" : "green")}</div><h3>${title}</h3><div class="value">${value}</div><p>${esc(text)}</p></div>`,
      )
      .join("")}</div>` +
    `<div class="two-column">${panel(
      "Receiver health",
      `<div class="panel-body">${Object.entries(S.system.listeners)
        .map(
          ([name, v]) =>
            `<div class="witness"><div><strong>${name.toUpperCase()} Syslog</strong><small>${v.listening ? esc(v.host) + ":" + v.port : esc(v.reason || v.error || "Disabled")}</small></div>${badge(v.listening ? "Listening" : "Not enabled", v.listening ? "green" : "outline")}</div>`,
        )
        .join(
          "",
        )}<div class="mt">${notice(`${S.stats.metrics.receiver_errors} receiver errors · ${S.stats.metrics.rejected} rejected oversized/empty events. ${esc(S.stats.metrics.last_receiver_error || "No receiver error recorded.")}`)}</div></div>`,
    )}${panel("Permissioned witnesses", `<div class="panel-body">${S.system.witnesses.map((w) => `<div class="witness"><div><strong>${esc(w.name)}</strong><small>${esc(w.key_id)}</small></div><div class="flex">${badge(S.system.remote_witnesses ? "configured" : (w.enabled ? "available" : "offline"), "outline")}${S.system.remote_witnesses ? "" : button(w.enabled ? "Pause" : "Resume", "witness", "", "small", `data-name="${w.name}" data-enabled="${!w.enabled}"`)}</div></div>`).join("")}<p class="field-help mt">${esc(S.system.ledger_mode)}</p></div>`)}</div>` +
    `<div class="section-gap">${panel("SIEM & data lake outputs", sinks.length ? `<div class="table-scroll"><table><thead><tr><th>Output</th><th>Endpoint</th><th>Delivered</th><th>Pending</th><th>Status</th><th></th></tr></thead><tbody>${sinks.map((s) => `<tr><td>${esc(s.name)}<span class="source-sub">${esc(s.kind || "http")}</span></td><td class="mono">${esc(short(s.url, 45))}</td><td>${s.delivered}</td><td>${s.pending}</td><td>${badge(s.enabled ? "enabled" : "paused", s.enabled ? "green" : "outline")}</td><td>${button(s.enabled ? "Pause" : "Resume", "sink-toggle", "", "small", `data-id="${s.id}" data-enabled="${!s.enabled}"`)}</td></tr>`).join("")}</tbody></table></div>` : empty("No output endpoint configured", "Add a local HTTP collector for ongoing delivery, or export JSONL, ECS-mapped JSONL, and CSV files.", button("Add output", "add-sink", "plus", "small")), '<span class="tiny muted">Durable outbox · retries · idempotency keys</span>')}</div>` +
    (outbox.some((o) => o.error)
      ? `<div class="section-gap">${notice("<strong>Delivery requires attention.</strong> " + esc(outbox.find((o) => o.error).error), "amber")}</div>`
      : "") +
    `<div class="two-column section-gap">${panel("Schema & provenance", `<div class="panel-body"><div class="key-value"><div>Canonical schema</div><div>${esc(S.system.schema.name)}</div><div>Version</div><div>${S.system.schema.version}</div><div>Schema hash</div><div class="mono">${esc(short(S.system.schema_hash, 24))}</div><div>Source data</div><div>Raw bytes + extracted attributes + unmapped fields</div></div><p class="field-help mt">LOGFLUX uses OCSF concepts and an ECS export adapter. Full OCSF schema conformance is not claimed.</p></div>`)}${panel("Air-gapped operation", `<div class="panel-body">${["All interface assets served locally", "No cloud API required for collection or normalization", "Signed parser bundles support offline transfer", "Local model required for semantic AI proposals", "Python wheels / container images must be staged before isolation"].map((x) => `<div class="feature-row">${icon("check")}${x}</div>`).join("")}<div class="mt">${button("Offline setup guide", "offline-guide", "file", "small")}</div></div>`)}</div>`
  );
}
async function render() {
  const page = S.page;
  const renderers = {
    overview,
    events: eventsPage,
    sources: sourcesPage,
    lab: labPage,
    evidence: evidencePage,
    investigate: investigatePage,
    system: systemPage,
  };
  const html = await renderers[page]();
  if (page === S.page) $("#main").innerHTML = html;
}
function modal(title, subtitle, body, footer = "", wide = false) {
  S.modal = true;
  $("#modal-root").innerHTML =
    `<div class="modal-backdrop"><section class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div class="modal-head"><div><h2 id="modal-title">${title}</h2><p>${subtitle}</p></div><button class="modal-close" data-action="close" aria-label="Close dialog">×</button></div><div class="modal-body">${body}</div>${footer ? `<div class="modal-footer">${footer}</div>` : ""}</section></div>`;
  setTimeout(
    () =>
      $("#modal-root input, #modal-root select, #modal-root button")?.focus(),
    20,
  );
}
function closeModal() {
  S.modal = null;
  S.event = null;
  $("#modal-root").innerHTML = "";
}
function sourceModal(source = null) {
  S.editSourceId = source?.id || null;
  modal(
    "Connect a source",
    "Register its identity before receiving logs.",
    `<div class="form-grid"><div class="field"><label for="source-name">Device name</label><input id="source-name" placeholder="e.g. Branch firewall" maxlength="100"></div><div class="field"><label for="source-kind">Device category</label><select id="source-kind">${["firewall", "router", "ids", "switch", "vpn", "server", "application", "network", "gateway", "lab", "unclassified"].map((k) => `<option>${k}</option>`).join("")}</select></div><div class="field"><label for="source-peer">Sender IP (for Syslog)</label><input id="source-peer" placeholder="e.g. 192.168.1.1"><p class="field-help">Match the actual sender address visible to this collector.</p></div><div class="field"><label for="source-mode">Traffic origin</label><select id="source-mode"><option value="live">Live device</option><option value="lab">Isolated lab device</option><option value="replay">File / synthetic replay</option></select></div></div>${notice("Registration does not configure the device. Enable remote Syslog on the device and point it at the collector’s reachable IP and port.")}`,
    button("Cancel", "close") +
      button(source ? "Save source" : "Register source", "save-source", "plus", "primary"),
  );
  if (source) { $("#source-name").value = source.name; $("#source-peer").value = source.peer || ""; $("#source-kind").value = source.kind; $("#source-mode").value = source.mode; }
}
function connectGuide() {
  modal(
    "Connect a real device",
    "The receiver accepts actual TCP, UDP, and configured TLS traffic.",
    `<div class="guide-step"><span>1</span><div><h3>Start the collector on a reachable interface</h3><p>On the deployment machine, use <code>LOGFLUX_SYSLOG_HOST=0.0.0.0</code> to receive IPv4 traffic from your lab network. TCP/UDP port defaults to <code>5514</code>. Allow only the intended senders through the host firewall.</p></div></div><div class="guide-step"><span>2</span><div><h3>Enable device logging</h3><p>Set the remote Syslog destination to your collector’s LAN IP, not <code>127.0.0.1</code>. Choose TCP where supported. Some devices use fixed UDP port 514; map that port to 5514 on your container host.</p></div></div><div class="guide-step"><span>3</span><div><h3>Send a genuine event</h3><p>Generate a permitted connection or a blocked connection in your isolated lab. Open Live events and select “Live devices.” Source IP association identifies a sender but does not authenticate it; configure mutual TLS when supported.</p></div></div><div class="guide-step"><span>4</span><div><h3>Check normalization</h3><p>Built-in adapters cover tested FortiGate key-value, Cisco ASA deny messages, pfSense filterlog, Suricata EVE, CEF, and LEEF layouts. Different firmware/event layouts may need a new mapping. Unknown events stay in the vault.</p></div></div>${notice("UDP is best effort. No receiver can recover a datagram that never arrived. TCP source buffering and application acknowledgments depend on the device.", "amber")}`,
    button("Add source", "add-source", "plus", "primary"),
  );
}
function importModal() {
  modal(
    "Import log evidence",
    "Choose line-delimited logs or a single complete event.",
    `<div class="field"><label for="import-source">Source identity</label><select id="import-source">${S.stats.sources.map((s) => `<option value="${s.id}" ${s.mode === "replay" ? "selected" : ""}>${esc(s.name)} (${s.mode})</option>`).join("")}</select><p class="field-help">Use a replay source for sample files. ${button("Register a new source", "add-source", "", "small ghost")}</p></div><div class="field"><label for="import-framing">Event boundaries</label><select id="import-framing"><option value="lines">One event per line (Syslog / NDJSON)</option><option value="single">Entire file is one event (XML / JSON / CSV header + row)</option></select></div><div class="field"><label for="log-file">Log file · maximum 8 MiB</label><input class="file-input" id="log-file" type="file"></div><div class="field"><label for="raw-input">Or paste one event</label><textarea id="raw-input" rows="4" placeholder='srcip=10.0.0.1 dstip=192.0.2.10 action=deny'></textarea></div>`,
    button("Cancel", "close") +
      button("Preserve & process", "do-import", "upload", "primary"),
  );
}
function exportModal() {
  modal(
    "Export processed events",
    "Latest 1,000 matching events. Original evidence remains in the vault.",
    `<div class="field"><label for="export-format">Representation</label><select id="export-format"><option value="jsonl">Complete LOGFLUX events · JSONL, including raw Base64</option><option value="ecs">ECS-mapped events · JSONL</option><option value="csv">Common fields · CSV</option></select></div>${notice("JSONL retains the full event envelope. CSV is an analytics projection and is not a replacement for the raw evidence archive. Current event search and status filters apply.")}`,
    button("Cancel", "close") +
      button("Download export", "do-export", "down", "primary"),
  );
}
async function showEvent(id, tab = "event") {
  S.eventId = id;
  S.eventTab = tab;
  const e = await api("/events/" + id);
  S.event = e;
  let body = "";
  if (tab === "event") {
    const n = e.normalized;
    body = `<div class="event-meta-grid"><div><label>Source</label><strong>${esc(e.source)}</strong></div><div><label>Receipt time</label><strong>${date(e.received_at)}</strong></div><div><label>Parser</label><strong>${esc(e.parser || "Awaiting approved parser")}</strong></div></div><div class="detail-split"><div><h3>Original received event <span>${bytes(e.raw_size)}</span></h3><pre class="code dark-code">${esc(e.raw_text)}</pre><p class="field-help">Text preview uses replacement characters for invalid UTF-8. Download raw bytes for exact evidence.</p><h3 class="mt">Raw SHA-256</h3><p class="mono break tiny muted">${e.raw_hash}</p></div><div><h3>Common fields</h3>${n ? `<div class="key-value">${["source_ip", "destination_ip", "source_port", "destination_port", "protocol", "action", "severity", "time", "time_basis"].map((k) => `<div>${k.replaceAll("_", " ")}</div><div class="mono">${esc(n[k] ?? "—")}</div>`).join("")}</div>` : notice(esc(e.error || "This format has not been approved. Its original bytes and extracted attributes are preserved."), "amber")}${n?.quality.issues.length ? `<div class="mt">${notice(n.quality.issues.map((i) => esc(i.field) + ": " + esc(i.reason)).join("<br>"), "amber")}</div>` : ""}</div></div>`;
  } else if (tab === "json") {
    body = `<pre class="code">${esc(JSON.stringify({ normalized: e.normalized, source_attributes: e.attributes, raw_reference: "/api/events/" + e.id + "/raw" }, null, 2))}</pre>`;
  } else if (tab === "proof") {
    const p = await api("/events/" + id + "/proof");
    body = p.sealed
      ? `<div class="check-grid">${[
          ["Raw bytes", p.raw_hash_valid],
          ["Manifest", p.manifest_valid],
          ["Merkle proof", p.merkle_valid],
          ["Ledger quorum", p.ledger_valid],
        ]
          .map(
            ([label, ok]) =>
              `<div class="check-item ${ok ? "" : "failed"}">${icon(ok ? "check" : "x")}${label}<br><strong>${ok ? "Verified" : "Failed"}</strong></div>`,
          )
          .join(
            "",
          )}</div><div class="proof-tree"><strong>Event leaf</strong> <span class="mono">${esc(short(p.leaf, 35))}</span><br>↓ ${p.proof.length} sibling hash${p.proof.length === 1 ? "" : "es"}<br><strong>Batch root</strong> <span class="mono">${esc(short(p.root, 35))}</span><br>↓ checkpoint #${p.checkpoint.sequence}<br><strong>${p.anchor.votes.length} witness signatures</strong> · ${p.anchor.quorum} required</div>${notice(esc(p.trust_note))}<pre class="code">${esc(JSON.stringify(p, null, 2))}</pre>`
      : notice(
          "This event is preserved but has not yet entered a sealed batch. Seal pending events, then verify it.",
          "amber",
        );
  } else {
    const p = await api("/events/" + id + "/provenance");
    body = `<h3>Original evidence</h3><div class="revision"><strong class="mono">${esc(p.raw.id)}</strong><p>${esc(p.source)} · ${date(p.raw.received_at)}</p><p class="mono break">${esc(p.raw.hash)}</p></div><h3 class="mt">Processing revisions</h3>${p.revisions.map((r) => `<div class="revision"><div class="flex between"><strong>Revision ${r.version} · ${esc(r.parser || "No parser")}</strong>${badge(r.status)}</div><p>${date(r.created_at)}</p></div>`).join("")}<h3 class="mt">Detection → case links</h3>${p.alerts.map((a) => `<div class="revision">${esc(a.title)} ${badge(a.severity)}</div>`).join("") || '<p class="tiny muted">No detection linked to this event.</p>'}${p.cases.map((c) => `<div class="revision">Case: ${esc(c.title)}</div>`).join("")}`;
  }
  modal(
    "Event inspection",
    id,
    `<div class="event-detail-top"><div class="flex">${badge(e.status)}${badge(e.mode)}${badge(e.format, "outline")}</div><span class="mono">Revision ${e.revision} · ${e.duration_ms?.toFixed(2)} ms processing</span></div><div class="tabs">${[
      ["event", "Original & normalized"],
      ["json", "Full representation"],
      ["proof", "Verify evidence"],
      ["lineage", "Provenance"],
    ]
      .map(
        ([t, l]) =>
          `<button class="tab ${tab === t ? "active" : ""}" data-action="event-tab" data-tab="${t}">${l}</button>`,
      )
      .join("")}</div>${body}`,
    button("Download raw", "download-raw", "down") +
      (tab === "proof"
        ? button("Download proof", "download-proof", "shield")
        : "") +
      button("Close", "close"),
    true,
  );
}
async function pluginsModal() {
  const plugins = await api("/plugins");
  modal(
    "Signed plugin registry",
    "Only trusted signatures and tested bundles can be imported.",
    `${plugins.length ? `<div class="table-scroll"><table><thead><tr><th>Parser</th><th>Version</th><th>State</th><th>Reviewer</th><th></th></tr></thead><tbody>${plugins.map((p) => `<tr><td class="mono">${esc(p.id)}</td><td>${p.version}</td><td>${badge(p.active ? "active" : "inactive", p.active ? "green" : "outline")}</td><td>${esc(p.reviewer)}</td><td><div class="button-group">${button("Export", "plugin-export", "down", "small", `data-id="${p.id}"`)}${!p.active ? button("Activate", "plugin-activate", "", "small", `data-id="${p.id}"`) : ""}</div></td></tr>`).join("")}</tbody></table></div>` : empty("No approved plugins", "Approve a candidate in Parser lab to create a signed WASM mapping bundle.")}<div class="field mt"><label for="plugin-file">Import a signed parser bundle</label><input id="plugin-file" type="file" accept=".json"><p class="field-help">The signer must be pinned in <code>data/trusted-plugin-keys.json</code>. Imported plugins remain inactive until activated.</p></div>`,
    button("Import bundle", "plugin-import", "upload") +
      button("Close", "close"),
    true,
  );
}
function approvalModal() {
  const c = S.candidate;
  modal(
    "Approve this parser",
    "Your approval confirms the field meanings, not just their syntax.",
    `<div class="field"><label for="reviewer">Reviewer name</label><input id="reviewer" placeholder="Your name"></div><div class="code mb">${esc(JSON.stringify(c.mapping, null, 2))}</div><label class="check-label"><input id="semantic-confirm" type="checkbox"><span>I reviewed the source documentation or labeled samples and checked source/destination roles, action meanings, time interpretation, and units.</span></label><p class="field-help mt">Approval signs a versioned WASM field mapping with its test vectors and SBOM. Retained events can then be replayed.</p>`,
    button("Cancel", "close") +
      button("Sign & deploy parser", "confirm-approve", "shield", "primary"),
  );
}
function offlineGuide() {
  modal(
    "Run inside an air gap",
    "Prepare dependencies before disconnecting the deployment network.",
    `<div class="guide-step"><span>1</span><div><h3>Stage the runtime</h3><p>Use the included wheelhouse preparation script on the same operating system, CPU architecture, and Python version as the target. Or build and save the container images on a connected machine.</p></div></div><div class="guide-step"><span>2</span><div><h3>Stage the local model</h3><p>Load <code>qwen3:0.6b</code> into Ollama before isolation. Transfer the model directory and runtime alongside the application. No model call goes to a cloud API.</p></div></div><div class="guide-step"><span>3</span><div><h3>Transfer trusted updates</h3><p>Parser bundles contain their binary, mapping, test vectors, SBOM, and signature. Pin the exporting registry’s public key before importing. Keep signing private keys protected.</p></div></div><div class="guide-step"><span>4</span><div><h3>Verify offline</h3><p>Disable internet access, start the application, send local device logs, run parser validation, verify evidence, and export a normalized event.</p></div></div>`,
    button("Close", "close"),
  );
}
function help() {
  modal(
    "A short path from log to evidence",
    "Use this flow for the demonstration.",
    [
      [
        "Capture",
        "Connect a device or run the labeled replay. Original received bytes are durably stored first.",
      ],
      [
        "Normalize",
        "Open Event stream to compare device fields with a consistent representation.",
      ],
      [
        "Onboard",
        "Open Parser lab, review an unfamiliar format, validate the mapping, and approve its signed plugin.",
      ],
      [
        "Recover",
        "Replay retained events. Original evidence stays unchanged and a new processing revision is recorded.",
      ],
      [
        "Verify",
        "Open an event’s evidence tab to verify its raw hash, Merkle proof, and ledger checkpoint.",
      ],
      [
        "Investigate",
        "Follow related addresses and detections, then save the selected evidence in a case.",
      ],
    ]
      .map(
        ([title, text], i) =>
          `<div class="guide-step"><span>${i + 1}</span><div><h3>${title}</h3><p>${text}</p></div></div>`,
      )
      .join(""),
    button("Start replay", "demo", "play", "primary"),
  );
}
async function action(el) {
  const a = el.dataset.action;
  const id = el.dataset.id;
  switch (a) {
    case "nav":
      location.hash = el.dataset.page;
      return;
    case "close":
      closeModal();
      return;
    case "help":
      help();
      return;
    case "logout":
      S.token = "";
      sessionStorage.removeItem("logflux-token");
      $("#login").hidden = false;
      closeModal();
      return;
    case "refresh":
      await refresh(true);
      return;
    case "add-source":
      sourceModal();
      return;
    case "connect-guide":
      connectGuide();
      return;
    case "offline-guide":
      offlineGuide();
      return;
    case "edit-source":
      sourceModal(S.stats.sources.find(x=>x.id===id)); return;
    case "save-source": {
      const body = {
        name: $("#source-name").value,
        peer: $("#source-peer").value.trim(),
        kind: $("#source-kind").value,
        mode: $("#source-mode").value,
      };
      const result = S.editSourceId ? await api("/sources/" + S.editSourceId,{method:"PATCH",body:JSON.stringify(body)}) : await post("/sources",body);
      closeModal();
      toast("Source registered: " + result.name);
      await refresh(true);
      return;
    }
    case "source-events":
      S.filters.source = id;
      S.filters.offset = 0;
      location.hash = "events";
      return;
    case "import":
      if (!S.stats.sources.length) {
        sourceModal();
        toast("Register a source first.");
        return;
      }
      importModal();
      return;
    case "do-import": {
      const source = $("#import-source").value;
      const file = $("#log-file").files[0];
      let result;
      if (file) {
        result = await api(
          "/upload?source_id=" +
            encodeURIComponent(source) +
            "&framing=" +
            $("#import-framing").value,
          {
            method: "POST",
            body: file,
            headers: { "Content-Type": "application/octet-stream" },
          },
        );
        toast(
          `${result.accepted} events preserved${result.rejected.length ? "; " + result.rejected.length + " rejected — check size limits" : ""}.`,
        );
      } else {
        result = await post("/ingest", {
          source_id: source,
          raw: $("#raw-input").value,
        });
        toast("Event preserved · " + result.event.status);
      }
      closeModal();
      await refresh(true);
      return;
    }
    case "demo": {
      await post("/demo/start", { count: 7000 });
      closeModal();
      toast(
        "Synthetic replay started (7,000 events). Every generated event is labeled replay.",
      );
      await refresh(true);
      return;
    }
    case "drift": {
      await post("/demo/drift");
      S.candidateId = null;
      toast("A changed-format replay event was retained for review.");
      await refresh(true);
      return;
    }
    case "event":
      await showEvent(id);
      return;
    case "event-tab":
      await showEvent(S.eventId, el.dataset.tab);
      return;
    case "download-raw":
      await download("/events/" + S.eventId + "/raw", S.eventId + ".raw");
      return;
    case "download-proof":
      await download(
        "/events/" + S.eventId + "/proof",
        S.eventId + ".proof.json",
      );
      return;
    case "export":
      exportModal();
      return;
    case "do-export": {
      const format = $("#export-format").value;
      await download(
        "/export?" +
          new URLSearchParams({
            format,
            q: S.filters.q,
            status: S.filters.status,
            source: S.filters.source, mode: S.filters.mode,
          }),
        "logflux-" + format + (format === "csv" ? ".csv" : ".jsonl"),
      );
      closeModal();
      return;
    }
    case "previous":
      S.filters.offset = Math.max(0, S.filters.offset - 40);
      await render();
      return;
    case "next":
      S.filters.offset += 40;
      await render();
      return;
    case "candidate":
      S.candidateId = id;
      S.labTab = "mapping";
      await render();
      return;
    case "lab-tab":
      S.labTab = el.dataset.tab;
      await render();
      return;
    case "pause-stream":
      S.paused = !S.paused; await render(); return;
    case "revise":
      S.candidateId = (await post("/candidates/" + S.candidateId + "/revise")).id; S.labTab = "mapping"; await render(); return;
    case "validate": {
      let mapping = S.candidate.mapping;
      if (S.labTab === "mapping") {
        mapping = {};
        $$(".mapping-select").forEach((s) => {
          if (s.value) mapping[s.dataset.field] = s.value;
        });
        await api("/candidates/" + S.candidateId + "/mapping", {
          method: "PUT",
          body: JSON.stringify({ mapping }),
        });
      }
      const rawExpectations = $("#semantic-expectations")?.value || S.expectations[S.candidateId] || "[]";
      let expectations;
      try { expectations = JSON.parse(rawExpectations); } catch { throw new Error("Semantic assertions must be a valid JSON array."); }
      S.expectations[S.candidateId] = rawExpectations;
      const r = await post("/candidates/" + S.candidateId + "/validate", {expectations});
      toast(
        r.passed
          ? "Replay and sandbox checks passed. Review field meanings before approval."
          : "Validation found issues. Check the report.",
        !r.passed,
      );
      await render();
      return;
    }
    case "approve":
      approvalModal();
      return;
    case "confirm-approve": {
      const result = await post("/candidates/" + S.candidateId + "/approve", {
        reviewer: $("#reviewer").value,
        acknowledge: $("#semantic-confirm").checked,
      });
      closeModal();
      toast("Signed parser deployed: " + result.plugin);
      await refresh(true);
      return;
    }
    case "replay": {
      const r = await post("/candidates/" + S.candidateId + "/replay");
      toast(r.count + " retained events replayed. Originals unchanged.");
      await refresh(true);
      return;
    }
    case "llm": {
      toast(
        "Local model is reviewing sample attributes. This can take a minute.",
      );
      const result = await post("/candidates/" + S.candidateId + "/llm");
      toast("Local AI proposal ready. Review and validate before approval.");
      S.labTab = "mapping";
      await render();
      modal(
        "Local AI proposal",
        result.model,
        `<p class="muted" style="font-size:13px">${esc(result.explanation)}</p><pre class="code mt">${esc(JSON.stringify(result.mapping, null, 2))}</pre>${notice("This is an untrusted suggestion. It cannot deploy a parser or approve itself.", "amber")}`,
        button("Review mapping", "close", "arrow", "primary"),
      );
      return;
    }
    case "plugins":
      await pluginsModal();
      return;
    case "plugin-export":
      await download(
        "/plugins/" + encodeURIComponent(id) + "/bundle",
        id + ".logflux.json",
      );
      return;
    case "plugin-activate":
      await post("/plugins/" + encodeURIComponent(id) + "/activate");
      toast("Plugin activated. Replay is a separate action.");
      await pluginsModal();
      return;
    case "plugin-import": {
      const file = $("#plugin-file").files[0];
      if (!file) throw new Error("Choose a bundle to import.");
      if (file.size > 8 * 1024 * 1024) throw new Error("Bundle exceeds 8 MiB.");
      const bundle = JSON.parse(await file.text());
      await post("/plugins/import", bundle);
      toast("Verified bundle imported inactive.");
      await pluginsModal();
      return;
    }
    case "seal": {
      const r = await post("/integrity/seal");
      toast(r.sealed_events + " events sealed; checkpoints synchronized.");
      await refresh(true);
      return;
    }
    case "batch": {
      const batches = await api("/integrity/batches");
      const b = batches.find((x) => x.id === id);
      modal(
        "Checkpoint #" + b.seq,
        "Merkle root and signed witness receipts.",
        `<pre class="code">${esc(JSON.stringify(b, null, 2))}</pre>`,
        button("Close", "close"),
        true,
      );
      return;
    }
    case "analytics-tab":
      S.analyticsTab=el.dataset.tab;
      await render();
      return;
    case "graph-zoom-in":
    case "graph-zoom-out":
    case "graph-zoom-reset":
      S.graphZoom=el.dataset.action==="graph-zoom-reset"?1:Math.max(.8,Math.min(2,S.graphZoom+(el.dataset.action==="graph-zoom-in"?.2:-.2)));
      await render();
      return;
    case "graph-ip":
      S.ip = el.dataset.ip;
      await render();
      return;
    case "investigate-search":
      S.ip = $("#graph-search").value.trim();
      S.graphSource = $("#graph-source").value;
      S.graphMinutes = $("#graph-time").value;
      await render();
      return;
    case "clear-ip":
      S.ip = "";
      await render();
      return;
    case "create-case":
      modal(
        "Create an investigation case",
        `${Math.min(S.graph.timeline.length, 1000)} currently matching events will be linked.`,
        `<div class="field"><label for="case-title">Case title</label><input id="case-title" placeholder="e.g. Review management-port activity"></div><div class="field"><label for="case-notes">Analyst notes</label><textarea id="case-notes" rows="5" placeholder="Record observations, uncertainty, and next steps."></textarea></div>`,
        button("Cancel", "close") +
          button("Save case", "save-case", "file", "primary"),
      );
      return;
    case "save-case": {
      const r = await post("/cases", {
        title: $("#case-title").value,
        notes: $("#case-notes").value,
        event_ids: S.graph.timeline.slice(0, 1000).map((e) => e.id),
      });
      closeModal();
      toast("Case saved with linked evidence.");
      await render();
      return;
    }
    case "case": {
      const cases = await api("/cases");
      const c = cases.find((x) => x.id === id);
      modal(
        esc(c.title),
        `${c.event_ids.length} evidence links · ${date(c.created_at)}`,
        `<p class="code">${esc(c.notes || "No notes recorded.")}</p><h3 class="mt">Linked evidence</h3>${c.event_ids
          .slice(0, 50)
          .map(
            (e) =>
              `<div class="revision"><button class="row-button mono" data-action="event" data-id="${e}">${e}</button></div>`,
          )
          .join("")}`,
        button("Close", "close"),
      );
      return;
    }
    case "witness":
      await post("/integrity/witness/" + el.dataset.name, {
        enabled: el.dataset.enabled === "true",
      });
      toast("Witness availability updated.");
      await refresh(true);
      return;
    case "add-sink":
      modal(
        "Add an output endpoint",
        "New normalized revisions will enter a durable delivery queue.",
        `<div class="field"><label for="sink-kind">Connector</label><select id="sink-kind"><option value="http">Generic HTTP webhook</option><option value="elasticsearch">Elasticsearch Bulk API</option></select></div><div class="field"><label for="sink-index">Elasticsearch index</label><input id="sink-index" value="logflux-events"></div><div class="field"><label for="sink-name">Output name</label><input id="sink-name" placeholder="Local SIEM collector"></div><div class="field"><label for="sink-url">HTTP(S) endpoint</label><input id="sink-url" placeholder="http://127.0.0.1:9000/events"></div>${notice("For Elasticsearch, enter the server base URL; LOGFLUX uses its Bulk API with stable event/revision IDs and checks item errors. Generic HTTP expects a LOGFLUX JSON envelope and uses Idempotency-Key. Retries are at least once.")}`,
        button("Cancel", "close") +
          button("Add output", "save-sink", "plus", "primary"),
      );
      return;
    case "save-sink":
      await post("/sinks", {
        name: $("#sink-name").value,
        url: $("#sink-url").value,
        kind: $("#sink-kind").value,
        index_name: $("#sink-index").value,
      });
      closeModal();
      toast("Output registered. New normalized events will be queued.");
      await render();
      return;
    case "sink-toggle":
      await post("/sinks/" + id + "/toggle", {
        enabled: el.dataset.enabled === "true",
      });
      await render();
      return;
  }
}
document.addEventListener("click", async (event) => {
  const el = event.target.closest("[data-action]");
  if (!el || el.disabled) return;
  const canDisable = el.tagName === "BUTTON";
  if (canDisable) el.disabled = true;
  try {
    await action(el);
  } catch (error) {
    toast(error.message, true);
  } finally {
    if (canDisable && el.isConnected) el.disabled = false;
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModal();
  if (event.key === "Enter" && event.target.id === "graph-search")
    action({ dataset: { action: "investigate-search" } }).catch((e) =>
      toast(e.message, true),
    );
  if (
    event.key === "Enter" &&
    event.target.matches('[role="button"][data-action]')
  )
    action(event.target).catch((e) => toast(e.message, true));
  if (event.key === "Tab" && S.modal) {
    const focusable = $$(
      '#modal-root button:not(:disabled),#modal-root input,#modal-root select,#modal-root textarea,#modal-root [tabindex="0"]',
    );
    if (!focusable.length) return;
    const first = focusable[0],
      last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      last.focus();
      event.preventDefault();
    } else if (!event.shiftKey && document.activeElement === last) {
      first.focus();
      event.preventDefault();
    }
  }
});
let searchTimer;
document.addEventListener("input", (e) => {
  if (e.target.id === "event-search") {
    S.filters.q = e.target.value;
    S.filters.offset = 0;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(
      () =>
        render()
          .then(() => {
            const input = $("#event-search");
            input?.focus();
            input?.setSelectionRange(input.value.length, input.value.length);
          })
          .catch((err) => toast(err.message, true)),
      400,
    );
  }
});
document.addEventListener("change", (e) => {
  if (e.target.id === "status-filter") S.filters.status = e.target.value;
  else if (e.target.id === "mode-filter") S.filters.mode = e.target.value;
  else if (e.target.id === "source-filter") S.filters.source = e.target.value;
  else return;
  S.filters.offset = 0;
  render().catch((err) => toast(err.message, true));
});
window.addEventListener("hashchange", () => {
  const p = location.hash.slice(1);
  if (!nav.some((n) => n[0] === p)) return;
  S.page = p;
  closeModal();
  navRender();
  $("#main").innerHTML =
    '<div class="loading"><span class="spinner"></span>Loading workspace…</div>';
  if (S.stats) render().catch((e) => toast(e.message, true));
});
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  S.token = $("#access-token").value.trim();
  $("#login-error").textContent = "";
  try {
    await api("/status");
    sessionStorage.setItem("logflux-token", S.token);
    $("#login").hidden = true;
    $("#access-token").value = "";
    await refresh(true);
  } catch (err) {
    $("#login-error").textContent = err.message;
  }
});
if (nav.some((n) => n[0] === location.hash.slice(1)))
  S.page = location.hash.slice(1);
navRender();
$("#clock").textContent = new Date().toLocaleDateString([], {
  day: "numeric",
  month: "short",
  year: "numeric",
});
if (S.token) refresh(true);
else $("#login").hidden = false;
setInterval(() => refresh(), 4000);
