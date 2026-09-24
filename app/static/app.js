"use strict";

const state = { period: "", categories: [], kinds: {}, view: "overview", selectedCat: null, selected: new Set() };
const MONTHS = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
const MONTHS_LONG = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
  "september", "oktober", "november", "december"];

const el = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const eur = new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR" });
const eur0 = new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const fmt = (v) => eur.format(v);
const fmt0 = (v) => eur0.format(v);
const compact = (v) => Math.abs(v) >= 1000 ? `€${(v / 1000).toLocaleString("nl-NL", { maximumFractionDigits: 1 })}k` : `€${Math.round(v)}`;
const monthLabel = (m) => `${MONTHS[+m.slice(5, 7) - 1]} ’${m.slice(2, 4)}`;
const periodLabel = (p) => {
  if (!p || p === "all") return "alle maanden";
  if (p.length === 4) return p;
  return `${MONTHS_LONG[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`;
};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Fout ${res.status}`);
  return data;
}
const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function toast(msg, ms = 3200) {
  const t = el("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), ms);
}

// ------------------------------------------------------------------ tooltip
const tip = el("tooltip");
function showTip(html, x, y) {
  tip.innerHTML = html;
  tip.hidden = false;
  const r = tip.getBoundingClientRect();
  let left = x + 14, top = y + 14;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
  tip.style.left = `${Math.max(8, left)}px`;
  tip.style.top = `${Math.max(8, top)}px`;
}
const hideTip = () => (tip.hidden = true);

// ------------------------------------------------------------------ init
async function init() {
  bindUi();
  await loadCategories();
  await loadPeriods();
  await refresh();
}

async function loadCategories() {
  state.categories = await api("api/categories");
  state.kinds = Object.fromEntries(state.categories.map((c) => [c.name, c.kind]));
  const opts = state.categories.map((c) => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
  el("tx-category").innerHTML = `<option value="">Alle categorieën</option>${opts}`;
  el("rule-category").innerHTML = opts;
  el("bulk-category").innerHTML = categorySelect("");
}

async function loadPeriods() {
  const { months, years } = await api("api/periods");
  const sel = el("period");
  const prev = state.period;
  sel.innerHTML =
    `<optgroup label="Maand">${months.map((m) => `<option value="${m}">${periodLabel(m)}</option>`).join("")}</optgroup>` +
    `<optgroup label="Jaar">${years.map((y) => `<option value="${y}">Heel ${y}</option>`).join("")}</optgroup>` +
    `<option value="all">Alles</option>`;
  state.period = prev && [...months, ...years, "all"].includes(prev) ? prev : (months[0] || "all");
  sel.value = state.period;
  const empty = months.length === 0;
  el("empty").classList.toggle("hidden", !empty);
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("hidden", empty || v.id !== `view-${state.view}`));
  sel.disabled = empty;
}

async function refresh() {
  if (!el("empty").classList.contains("hidden")) return;
  if (state.view === "overview") await renderOverview();
  if (state.view === "transactions") await renderTransactions();
  if (state.view === "subscriptions") await renderSubscriptions();
  if (state.view === "categories") await renderCategories();
  if (state.view === "rules") await renderRules();
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  if (el("empty").classList.contains("hidden")) {
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("hidden", v.id !== `view-${view}`));
  }
  try { localStorage.setItem("hb-view", view); } catch (_) { /* geen opslag */ }
  refresh();
}

function bindUi() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.goto)));
  el("period").addEventListener("change", (e) => { state.period = e.target.value; state.selectedCat = null; refresh(); });
  el("file-input").addEventListener("change", (e) => upload(e.target.files));
  el("detail-close").addEventListener("click", () => { state.selectedCat = null; renderOverview(); });

  let tTimer;
  el("tx-search").addEventListener("input", () => { clearTimeout(tTimer); tTimer = setTimeout(renderTransactions, 200); });
  el("tx-category").addEventListener("change", renderTransactions);
  el("rule-search").addEventListener("input", renderRules);
  el("rule-own").addEventListener("change", renderRules);
  el("rule-form").addEventListener("submit", addRule);
  el("cat-form").addEventListener("submit", addCategory);
  el("tx-all").addEventListener("change", (e) => {
    el("tx-body").querySelectorAll(".row-chk").forEach((c) => {
      c.checked = e.target.checked;
      toggleSelected(c.closest("tr"), c.checked);
    });
    updateBulkbar();
  });
  el("bulk-clear").addEventListener("click", () => { state.selected.clear(); renderTransactions(); });
  el("bulk-apply").addEventListener("click", bulkApply);
  el("reset-btn").addEventListener("click", resetAll);

  // Drag & drop overal op de pagina
  let depth = 0;
  const overlay = el("drop-overlay");
  window.addEventListener("dragenter", (e) => { if (e.dataTransfer?.types.includes("Files")) { depth++; overlay.hidden = false; } });
  window.addEventListener("dragleave", () => { depth = Math.max(0, depth - 1); if (!depth) overlay.hidden = true; });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => { e.preventDefault(); depth = 0; overlay.hidden = true; if (e.dataTransfer.files.length) upload(e.dataTransfer.files); });

  let resizeT;
  window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => state.view === "overview" && state.lastSummary && drawMonthly(state.lastSummary.monthly), 150); });

  try { const v = localStorage.getItem("hb-view"); if (v) state.view = v; } catch (_) { /* geen opslag */ }
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === state.view));
}

async function upload(files) {
  if (!files || !files.length) return;
  const fd = new FormData();
  [...files].forEach((f) => fd.append("files", f));
  try {
    const r = await api("api/upload", { method: "POST", body: fd });
    toast(`${r.added} nieuwe transacties toegevoegd${r.skipped ? `, ${r.skipped} al bekend` : ""}.`);
    state.period = "";
    await loadPeriods();
    await refresh();
  } catch (e) {
    toast(e.message, 6000);
  } finally {
    el("file-input").value = "";
  }
}

// ------------------------------------------------------------------ overzicht
function deltaHtml(cur, prev, higherIsGood, label) {
  if (prev == null || prev === 0) return `<div class="delta">&nbsp;</div>`;
  const pct = ((cur - prev) / Math.abs(prev)) * 100;
  if (Math.abs(pct) < 0.5) return `<div class="delta">Gelijk aan ${label}</div>`;
  const up = pct > 0;
  const good = up === higherIsGood;
  const cls = `${up ? "up" : "down"}-${good ? "good" : "bad"}`;
  return `<div class="delta"><span class="${cls}">${up ? "▲" : "▼"} ${Math.abs(pct).toFixed(0)}%</span> t.o.v. ${label}</div>`;
}

async function renderOverview() {
  const s = await api(`api/summary?period=${encodeURIComponent(state.period)}`);
  state.lastSummary = s;
  const avgLabel = `gem. ${s.prev_months} mnd ervoor`;
  const perMonth = s.months_in_period > 1;
  const savingsRate = s.income > 0 ? ((s.income - s.expenses) / s.income) * 100 : null;

  el("kpis").innerHTML = [
    { label: "Inkomsten", value: fmt0(s.income), delta: deltaHtml(s.income, s.prev_income, true, avgLabel),
      extra: perMonth ? `${fmt0(s.income / s.months_in_period)} per maand` : "" },
    { label: "Uitgaven", value: fmt0(s.expenses), delta: deltaHtml(s.expenses, s.prev_expenses, false, avgLabel),
      extra: perMonth ? `${fmt0(s.expenses / s.months_in_period)} per maand` : "" },
    { label: "Over (inkomsten − uitgaven)", value: fmt0(s.net),
      extra: (savingsRate != null ? `${savingsRate.toFixed(0)}% van de inkomsten` : "") +
        (s.saved > 0.5 ? ` · ${fmt0(s.saved)} naar sparen` : s.saved < -0.5 ? ` · ${fmt0(-s.saved)} uit sparen gehaald` : "") },
    { label: "Saldo", value: s.balance != null ? fmt0(s.balance) : "—", extra: "na laatste transactie in periode" },
  ].map((k) => `<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div>${k.delta || ""}${k.extra ? `<div class="delta">${k.extra}</div>` : ""}</div>`).join("");

  const notice = el("notice");
  if (s.uncategorized > 0) {
    notice.innerHTML = `<span>⚠︎ <b>${s.uncategorized}</b> transactie${s.uncategorized === 1 ? " is" : "s zijn"} nog niet gecategoriseerd in ${periodLabel(s.period)}.</span>
      <button class="btn small" id="fix-uncat">Nu indelen</button>`;
    notice.classList.remove("hidden");
    el("fix-uncat").onclick = () => { el("tx-category").value = "Ongecategoriseerd"; setView("transactions"); };
  } else notice.classList.add("hidden");

  el("monthly-legend").innerHTML =
    `<span class="key"><i class="swatch" style="background:var(--series-1)"></i>Inkomsten</span>` +
    `<span class="key"><i class="swatch" style="background:var(--series-2)"></i>Uitgaven</span>`;
  el("monthly-sub").textContent = s.monthly.length ? `${monthLabel(s.monthly[0].month)} – ${monthLabel(s.monthly[s.monthly.length - 1].month)}` : "";
  drawMonthly(s.monthly);
  drawCategoryBars(s);
  drawIncome(s);
  await drawDetail(s);
  drawSubsMini();
}

function niceMax(v) {
  if (v <= 0) return 100;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}

function drawMonthly(data) {
  const host = el("monthly-chart");
  const W = Math.max(320, host.clientWidth || 700);
  const H = 260, m = { t: 10, r: 8, b: 26, l: 48 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const max = niceMax(Math.max(1, ...data.flatMap((d) => [d.income, d.expenses])));
  const y = (v) => m.t + ih - (v / max) * ih;
  const band = iw / Math.max(data.length, 1);
  const bw = Math.max(3, Math.min(22, (band - 10) / 2));
  const round = (x, yTop, w, h) => {
    if (h <= 0) return "";
    const r = Math.min(4, h, w / 2);
    const yb = yTop + h;
    return `M${x},${yb}V${yTop + r}Q${x},${yTop} ${x + r},${yTop}H${x + w - r}Q${x + w},${yTop} ${x + w},${yTop + r}V${yb}Z`;
  };
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Staafdiagram inkomsten en uitgaven per maand">`;
  const lead = max / Math.pow(10, Math.floor(Math.log10(max)));
  const ticks = lead === 2 ? 4 : 5;
  for (let i = 0; i <= ticks; i++) {
    const v = (max / ticks) * i, yy = y(v);
    svg += `<line class="${i ? "gridline" : "baseline"}" x1="${m.l}" x2="${W - m.r}" y1="${yy}" y2="${yy}"/>`;
    svg += `<text x="${m.l - 8}" y="${yy + 4}" text-anchor="end">${compact(v)}</text>`;
  }
  const showEvery = band < 38 ? 2 : 1;
  data.forEach((d, i) => {
    const cx = m.l + band * i + band / 2;
    const x1 = cx - bw - 1, x2 = cx + 1; // 2px gap tussen de staven
    svg += `<path d="${round(x1, y(d.income), bw, y(0) - y(d.income))}" fill="var(--series-1)"/>`;
    svg += `<path d="${round(x2, y(d.expenses), bw, y(0) - y(d.expenses))}" fill="var(--series-2)"/>`;
    if (i % showEvery === 0 || i === data.length - 1)
      svg += `<text x="${cx}" y="${H - 8}" text-anchor="middle">${monthLabel(d.month)}</text>`;
    svg += `<rect class="hit" data-i="${i}" x="${m.l + band * i}" y="${m.t}" width="${band}" height="${ih}" rx="6"/>`;
  });
  svg += `</svg>`;
  host.innerHTML = data.length ? svg : `<p class="sub">Nog geen gegevens.</p>`;

  host.querySelectorAll(".hit").forEach((r) => {
    const d = data[+r.dataset.i];
    const net = d.income - d.expenses;
    const html = `<div class="t">${periodLabel(d.month)}</div>
      <div class="row"><span><i class="sw" style="background:var(--series-1)"></i>Inkomsten</span><b>${fmt(d.income)}</b></div>
      <div class="row"><span><i class="sw" style="background:var(--series-2)"></i>Uitgaven</span><b>${fmt(d.expenses)}</b></div>
      <hr><div class="row"><span>Over</span><b>${fmt(net)}</b></div>
      ${d.saved ? `<div class="row"><span>${d.saved > 0 ? "Naar sparen" : "Uit sparen"}</span><span>${fmt(Math.abs(d.saved))}</span></div>` : ""}`;
    r.addEventListener("mousemove", (e) => showTip(html, e.clientX, e.clientY));
    r.addEventListener("mouseleave", hideTip);
    r.style.cursor = "pointer";
    r.addEventListener("click", () => { state.period = d.month; el("period").value = d.month; hideTip(); refresh(); });
  });
}

function drawCategoryBars(s) {
  const cats = s.expense_categories;
  const max = Math.max(1, ...cats.map((c) => Math.max(c.total, c.avg_prev || 0)));
  const hasAvg = cats.some((c) => c.avg_prev != null);
  el("cat-sub").textContent = `${periodLabel(s.period)} · klik voor details`;
  el("cat-bars").innerHTML = cats.length ? cats.map((c) => {
    const pct = s.expenses ? (c.total / s.expenses) * 100 : 0;
    return `<button class="hbar ${state.selectedCat === c.category ? "selected" : ""}" data-cat="${esc(c.category)}">
      <span class="name">${esc(c.category)}</span>
      <span class="track"><span class="fill" style="width:${(c.total / max) * 100}%"></span>
        ${c.avg_prev ? `<span class="avg" style="left:calc(${(c.avg_prev / max) * 100}% - 1px)"></span>` : ""}</span>
      <span class="amt">${fmt0(c.total)}<small>${pct.toFixed(0)}%</small></span>
    </button>`;
  }).join("") + (hasAvg ? `<div class="hbars-legend"><span><i style="width:10px;height:10px;border-radius:3px;background:var(--series-1)"></i>Deze periode</span><span><i style="width:2px;height:12px;background:var(--text-primary);opacity:.55"></i>Gemiddelde ${s.prev_months} maanden ervoor</span></div>` : "")
    : `<p class="sub">Geen uitgaven in deze periode.</p>`;

  el("cat-bars").querySelectorAll(".hbar").forEach((b) => {
    const c = cats.find((x) => x.category === b.dataset.cat);
    b.addEventListener("click", () => { state.selectedCat = c.category; drawCategoryBars(s); drawDetail(s); });
    b.addEventListener("mousemove", (e) => {
      let html = `<div class="t">${esc(c.category)}</div><div class="row"><span>${esc(periodLabel(s.period))}</span><b>${fmt(c.total)}</b></div>`;
      if (c.avg_prev != null) {
        const diff = c.total - c.avg_prev;
        html += `<div class="row"><span>Gemiddeld ervoor</span><span>${fmt(c.avg_prev)}</span></div>
          <hr><div class="row"><span>Verschil</span><b>${diff >= 0 ? "+" : "−"}${fmt(Math.abs(diff))}</b></div>`;
      }
      showTip(html, e.clientX, e.clientY);
    });
    b.addEventListener("mouseleave", hideTip);
  });
}

async function drawDetail(s) {
  const body = el("detail-body");
  if (!state.selectedCat) {
    el("detail-title").textContent = "Grootste ontvangers";
    el("detail-sub").textContent = `Waar het meeste geld naartoe ging · ${periodLabel(s.period)}`;
    el("detail-close").classList.add("hidden");
    body.innerHTML = s.top_merchants.length ? `<ul class="list">${s.top_merchants.map((m) =>
      `<li><div class="l"><b>${esc(m.name)}</b><span>${esc(m.category)} · ${m.n}×</span></div><div class="r">${fmt(m.total)}</div></li>`).join("")}</ul>`
      : `<p class="sub">Geen uitgaven.</p>`;
    return;
  }
  const cat = state.selectedCat;
  el("detail-title").textContent = cat;
  el("detail-sub").textContent = "Verloop per maand en transacties in deze periode";
  el("detail-close").classList.remove("hidden");
  const [trend, txs] = await Promise.all([
    api(`api/category-trend?category=${encodeURIComponent(cat)}`),
    api(`api/transactions?period=${encodeURIComponent(state.period)}&category=${encodeURIComponent(cat)}`),
  ]);
  const max = Math.max(1, ...trend.map((t) => t.total));
  const bars = `<div style="display:flex;align-items:flex-end;gap:2px;height:90px;margin-bottom:6px">${trend.map((t) =>
    `<div class="mini" data-m="${t.month}" data-v="${t.total}" style="flex:1;height:100%;display:flex;align-items:flex-end;cursor:default">
       <div style="width:100%;height:${Math.max(2, (t.total / max) * 100)}%;background:${t.month === state.period ? "var(--series-1)" : "var(--series-1-soft)"};border-radius:4px 4px 0 0"></div></div>`).join("")}</div>
    <div style="display:flex;justify-content:space-between;color:var(--text-muted);font-size:11px;margin-bottom:12px">
      <span>${trend.length ? monthLabel(trend[0].month) : ""}</span><span>${trend.length ? monthLabel(trend[trend.length - 1].month) : ""}</span></div>`;
  const list = `<ul class="list">${txs.slice(0, 12).map((t) =>
    `<li><div class="l"><b>${esc(t.name)}</b><span>${t.date.split("-").reverse().join("-")}</span></div><div class="r ${t.amount > 0 ? "pos" : ""}">${fmt(-t.amount)}</div></li>`).join("")}</ul>
    ${txs.length > 12 ? `<button class="btn ghost small" id="detail-all">Alle ${txs.length} transacties bekijken</button>` : ""}`;
  body.innerHTML = bars + list;
  body.querySelectorAll(".mini").forEach((b) => {
    b.addEventListener("mousemove", (e) => showTip(`<div class="t">${periodLabel(b.dataset.m)}</div><div class="row"><span>${esc(cat)}</span><b>${fmt(+b.dataset.v)}</b></div>`, e.clientX, e.clientY));
    b.addEventListener("mouseleave", hideTip);
  });
  const all = el("detail-all");
  if (all) all.onclick = () => { el("tx-category").value = cat; setView("transactions"); };
}

function drawIncome(s) {
  el("income-list").innerHTML = s.income_categories.length ? `<ul class="list">${s.income_categories.map((c) =>
    `<li><div class="l"><b>${esc(c.category)}</b><span>${s.income ? ((c.total / s.income) * 100).toFixed(0) : 0}% van inkomsten</span></div><div class="r">${fmt(c.total)}</div></li>`).join("")}</ul>`
    : `<p class="sub">Geen inkomsten in deze periode.</p>`;
}

async function drawSubsMini() {
  const subs = (await api("api/subscriptions")).filter((x) => x.active);
  const total = subs.reduce((a, b) => a + b.monthly, 0);
  el("subs-mini").innerHTML = subs.length ? `<ul class="list">${subs.slice(0, 6).map((x) =>
    `<li><div class="l"><b>${esc(x.name)}</b><span>${esc(x.category)}</span></div><div class="r">${fmt(x.monthly)}<span class="sub" style="display:block;font-size:11px">p/m</span></div></li>`).join("")}
    <li><div class="l"><b>Totaal ${subs.length} vaste lasten</b></div><div class="r"><b>${fmt(total)}</b> p/m</div></li></ul>`
    : `<p class="sub">Nog niet genoeg maanden om vaste lasten te herkennen (minimaal 3).</p>`;
}

// ------------------------------------------------------------------ transacties
function categorySelect(current) {
  const groups = { uitgave: "Uitgaven", inkomen: "Inkomsten", overboeking: "Overboekingen (tellen niet mee)" };
  return Object.entries(groups).map(([k, label]) =>
    `<optgroup label="${label}">${state.categories.filter((c) => c.kind === k).map((c) =>
      `<option ${c.name === current ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</optgroup>`).join("");
}

async function renderTransactions() {
  const q = el("tx-search").value;
  const cat = el("tx-category").value;
  const txs = await api(`api/transactions?period=${encodeURIComponent(state.period)}&category=${encodeURIComponent(cat)}&q=${encodeURIComponent(q)}`);
  const total = txs.reduce((a, t) => a + t.amount, 0);
  el("tx-count").textContent = `${txs.length} transacties · saldo ${fmt(total)}`;
  const visible = new Set(txs.map((t) => t.id));
  [...state.selected].forEach((id) => { if (!visible.has(id)) state.selected.delete(id); });
  el("tx-all").checked = txs.length > 0 && txs.every((t) => state.selected.has(t.id));
  el("tx-body").innerHTML = txs.map((t) => `<tr data-id="${t.id}" data-name="${esc(t.name)}" class="${state.selected.has(t.id) ? "sel" : ""}">
      <td class="chk"><input type="checkbox" class="row-chk" ${state.selected.has(t.id) ? "checked" : ""} aria-label="Selecteer transactie"></td>
      <td class="date">${t.date.split("-").reverse().join("-")}</td>
      <td class="desc"><b>${esc(t.name)}</b><span title="${esc(t.description)}">${esc(t.mutation_type)}${t.description ? " · " + esc(t.description) : ""}</span></td>
      <td class="num ${t.amount > 0 ? "pos" : ""}">${t.amount > 0 ? "+" : ""}${fmt(t.amount)}</td>
      <td><select class="cat-select">${categorySelect(t.category)}</select>${t.manual ? `<span class="manual" title="Handmatig ingedeeld – klik om terug te zetten naar automatische indeling">✎</span>` : ""}</td>
    </tr>`).join("") || `<tr><td colspan="5" class="sub" style="padding:20px">Geen transacties gevonden.</td></tr>`;
  updateBulkbar();
  el("tx-body").querySelectorAll(".row-chk").forEach((c) => c.addEventListener("change", () => {
    toggleSelected(c.closest("tr"), c.checked);
    updateBulkbar();
  }));

  el("tx-body").querySelectorAll(".cat-select").forEach((sel) => sel.addEventListener("change", async (e) => {
    const tr = e.target.closest("tr");
    const name = tr.dataset.name;
    const makeRule = name && confirm(`Wil je alle transacties van “${name}” voortaan als “${e.target.value}” indelen?\n\nOK = regel maken voor alle (ook toekomstige) transacties\nAnnuleren = alleen deze transactie`);
    try {
      const r = await api(`api/transactions/${tr.dataset.id}`, json("PATCH", { category: e.target.value, make_rule: makeRule }));
      toast(makeRule ? `Regel gemaakt · ${r.changed} transacties ingedeeld als ${e.target.value}` : "Categorie aangepast");
      renderTransactions();
    } catch (err) { toast(err.message); }
  }));
  el("tx-body").querySelectorAll(".manual").forEach((m) => m.addEventListener("click", async (e) => {
    await api(`api/transactions/${e.target.closest("tr").dataset.id}/reset`, { method: "POST" });
    toast("Teruggezet naar automatische indeling");
    renderTransactions();
  }));
}

function toggleSelected(tr, on) {
  const id = +tr.dataset.id;
  if (on) state.selected.add(id); else state.selected.delete(id);
  tr.classList.toggle("sel", on);
}

function updateBulkbar() {
  const n = state.selected.size;
  el("bulkbar").hidden = n === 0;
  el("bulk-count").textContent = `${n} geselecteerd · verplaats naar`;
}

async function bulkApply() {
  const category = el("bulk-category").value;
  try {
    const r = await api("api/transactions/bulk", json("POST", { ids: [...state.selected], category }));
    toast(`${r.changed} transacties verplaatst naar ${category}`);
    state.selected.clear();
    renderTransactions();
  } catch (err) { toast(err.message); }
}

// ------------------------------------------------------------------ categorieën
const KIND_LABELS = { uitgave: "Uitgave", inkomen: "Inkomen", overboeking: "Overboeking" };

async function renderCategories() {
  const cats = await api("api/categories");
  const kindSelect = (cur) => Object.entries(KIND_LABELS).map(([k, l]) =>
    `<option value="${k}" ${k === cur ? "selected" : ""}>${l}</option>`).join("");
  el("cat-body").innerHTML = cats.map((c) => `<tr data-name="${esc(c.name)}">
      <td>${c.protected ? `<b>${esc(c.name)}</b>` : `<input class="cat-name" value="${esc(c.name)}" aria-label="Naam">`}</td>
      <td><select class="cat-kind" aria-label="Soort">${kindSelect(c.kind)}</select></td>
      <td class="num"><a href="#" class="cat-show">${c.tx_count}</a></td>
      <td class="num">${fmt(c.total)}</td>
      <td class="num">${c.rule_count}</td>
      <td class="num">${c.protected ? "" : `<div class="row-actions">
        <button class="btn ghost small cat-save" hidden>Opslaan</button>
        <button class="btn ghost small cat-del">Verwijderen</button></div>`}</td>
    </tr>`).join("");

  el("cat-body").querySelectorAll("tr").forEach((tr) => {
    const name = tr.dataset.name;
    const input = tr.querySelector(".cat-name");
    const save = tr.querySelector(".cat-save");
    const update = async (body) => {
      try {
        await api("api/categories/update", json("POST", { old: name, ...body }));
        toast("Categorie bijgewerkt");
        await loadCategories();
        renderCategories();
      } catch (err) { toast(err.message); }
    };
    tr.querySelector(".cat-kind").addEventListener("change", (e) => update({ kind: e.target.value }));
    if (input) {
      input.addEventListener("input", () => (save.hidden = input.value.trim() === name));
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") save.click(); });
      save.addEventListener("click", () => input.value.trim() && update({ name: input.value.trim() }));
    }
    tr.querySelector(".cat-show").addEventListener("click", (e) => {
      e.preventDefault();
      el("tx-category").value = name;
      el("period").value = state.period = "all";
      setView("transactions");
    });
    const del = tr.querySelector(".cat-del");
    if (del) del.addEventListener("click", () => {
      const cell = del.closest("td");
      const others = cats.filter((c) => c.name !== name);
      cell.innerHTML = `<div class="del-box"><span class="sub">Transacties naar</span>
        <select class="move-to">${others.map((c) => `<option ${c.name === "Ongecategoriseerd" ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select>
        <button class="btn small primary del-ok">Verwijder</button><button class="btn ghost small del-cancel">Annuleer</button></div>`;
      cell.querySelector(".del-cancel").onclick = renderCategories;
      cell.querySelector(".del-ok").onclick = async () => {
        try {
          const r = await api("api/categories/delete", json("POST", { name, move_to: cell.querySelector(".move-to").value }));
          toast(`“${name}” verwijderd · ${r.moved} transacties verplaatst`);
          await loadCategories();
          renderCategories();
        } catch (err) { toast(err.message); }
      };
    });
  });
}

// ------------------------------------------------------------------ vaste lasten
async function renderSubscriptions() {
  const subs = await api("api/subscriptions");
  const active = subs.filter((s) => s.active);
  const monthly = active.reduce((a, b) => a + b.monthly, 0);
  el("subs-kpis").innerHTML = `
    <div class="kpi"><div class="label">Vaste lasten per maand</div><div class="value">${fmt0(monthly)}</div><div class="delta">${active.length} actieve posten</div></div>
    <div class="kpi"><div class="label">Per jaar</div><div class="value">${fmt0(monthly * 12)}</div></div>
    <div class="kpi"><div class="label">Waarvan abonnementen & streaming</div><div class="value">${fmt0(active.filter((s) => s.category === "Abonnementen & streaming").reduce((a, b) => a + b.monthly, 0))}</div><div class="delta">per maand</div></div>`;
  el("subs-body").innerHTML = subs.map((s) => `<tr>
      <td class="desc"><b>${esc(s.name)}</b><span>${s.months} maanden gezien</span></td>
      <td><span class="pill">${esc(s.category)}</span></td>
      <td class="num">${fmt(s.monthly)}</td>
      <td class="num">${fmt(s.yearly)}</td>
      <td class="date">${s.last_date.split("-").reverse().join("-")}${s.changed ? `<br><span class="sub" style="font-size:11px">laatst ${fmt(s.last_amount)}</span>` : ""}</td>
      <td>${s.active ? `<span class="status"><i style="background:var(--good)"></i>Actief</span>` : `<span class="status"><i style="background:var(--text-muted)"></i>Gestopt?</span>`}</td>
    </tr>`).join("") || `<tr><td colspan="6" class="sub" style="padding:20px">Upload minimaal 3 maanden om vaste lasten te herkennen.</td></tr>`;
}

// ------------------------------------------------------------------ regels
async function renderRules() {
  const rules = await api("api/rules");
  const q = el("rule-search").value.toLowerCase();
  const own = el("rule-own").checked;
  const dir = { "": "Af en bij", af: "Af", bij: "Bij" };
  const rows = rules.filter((r) => (!own || r.user_defined) && (!q || r.pattern.includes(q) || r.category.toLowerCase().includes(q)));
  el("rules-body").innerHTML = rows.map((r) => `<tr>
      <td><code>${esc(r.pattern)}</code></td><td>${dir[r.direction]}</td>
      <td><span class="pill">${esc(r.category)}</span></td>
      <td class="sub">${r.user_defined ? "Eigen regel" : "Standaard"}</td>
      <td class="num"><button class="btn ghost small" data-del="${r.id}">Verwijderen</button></td></tr>`).join("");
  el("rules-body").querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    await api(`api/rules/${b.dataset.del}`, { method: "DELETE" });
    toast("Regel verwijderd, transacties opnieuw ingedeeld");
    renderRules();
  }));
}

async function addRule(e) {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    const r = await api("api/rules", json("POST", Object.fromEntries(f)));
    toast(`Regel toegevoegd · ${r.recategorized} transacties opnieuw ingedeeld`);
    e.target.reset();
    renderRules();
  } catch (err) { toast(err.message); }
}

async function addCategory(e) {
  e.preventDefault();
  const name = el("new-cat-name").value.trim();
  if (!name) return;
  try {
    await api("api/categories", json("POST", { name, kind: el("new-cat-kind").value }));
    el("new-cat-name").value = "";
    await loadCategories();
    toast(`Categorie “${name}” toegevoegd`);
    renderCategories();
  } catch (err) { toast(err.message); }
}

async function resetAll() {
  const answer = prompt("Hiermee worden ALLE transacties verwijderd (regels blijven bewaard). Typ WISSEN om te bevestigen.");
  if (answer !== "WISSEN") return;
  await api("api/reset", json("POST", { confirm: "WISSEN" }));
  toast("Alle transacties zijn verwijderd");
  await loadPeriods();
}

init().catch((e) => toast(e.message, 8000));
