"use strict";
const $ = (id) => document.getElementById(id);
const t = (k, v) => (window.I18N ? I18N.t(k, v) : k);   // atajo i18n

marked.setOptions({
  highlight: (code, lang) => {
    try { return hljs.highlight(code, { language: hljs.getLanguage(lang) ? lang : "plaintext" }).value; }
    catch { return code; }
  },
});
const renderMd = (md) => DOMPurify.sanitize(marked.parse(md || ""));

let CAPS = null;
const _RICO = 'class="role-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
const USER_SVG  = `<svg ${_RICO}><circle cx="12" cy="8" r="3.5"/><path d="M5.5 20a6.5 6.5 0 0 1 13 0"/></svg>`;
const ANGEL_SVG = `<svg ${_RICO}><ellipse cx="12" cy="4" rx="3" ry="1.1"/><path d="M12 7.5v8.5"/><path d="M12 9.5C10 7 7 6.4 4.4 7.2c0 3.3 2.1 6.1 5.1 6.8"/><path d="M12 9.5c2-2.5 5-3.1 7.6-2.3 0 3.3-2.1 6.1-5.1 6.8"/></svg>`;
const CROWN_SVG = `<svg ${_RICO}><path d="M5 17 4 7 8.5 11 12 6 15.5 11 20 7 19 17Z"/><path d="M5.4 20.2h13.2"/></svg>`;
const ICONS_ROLE = { dios: CROWN_SVG, angel: ANGEL_SVG, humano: USER_SVG };

// ---------- Tema ----------
const SUN_SVG = '<svg class="mi-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const MOON_SVG = '<svg class="mi-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>';
function setThemeIcon(theme) { const ic = $("themeIcon"); if (ic) ic.innerHTML = theme === "dark" ? MOON_SVG : SUN_SVG; }
setThemeIcon(document.documentElement.getAttribute("data-theme") || "light");
$("themeBtn").addEventListener("click", () => {
  const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  setThemeIcon(next);
});

// ---------- Popovers del header (menú de opciones + recursos) ----------
function closeMenus() { ["headerMenu", "statsPop"].forEach(id => $(id)?.classList.add("hidden")); }
const closeHeaderMenu = closeMenus;   // alias usado por openSettings/aboutBtn
function toggleMenu(id) { const el = $(id); if (!el) return; const wasClosed = el.classList.contains("hidden"); closeMenus(); if (wasClosed) el.classList.remove("hidden"); }
$("menuBtn")?.addEventListener("click", (e) => { e.stopPropagation(); toggleMenu("headerMenu"); });
$("statsChip")?.addEventListener("click", (e) => { e.stopPropagation(); toggleMenu("statsPop"); });
document.addEventListener("click", (e) => { if (!e.target.closest(".menu-wrap")) closeMenus(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenus(); });

// ---------- Toasts ----------
function toast(msg, kind) {
  const el = document.createElement("div");
  el.className = "toast " + (kind || "");
  el.textContent = msg;
  $("toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 300); }, 3200);
}

// ---------- Sesión / login ----------
async function loadMe() {
  const me = await (await fetch("/api/me")).json();
  if (me.authenticated) onAuthed(me); else showLogin();
}
function showLogin() {
  $("overlay").classList.remove("hidden");
  $("appWrap").classList.add("hidden");
  $("loginPass").focus();
}
async function doLogin() {
  const pass = $("loginPass").value;
  if (!pass) return;
  const fd = new FormData(); fd.append("password", pass);
  $("loginBtn").disabled = true;
  try {
    const res = await fetch("/api/login", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error");
    $("loginPass").value = "";
    onAuthed(data);
    toast(t("toast.welcome", { label: data.label }), "ok");
  } catch (e) { toast(e.message, "err"); }
  finally { $("loginBtn").disabled = false; }
}
function onAuthed(caps) {
  CAPS = caps;
  $("overlay").classList.add("hidden");
  $("appWrap").classList.remove("hidden");
  const b = $("roleBadge");
  b.className = "badge " + caps.role;
  b.innerHTML = `${ICONS_ROLE[caps.role] || ""}<span>${caps.label}</span>`;
  $("urlBlock").classList.toggle("hidden", !caps.convertUrl);
  // Base URL personalizada solo si el rol lo permite (se muestra al elegir "Personalizado")
  const customOpt = document.querySelector('#provider option[value="custom"]');
  if (customOpt) customOpt.hidden = !caps.llmCustomBase;
  $("baseUrlField").classList.add("hidden");
  $("ocrField").classList.toggle("hidden", !caps.ocr);
  $("advField").classList.toggle("hidden", !caps.advancedExtract);
  $("anonField").classList.toggle("hidden", !caps.anonimal);   // anonimización si el server la habilita
  if (caps.anonimal && caps.detectors) renderDetectors(caps.detectors);
  $("stats").classList.toggle("hidden", caps.stats === "none");
  // Versión real (la informa el servidor desde el tag de git).
  if (caps.version) $("aboutVer").textContent = caps.version.startsWith("v") ? caps.version : "v" + caps.version;
  // Si el servidor ya tiene claves de IA, la del usuario es opcional.
  const sp = caps.serverProviders || [];
  if (sp.length) $("apiKey").placeholder = t("ai.keyOptional", { p: sp.join(", ") });
  restoreApiKey();
  applyLimits();
  loadFormats();
  loadModelPrices();
  startStats();
}
function applyLimits() {
  if (!CAPS) return;
  const ico = (p) => `<svg class="lim-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  const I_FILE = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>';
  const I_LAYERS = '<path d="m12 2 9 4.5-9 4.5-9-4.5L12 2z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>';
  const I_MUTE = '<line x1="2" y1="2" x2="22" y2="22"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V5a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>';
  const mb = CAPS.maxFileMb ? t("limits.size.lim", { mb: CAPS.maxFileMb }) : t("limits.size.unl");
  const batch = CAPS.maxBatch ? t("limits.batch.lim", { n: CAPS.maxBatch }) : t("limits.batch.unl");
  let html = `<span class="lim-label">${t("limits.prefix")}</span>`
    + `<span class="lim-chip">${ico(I_FILE)}${mb}</span>`
    + `<span class="lim-chip">${ico(I_LAYERS)}${batch}</span>`;
  if (!CAPS.audioZip) html += `<span class="lim-chip warn">${ico(I_MUTE)}${t("limits.noaz").replace(/^\s*·\s*/, "")}</span>`;
  $("limits").className = "limits" + (CAPS.role ? " " + CAPS.role : "");
  $("limits").innerHTML = html;
}
async function doLogout() { await fetch("/api/logout", { method: "POST" }); CAPS = null; location.reload(); }

// Persistencia opcional de API keys POR PROVEEDOR (solo en este navegador).
const KEYS_STORE = "mid_keys", PROV_STORE = "mid_provider";
let KEYS = {};
let prevProvider = "auto";
function loadKeys() { try { KEYS = JSON.parse(localStorage.getItem(KEYS_STORE) || "{}"); } catch { KEYS = {}; } }
function saveKeys() { try { localStorage.setItem(KEYS_STORE, JSON.stringify(KEYS)); } catch {} }
function detectProvider(key) {
  if (/^AIza/.test(key)) return "gemini";
  if (/^sk-or-/.test(key)) return "openrouter";
  return "openai";
}
function providerSlot(p, key) { return p === "auto" ? detectProvider(key) : p; }

function restoreApiKey() {
  loadKeys();
  if (Object.values(KEYS).some(Boolean)) $("rememberKey").checked = true;
  const lastProv = localStorage.getItem(PROV_STORE);
  if (lastProv) {
    $("provider").value = lastProv;
    $("baseUrlField").classList.toggle("hidden", lastProv !== "custom");
  }
  prevProvider = $("provider").value;
  if (prevProvider !== "auto" && KEYS[prevProvider]) $("apiKey").value = KEYS[prevProvider];
  if ($("apiKey").value.trim() || serverHasKey()) { lastModelsKey = $("apiKey").value.trim(); fetchModels(); }
}
function persistApiKey() {
  if (!$("rememberKey").checked) { KEYS = {}; try { localStorage.removeItem(KEYS_STORE); localStorage.removeItem(PROV_STORE); } catch {} return; }
  const v = $("apiKey").value.trim();
  if (v) { KEYS[providerSlot($("provider").value, v)] = v; saveKeys(); }
  try { localStorage.setItem(PROV_STORE, $("provider").value); } catch {}
}
$("loginBtn").addEventListener("click", doLogin);
$("loginPass").addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
$("logoutBtn").addEventListener("click", doLogout);

// Mostrar / ocultar contraseña (ojito)
const EYE_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>`;
const EYE_OFF_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.4 0 10 7 10 7a13.2 13.2 0 0 1-1.67 2.68M6.6 6.6A13.4 13.4 0 0 0 2 11s3.6 7 10 7a9.1 9.1 0 0 0 5.4-1.6"/><path d="M14.12 14.12A3 3 0 1 1 9.88 9.88"/><line x1="2" y1="2" x2="22" y2="22"/></svg>`;
const _passToggle = $("loginPassToggle");
if (_passToggle) {
  _passToggle.innerHTML = EYE_SVG;
  _passToggle.addEventListener("click", () => {
    const inp = $("loginPass");
    const reveal = inp.type === "password";
    inp.type = reveal ? "text" : "password";
    _passToggle.innerHTML = reveal ? EYE_OFF_SVG : EYE_SVG;
    inp.focus();
  });
}

// ---------- Stats ----------
let statsTimer = null;
function startStats() {
  if (CAPS.stats === "none") return;
  const poll = async () => {
    try {
      const r = await fetch("/api/stats"); if (!r.ok) return;
      const s = await r.json();
      $("stConv").textContent = s.conversions ?? "—";
      if (CAPS.stats === "full" && s.cpu_percent !== undefined) {
        $("stCpu").textContent = s.cpu_percent.toFixed(0) + "%";
        $("stCpuBar").style.width = Math.min(100, s.cpu_percent) + "%";
        $("stRam").textContent = s.ram_used_gb + "/" + s.ram_total_gb + "G";
        $("stRamBar").style.width = s.ram_percent + "%";
        $("stCores").textContent = s.cores;
        // chip colapsado: un puntito de color por recurso (CPU y RAM) según uso
        const lvl = (p, w, c) => "status-dot" + (p >= c ? " crit" : (p >= w ? " warn" : ""));
        if ($("cpuDot")) $("cpuDot").className = lvl(s.cpu_percent, 70, 90);
        if ($("ramDot")) $("ramDot").className = lvl(s.ram_percent, 65, 85);
      } else {
        ["stCpu","stRam","stCores"].forEach(id => $(id).closest(".stat").classList.add("hidden"));
      }
    } catch {}
  };
  poll();
  if (statsTimer) clearInterval(statsTimer);
  statsTimer = setInterval(poll, 2500);
}
async function loadFormats() {
  try {
    const d = await (await fetch("/api/formats")).json();
    $("fmtBody").innerHTML = Object.entries(d.formats).map(([cat, exts]) =>
      `<div class="fmt-group"><h4>${escapeHtml(cat)}</h4><div class="fmt-chips">${exts.map(x => {
        const c = FTYPE_COLORS[x.toLowerCase()] || "var(--muted)";
        return `<span class="pill" style="--c:${c}">${x.toUpperCase()}</span>`;
      }).join("")}</div></div>`
    ).join("");
  } catch {}
}

// ---------- Cola ----------
let seq = 0;
let converting = false;
const items = new Map();
const FTYPE_COLORS = {
  pdf:"#e5484d",
  doc:"#3b82f6", docx:"#3b82f6", rtf:"#3b82f6", odt:"#3b82f6", epub:"#3b82f6",
  xls:"#22a06b", xlsx:"#22a06b", csv:"#22a06b", tsv:"#22a06b",
  ppt:"#e8833a", pptx:"#e8833a",
  html:"#64748b", htm:"#64748b", xml:"#64748b", json:"#64748b", md:"#64748b", txt:"#64748b",
  jpg:"#8b5cf6", jpeg:"#8b5cf6", png:"#8b5cf6", gif:"#8b5cf6", webp:"#8b5cf6", bmp:"#8b5cf6", tiff:"#8b5cf6",
  mp3:"#ec4899", wav:"#ec4899", m4a:"#ec4899", flac:"#ec4899", ogg:"#ec4899", aac:"#ec4899", opus:"#ec4899",
  mp4:"#6366f1", mov:"#6366f1", mkv:"#6366f1", webm:"#6366f1", avi:"#6366f1", m4v:"#6366f1", mpeg:"#6366f1", mpg:"#6366f1", wmv:"#6366f1", flv:"#6366f1",
  zip:"#d97706",
};
const MEDIA_EXTS = ["mp3","wav","m4a","flac","ogg","aac","opus","wma","mp4","mov","mkv","webm","avi","m4v","mpeg","mpg","wmv","flv","3gp"];
function fileChip(name, isUrl) {
  if (isUrl) return `<span class="ftype" style="background:#64748b">URL</span>`;
  const ext = (name.split(".").pop() || "").toLowerCase();
  const color = FTYPE_COLORS[ext] || "#7c8596";
  return `<span class="ftype" style="background:${color}">${(ext || "doc").slice(0, 4).toUpperCase()}</span>`;
}
const humanSize = (b) => b < 1024 ? b + " B" : b < 1048576 ? (b/1024).toFixed(1) + " KB" : (b/1048576).toFixed(1) + " MB";
const baseName = (n) => (n || "resultado").split(/[\\/]/).pop().replace(/\.[^.]+$/, "") || "resultado";

function addFile(file) {
  if (CAPS.maxBatch && items.size >= CAPS.maxBatch) { toast(t("toast.batch", { n: CAPS.maxBatch }), "err"); return; }
  if (CAPS.maxFileMb && file.size > CAPS.maxFileMb * 1048576) { toast(t("toast.size", { name: file.name, mb: CAPS.maxFileMb }), "err"); return; }
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (!CAPS.audioZip && (MEDIA_EXTS.includes(ext) || ext === "zip")) { toast(t("toast.noAudio"), "err"); return; }
  items.set(++seq, { id: seq, file, name: file.name, size: file.size, status: "queued", progress: 0, selected: true });
  render();
}
function addUrl(url) {
  if (!CAPS.convertUrl) { toast(t("toast.urlRole"), "err"); return; }
  if (!/^https?:\/\//i.test(url)) { toast(t("toast.urlScheme"), "err"); return; }
  items.set(++seq, { id: seq, url, name: url, size: 0, status: "queued", isUrl: true, progress: 0, selected: true });
  render();
}

function render() {
  const q = $("queue");
  $("appWrap").classList.toggle("has-files", items.size > 0);
  if (items.size === 0) { q.innerHTML = ""; updateZipBtn(); return; }
  const selCount = [...items.values()].filter(i => i.selected !== false).length;
  q.innerHTML =
    `<div class="qhead">
       <h3>${t("queue.title", { n: items.size })}</h3>
       <div class="spacer" style="flex:1"></div>
       <label class="selall"><input type="checkbox" id="selAll" ${selCount === items.size ? "checked" : ""}/> ${t("queue.all")}</label>
     </div>` +
    [...items.values()].map(itemHtml).join("");
  items.forEach(it => {
    const root = document.getElementById("it" + it.id);
    if (!root) return;
    root.querySelector(".item-top").addEventListener("click", (e) => {
      if (e.target.closest(".x") || e.target.closest(".sel")) return;
      if (it.status === "done") root.classList.toggle("open");
    });
    const cb = root.querySelector(".sel");
    if (cb) { cb.addEventListener("click", e => e.stopPropagation()); cb.addEventListener("change", () => { it.selected = cb.checked; updateSelUI(); }); }
    const x = root.querySelector(".x");
    if (x) x.addEventListener("click", () => { items.delete(it.id); render(); updateZipBtn(); });
    if (it.status === "done") wireResult(root, it);
  });
  $("selAll").addEventListener("change", (e) => { const v = e.target.checked; items.forEach(i => i.selected = v); render(); });
  updateZipBtn();
  updateSelUI();
}
function updateSelUI() {
  const all = [...items.values()];
  const sel = all.filter(i => i.selected !== false).length;
  // Solo se puede convertir lo que está pendiente (en cola o con error) y seleccionado.
  const pending = all.filter(i => i.selected !== false && (i.status === "queued" || i.status === "error")).length;
  const cv = $("convertBtn");
  if (cv) { cv.textContent = pending ? t("queue.convertSel", { n: pending }) : t("act.convertAll"); cv.disabled = converting || pending === 0; }
  const cnt = $("abCount"); if (cnt) cnt.textContent = t("queue.title", { n: items.size });
  const a = $("selAll"); if (a) a.checked = items.size > 0 && sel === items.size;
}

function pdfTypeI18n(tp) {
  if (!tp) return tp;
  if (tp.indexOf("forzado") >= 0) return t("pdf.forced");
  if (tp.indexOf("escane") >= 0) return t("pdf.scanned");
  if (tp.indexOf("electr") >= 0) return t("pdf.electronic");
  return tp;
}
function pdfBadge(r) {
  if (!r || !r.pdf_type) return "";
  const tp = pdfTypeI18n(r.pdf_type);
  return (r.ocr_applied ? t("sub.pdfocr", { t: tp }) : t("sub.pdf", { t: tp }));
}
function itemHtml(it) {
  const chip = { queued: t("chip.queued"), converting: chipText(it), done: t("chip.done"), error: t("chip.error") }[it.status];
  let sub;
  if (it.status === "done" && it.result) {
    sub = t("sub.stats", { w: it.result.words.toLocaleString(), c: it.result.chars.toLocaleString(), ms: it.result.elapsed_ms, min: Math.max(1, Math.round(it.result.words / 200)) }) + pdfBadge(it.result);
    if (it.result.anonymized) sub += ` · ${t("sub.anon", { n: it.result.pii_count ?? 0 })}`;
    if (it.result.note) sub += ` · ⚠️ ${it.result.note}`;
  } else if (it.status === "error") sub = it.error;
  else sub = it.isUrl ? t("sub.url") : humanSize(it.size);
  const pbar = it.status === "converting"
    ? `<div class="pbar"><span id="pb${it.id}" style="width:${it.progress}%"></span></div>` : "";
  const checkbox = it.status === "done"
    ? "" : `<input type="checkbox" class="sel" ${it.selected !== false ? "checked" : ""} title="Seleccionar" />`;
  return `
    <div class="item" id="it${it.id}">
      <div class="item-top">
        ${checkbox}
        ${fileChip(it.name, it.isUrl)}
        <div class="meta"><div class="name">${escapeHtml(it.name)}</div><div class="small">${escapeHtml(sub)}</div></div>
        <span class="chip ${it.status}" id="chip${it.id}">${chip}</span>
        <span class="x" title="Quitar">✕</span>
      </div>
      ${pbar}
      <div class="item-body"></div>
    </div>`;
}
function chipText(it) {
  if (it.phase === "processing") return `<span class="spinner"></span> ${t("chip.processing")}`;
  return `⬆ ${Math.round(it.progress)}%`;
}
function updateProgressDom(it) {
  const pb = $("pb" + it.id); if (pb) pb.style.width = it.progress + "%";
  const ch = $("chip" + it.id); if (ch) ch.innerHTML = chipText(it);
}

function wireResult(root, it) {
  const body = root.querySelector(".item-body");
  const canRedact = CAPS && CAPS.anonimal && it.file &&
    /\.(pdf|png|jpe?g|tiff?|bmp|webp)$/i.test(it.name || "");
  // Un solo desplegable con TODAS las salidas; PDF censurado destacado al final.
  const expGroup = (CAPS.export && CAPS.export.length)
    ? `<optgroup label="${t("dl.convert")}">${CAPS.export.map(f => `<option value="exp:${f.id}">${escapeHtml(f.label)}</option>`).join("")}</optgroup>` : "";
  const redactGroup = canRedact
    ? `<optgroup label="${t("dl.privacy")}"><option value="redact">${t("res.redact")}</option></optgroup>` : "";
  body.innerHTML = `
    <div class="resbar">
      <div class="tabs">
        <div class="tab active" data-v="preview">${t("tab.preview")}</div>
        <div class="tab" data-v="raw">${t("tab.raw")}</div>
        <div class="tab" data-v="split">${t("tab.split")}</div>
      </div>
      <div class="spacer" style="flex:1"></div>
      <button class="btn ghost sm" data-act="zoom">${t("res.zoom")}</button>
      <button class="btn ghost sm" data-act="copy">${t("res.copy")}</button>
      <select class="dl-sel">
        <option value="">${t("dl.pick")}</option>
        <optgroup label="Markdown">
          <option value="md">Markdown (.md)</option>
          <option value="compact">${t("dl.compact")}</option>
          <option value="chunks">${t("dl.chunks")}</option>
        </optgroup>
        ${expGroup}${redactGroup}
      </select>
      <button class="btn sm dl-go" disabled>${t("dl.download")}</button>
    </div>
    ${it.result.llm ? '<div class="llm-panel-wrap"></div>' : ""}
    <div class="view"><div class="preview"></div><pre class="raw hidden"></pre></div>`;
  const view = body.querySelector(".view"), prev = body.querySelector(".preview"), raw = body.querySelector(".raw");
  prev.innerHTML = renderMd(it.result.markdown);
  raw.textContent = it.result.markdown || "";
  body.querySelectorAll(".tab").forEach(tb => tb.addEventListener("click", () => {
    body.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    tb.classList.add("active");
    const v = tb.dataset.v;
    view.classList.toggle("split", v === "split");
    prev.classList.toggle("hidden", v === "raw");
    raw.classList.toggle("hidden", v === "preview");
  }));
  body.querySelector('[data-act="copy"]').addEventListener("click", async (e) => {
    await navigator.clipboard.writeText(it.result.markdown || "");
    e.target.textContent = "✓"; setTimeout(() => e.target.textContent = t("res.copy"), 1400);
  });
  body.querySelector('[data-act="zoom"]').addEventListener("click", () => openResultModal(it));
  // Desplegable de formato → habilita el botón Descargar (NO dispara solo).
  const dl = body.querySelector(".dl-sel"), go = body.querySelector(".dl-go");
  dl.addEventListener("change", () => {
    go.disabled = !dl.value;
    go.textContent = dl.value === "redact" ? t("res.redact") : t("dl.download");
  });
  go.addEventListener("click", () => doDownload(it, dl.value, go));
  const pw = body.querySelector(".llm-panel-wrap");
  if (pw) mountPanel(pw, it);
  esEnhanceAll(body);
}

// Ejecuta la descarga/acción según el formato elegido en el desplegable unificado.
function doDownload(it, value, btn) {
  if (!value) return;
  if (value === "md") return downloadMd(baseName(it.name), it.result.markdown || "");
  if (value === "compact") return downloadProcessed("/api/compact", it, btn, baseName(it.name) + "-compacto.md");
  if (value === "chunks") return downloadProcessed("/api/chunk", it, btn, baseName(it.name) + "-chunks.jsonl");
  if (value === "redact") return redactItem(it, btn);
  if (value.startsWith("exp:")) return exportFmt(it, value.slice(4), btn);
}

// Exportar el Markdown a otro formato (Pandoc) y descargar.
async function exportFmt(it, fmt, btn) {
  const orig = btn.textContent; btn.disabled = true; btn.textContent = "…";
  try {
    const fd = new FormData();
    fd.append("text", it.result.markdown || "");
    fd.append("fmt", fmt);
    const res = await fetch("/api/export", { method: "POST", body: fd });
    if (!res.ok) { let m = "Error " + res.status; try { m = (await res.json()).detail || m; } catch {} throw new Error(m); }
    const ext = res.headers.get("X-Export-Ext") || fmt;
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = baseName(it.name) + "." + ext;
    a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { toast(e.message, "err"); }
  finally { btn.disabled = false; btn.textContent = orig; }
}

// ---------- Panel LLM: catálogo de modelos EN VIVO (OpenRouter) ----------
let MODELS = [], MODELS_BY_ID = {}, MODELS_DEFAULTS = [];
const PANEL_STORE = "mid_panel_models";
async function loadModelPrices() {
  try {
    const d = await (await fetch("/api/model_prices")).json();
    MODELS = d.models || [];
    MODELS_BY_ID = Object.fromEntries(MODELS.map(m => [m.id, m]));
    MODELS_DEFAULTS = (d.defaults || []).filter(id => MODELS_BY_ID[id]);
    if (!MODELS_DEFAULTS.length) MODELS_DEFAULTS = MODELS.slice(0, 3).map(m => m.id);
  } catch {}
}
function panelModels() {
  try { const v = JSON.parse(localStorage.getItem(PANEL_STORE)); if (Array.isArray(v)) return v.filter(id => MODELS_BY_ID[id]); } catch {}
  return MODELS_DEFAULTS.slice();
}
function setPanelModels(ids) { try { localStorage.setItem(PANEL_STORE, JSON.stringify(ids)); } catch {} }
const ctxLabel = (n) => n >= 1e6 ? (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "M" : n >= 1000 ? Math.round(n / 1000) + "K" : "" + n;
const usd = (v) => v <= 0 ? "gratis" : v < 0.01 ? "$" + v.toFixed(4) : v < 1 ? "$" + v.toFixed(3) : "$" + v.toFixed(2);

// ---------- Panel LLM: render + interacción ----------
function mountPanel(wrap, it) {
  const d = it.result.llm; if (!d) return;
  const nf = (n) => (n || 0).toLocaleString();
  const sel = panelModels();
  const rows = sel.map(id => {
    const m = MODELS_BY_ID[id]; if (!m) return "";
    const cost = d.tokens / 1e6 * m.in, ok = d.tokens <= m.ctx;
    return `<tr>
      <td class="lm-name" title="${escapeHtml(m.id)}">${escapeHtml(m.name)}</td>
      <td class="lm-cost">~${usd(cost)}</td>
      <td><span class="llm-fit ${ok ? "ok" : "no"}">${ok ? IC_CHK : IC_X}${ctxLabel(m.ctx)}</span></td>
      <td><button class="lm-rm" data-id="${escapeHtml(id)}" title="${t("llm.remove")}">${IC_X}</button></td>
    </tr>`;
  }).join("");
  // desplegable para agregar (agrupado por proveedor), sin los ya elegidos
  const groups = {};
  MODELS.filter(m => !sel.includes(m.id)).forEach(m => { const g = m.id.split("/")[0]; (groups[g] ||= []).push(m); });
  const opts = Object.keys(groups).sort().map(g =>
    `<optgroup label="${escapeHtml(g)}">${groups[g].map(m => `<option value="${escapeHtml(m.id)}">${escapeHtml(m.name)} · ${usd(m.in)}/M · ${ctxLabel(m.ctx)}</option>`).join("")}</optgroup>`
  ).join("");
  const subParts = [];
  if (d.saved > 0) subParts.push(`${t("llm.saved")} ${d.saved_pct}%`);
  subParts.push(`${nf(d.pii_count)} ${t("llm.pii")}`);
  const inj = (d.injection && d.injection.length)
    ? `<div class="llm-warn">${IC_WARN}<div><b>${t("llm.injection")}</b> ${d.injection.map(x => escapeHtml(x.why)).join(" · ")}</div></div>` : "";
  wrap.innerHTML = `<div class="llm-panel">
    <div class="llm-head">
      <div class="llm-tok"><b>${nf(d.tokens)}</b> tokens</div>
      <span class="llm-sub">${subParts.join(" · ")}</span>
    </div>
    <table class="llm-tbl"><thead><tr><th>${t("llm.model")}</th><th>${t("llm.cost")}</th><th>${t("llm.context")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>
    <select class="llm-add"><option value="">+ ${t("llm.addModel")}</option>${opts}</select>
    ${inj}
  </div>`;
  wrap.querySelector(".llm-add").addEventListener("change", (e) => {
    if (!e.target.value) return;
    setPanelModels([...sel, e.target.value]); mountPanel(wrap, it);
  });
  wrap.querySelectorAll(".lm-rm").forEach(b => b.addEventListener("click", () => {
    setPanelModels(sel.filter(x => x !== b.dataset.id)); mountPanel(wrap, it);
  }));
  esEnhanceAll(wrap);
}

// Re-envía el Markdown del resultado a un endpoint de proceso y baja el archivo.
async function downloadProcessed(url, it, btn, filename, mime) {
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  try {
    const fd = new FormData();
    fd.append("text", it.result.markdown || "");
    const res = await fetch(url, { method: "POST", body: fd });
    if (!res.ok) throw new Error("Error " + res.status);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename; a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { toast(e.message, "err"); }
  finally { btn.disabled = false; btn.textContent = orig; }
}

// Censura visual: re-envía el archivo original y baja el PDF tachado.
let _redactStrict = "balanceado";
function redactFormData(it, preview, strict) {
  const fd = new FormData();
  fd.append("file", it.file);
  const lang = $("lang")?.value; if (lang) fd.append("lang", lang);
  fd.append("anon_strict", strict || _redactStrict || "balanceado");
  fd.append("anon_detectors", getEnabledDetectors().join(","));
  const rules = getAnonRules(); if (rules) fd.append("anon_rules", rules);
  if (preview) fd.append("preview", "1");
  return fd;
}

// Paso 1: elegir el NIVEL de censura.
function redactItem(it) { openRedactLevel(it); }
function openRedactLevel(it) {
  const cards = document.querySelectorAll("#redactLevelModal .rl-card");
  cards.forEach(c => { c.classList.toggle("rl-on", c.dataset.level === _redactStrict); c.onclick = () => { cards.forEach(x => x.classList.remove("rl-on")); c.classList.add("rl-on"); }; });
  $("rlGo").onclick = () => {
    const lvl = document.querySelector("#redactLevelModal .rl-card.rl-on")?.dataset.level || "balanceado";
    closeModal("redactLevelModal");
    runRedactPreview(it, lvl);
  };
  openModal("redactLevelModal");
}

// Paso 2: escanear con ese nivel y mostrar la vista previa de selección.
async function runRedactPreview(it, strict) {
  _redactStrict = strict;
  toast(t("redact.scanning"), "");
  try {
    const res = await fetch("/api/redact", { method: "POST", body: redactFormData(it, true, strict) });
    if (!res.ok) {
      let msg = "Error " + res.status;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    openRedactPreview(it, await res.json());
  } catch (e) { toast(e.message, "err"); }
}

const REDACT_TYPES = { PERSONA: "Nombre", DOMICILIO: "Domicilio", EMAIL: "Email", TEL: "Teléfono", ID: "ID/CUIT/DNI", FECHA: "Fecha", URL: "URL", SECRETO: "Secreto", DATO: "Dato" };
function openRedactPreview(it, d) {
  const ents = d.entities || [];
  $("rpStrict").textContent = d.strict ? t("anon.strict") : t("anon.balanced");
  $("rpDet").textContent = d.detectors == null ? t("rp.default") : d.detectors;
  $("rpCount").textContent = d.unique || 0;
  const body = $("rpList");
  $("rpAllWrap").style.display = ents.length ? "flex" : "none";
  if (!ents.length) {
    body.innerHTML = `<div class="rp-empty">${t("rp.empty")}</div>`;
  } else {
    body.innerHTML = ents.map(e =>
      `<label class="rp-row"><input type="checkbox" class="rp-chk" data-text="${escapeHtml(e.text)}" checked style="width:auto" />` +
      `<span class="rp-type">${escapeHtml(REDACT_TYPES[e.type] || e.type)}</span>` +
      `<span class="rp-text">${escapeHtml(e.text)}</span>` +
      `${e.count > 1 ? `<span class="rp-cnt">×${e.count}</span>` : ""}</label>`).join("");
  }
  const go = $("rpConfirm");
  const chks = () => Array.from(body.querySelectorAll(".rp-chk"));
  const refresh = () => {
    const sel = chks().filter(c => c.checked);
    $("rpSel").textContent = sel.length;
    go.disabled = !sel.length;
    $("rpAll").checked = sel.length === chks().length;
  };
  body.querySelectorAll(".rp-chk").forEach(c => c.addEventListener("change", refresh));
  $("rpAll").onchange = () => { chks().forEach(c => c.checked = $("rpAll").checked); refresh(); };
  refresh();
  go.onclick = () => {
    const only = chks().filter(c => c.checked).map(c => c.dataset.text);
    closeModal("redactPreviewModal");
    confirmRedact(it, only);
  };
  $("rpAdjust").onclick = () => { closeModal("redactPreviewModal"); openSettings("anon"); };
  $("rpLevel").onclick = () => { closeModal("redactPreviewModal"); openRedactLevel(it); };
  openModal("redactPreviewModal");
}

// Paso 2: confirmado — genera y descarga el PDF censurado de verdad (solo lo tildado).
async function confirmRedact(it, only) {
  toast(t("redact.working"), "");
  try {
    const fd = redactFormData(it, false);
    if (only && only.length) fd.append("only", JSON.stringify(only));
    const res = await fetch("/api/redact", { method: "POST", body: fd });
    if (!res.ok) {
      let msg = "Error " + res.status;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    const n = res.headers.get("X-Redacted-Entities") || "0";
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = baseName(it.name) + "-censurado.pdf";
    a.click(); URL.revokeObjectURL(a.href);
    toast(t("redact.done", { n }), "ok");
  } catch (e) { toast(e.message, "err"); }
}

// ---------- Modales ----------
const APP_VERSION = "1.3.4";
function openModal(id) { $(id).classList.remove("hidden"); }
function closeModal(id) { $(id).classList.add("hidden"); }
function openResultModal(it) {
  $("rmTitle").textContent = (it.name || "Resultado").split(/[\\/]/).pop();
  $("rmBody").innerHTML = renderMd(it.result.markdown);
  $("rmCopy").onclick = async () => { await navigator.clipboard.writeText(it.result.markdown || ""); toast(t("toast.copied"), "ok"); };
  $("rmDl").onclick = () => downloadMd(baseName(it.name), it.result.markdown || "");
  openModal("resultModal");
}
document.querySelectorAll(".modal-backdrop").forEach(bd => {
  bd.addEventListener("click", (e) => { if (e.target === bd || e.target.closest(".modal-close")) bd.classList.add("hidden"); });
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.querySelectorAll(".modal-backdrop:not(.hidden)").forEach(m => m.classList.add("hidden"));
});

function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c])); }

// ============ Escriba Select: dropdown custom (reemplaza el <select> nativo) ============
const ES_CHEV = '<svg class="es-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
const ES_CHECK = '<svg class="es-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
const IC_CHK = '<svg class="ic-fit" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
const IC_X = '<svg class="ic-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';
const IC_WARN = '<svg class="ic-warn" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>';
const esNorm = (s) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
function esCloseAll(except) {
  document.querySelectorAll(".es-wrap.open").forEach(w => { if (w !== except) { w.classList.remove("open"); w.querySelector(".es-pop")?.classList.add("hidden"); } });
}
function esEnhanceAll(root) { (root || document).querySelectorAll("select:not([data-es])").forEach(esEnhance); }
function esEnhance(sel) {
  sel.dataset.es = "1";
  const inline = sel.classList.contains("export-sel") || sel.id === "anonStrict";
  const wrap = document.createElement("div");
  wrap.className = "es-wrap" + (inline ? " es-inline" : "");
  sel.parentNode.insertBefore(wrap, sel);
  wrap.appendChild(sel); sel.classList.add("es-native");
  const trigger = document.createElement("button");
  trigger.type = "button"; trigger.className = "es-trigger";
  trigger.innerHTML = `<span class="es-val"></span>${ES_CHEV}`;
  const pop = document.createElement("div");
  pop.className = "es-pop hidden"; pop.setAttribute("role", "listbox");
  wrap.appendChild(trigger); wrap.appendChild(pop);
  const valEl = trigger.querySelector(".es-val");
  let rows = [], active = -1;

  const readOpts = () => {
    const out = [];
    Array.from(sel.children).forEach(ch => {
      if (ch.tagName === "OPTGROUP") Array.from(ch.children).forEach(o => out.push({ v: o.value, t: o.textContent, g: ch.label }));
      else if (ch.tagName === "OPTION") {
        const tt = ch.textContent.trim();
        const ph = ch.value === "" && (tt.startsWith("+") || /…$/.test(tt) || tt.endsWith("..."));
        out.push({ v: ch.value, t: ch.textContent, g: null, ph });
      }
    });
    return out;
  };
  const syncTrigger = () => {
    const opts = readOpts(); const o = opts.find(x => x.v === sel.value) || opts[0];
    valEl.textContent = o ? o.t : ""; valEl.classList.toggle("placeholder", !!(o && o.ph));
  };
  syncTrigger();
  sel.addEventListener("change", syncTrigger);

  const setActive = (i) => {
    if (rows[active]) rows[active].classList.remove("active");
    active = Math.max(0, Math.min(i, rows.length - 1));
    if (rows[active]) { rows[active].classList.add("active"); rows[active].scrollIntoView({ block: "nearest" }); }
  };
  const choose = (v) => { sel.value = v; sel.dispatchEvent(new Event("change", { bubbles: true })); syncTrigger(); close(); };
  function onKey(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(rows.length - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (rows[active]) rows[active].click(); }
    else if (e.key === "Escape") { e.preventDefault(); close(); trigger.focus(); }
  }
  const render = () => {
    const opts = readOpts();
    const useSearch = opts.filter(o => !o.ph).length > 8;
    pop.innerHTML = "";
    if (useSearch) {
      const search = document.createElement("input");
      search.className = "es-search"; search.placeholder = t("es.search"); search.type = "text";
      pop.appendChild(search);
      search.addEventListener("input", () => renderRows(opts, search.value));
      search.addEventListener("keydown", onKey);
      setTimeout(() => search.focus(), 10);
    }
    const list = document.createElement("div"); list.className = "es-list"; pop.appendChild(list);
    function renderRows(opts, f) {
      list.innerHTML = ""; rows = []; active = -1;
      const ff = esNorm(f); let lastG = null, shown = 0;
      opts.forEach(o => {
        if (o.ph || (ff && !esNorm(o.t).includes(ff))) return;
        if (o.g && o.g !== lastG) { const g = document.createElement("div"); g.className = "es-group"; g.textContent = o.g; list.appendChild(g); lastG = o.g; }
        const row = document.createElement("div");
        row.className = "es-opt" + (o.v === sel.value ? " es-sel" : "");
        row.setAttribute("role", "option");
        const parts = o.t.split(" · ");
        row.innerHTML = `<span class="es-label">${escapeHtml(parts[0])}</span>${parts.length > 1 ? `<span class="es-badge">${escapeHtml(parts.slice(1).join(" · "))}</span>` : ""}${ES_CHECK}`;
        row.addEventListener("click", () => choose(o.v));
        row.addEventListener("mousemove", () => { if (rows[active]) rows[active].classList.remove("active"); active = rows.indexOf(row); });
        list.appendChild(row); rows.push(row); shown++;
      });
      if (!shown) { const e = document.createElement("div"); e.className = "es-empty"; e.textContent = t("es.none"); list.appendChild(e); }
    }
    renderRows(opts, "");
  };
  const open = () => {
    render(); pop.classList.remove("hidden"); wrap.classList.add("open"); esCloseAll(wrap);
    active = rows.findIndex(r => r.classList.contains("es-sel"));
  };
  const close = () => { wrap.classList.remove("open"); pop.classList.add("hidden"); };
  trigger.addEventListener("click", (e) => { e.stopPropagation(); wrap.classList.contains("open") ? close() : open(); });
  trigger.addEventListener("keydown", (e) => {
    if (!wrap.classList.contains("open")) { if (["ArrowDown", "Enter", " "].includes(e.key)) { e.preventDefault(); open(); setActive(0); } }
    else onKey(e);
  });
}
document.addEventListener("click", (e) => { if (!e.target.closest(".es-wrap")) esCloseAll(); });
function downloadMd(name, md) {
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name + ".md"; a.click(); URL.revokeObjectURL(a.href);
}

// ---------- Conversión con barra de progreso (XHR) ----------
function convertOne(it) {
  return new Promise((resolve) => {
    it.status = "converting"; it.progress = 0; it.phase = "upload"; render();
    const fd = new FormData();
    if (it.isUrl) fd.append("url", it.url); else fd.append("file", it.file);
    const langVal = $("lang").value; if (langVal && langVal !== "auto") fd.append("lang", langVal);
    if (CAPS.ocr && $("ocrChk").checked) fd.append("ocr", "true");
    if (CAPS.advancedExtract && $("advChk").checked) fd.append("advanced", "true");
    // Anonimización de PII (si está habilitada y el usuario eligió un modo).
    if (CAPS.anonimal) {
      const am = $("anonMode")?.value;
      if (am && am !== "off") {
        fd.append("anonymize", am);
        fd.append("anon_strict", $("anonStrict")?.value || "balanceado");
        fd.append("anon_detectors", getEnabledDetectors().join(","));
        const rules = getAnonRules(); if (rules) fd.append("anon_rules", rules);
      }
    }
    // Cookies de YouTube (si el usuario las pegó en Configuración): solo aplican a links de YouTube.
    if (it.isUrl) { const ck = getYtCookies(); if (ck) fd.append("yt_cookies", ck); }
    persistApiKey();
    const prov = $("provider").value;
    const key = $("apiKey").value.trim();
    if (prov === "none") {
      fd.append("llm_provider", "none");   // explícito: no usar IA (aunque haya key en el server)
    } else if (key || serverHasKey()) {
      fd.append("llm_provider", prov);
      const m = $("model").value.trim(); if (m) fd.append("llm_model", m);
      if (key) fd.append("llm_api_key", key);
      if (prov === "custom") { const b = $("baseUrl").value.trim(); if (b) fd.append("llm_base_url", b); }
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/convert");
    let procTimer = null;

    // Fase 1: subida real (0–45%)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) { it.progress = Math.round((e.loaded / e.total) * 45); updateProgressDom(it); }
    };
    // Fase 2: procesando en el server (45–92%, animado, sin dato real)
    xhr.upload.onload = () => {
      it.phase = "processing"; it.progress = Math.max(it.progress, 48); updateProgressDom(it);
      procTimer = setInterval(() => {
        if (it.progress < 92) { it.progress += Math.max(0.4, (92 - it.progress) * 0.06); updateProgressDom(it); }
      }, 250);
    };
    const finish = () => { if (procTimer) clearInterval(procTimer); };

    xhr.onload = () => {
      finish();
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) { it.progress = 100; updateProgressDom(it); it.result = data; it.status = "done"; collectPseudoMap(data); }
        else { it.status = "error"; it.error = data.detail || `Error ${xhr.status}`; }
      } catch { it.status = "error"; it.error = `Error ${xhr.status}`; }
      render(); resolve();
    };
    xhr.onerror = () => { finish(); it.status = "error"; it.error = "Error de red"; render(); resolve(); };
    xhr.send(fd);
  });
}
async function convertAll(onlySelected = false) {
  let pending = [...items.values()].filter(it => it.status === "queued" || it.status === "error");
  if (onlySelected) pending = pending.filter(it => it.selected !== false);
  if (pending.length === 0) { toast(onlySelected ? t("toast.noSel") : t("toast.noQueue"), "err"); return; }
  converting = true; $("convertBtn").disabled = true;
  pending.forEach(it => { it.status = "queued"; it.progress = 0; }); render();
  await Promise.all(pending.map(convertOne));
  converting = false; updateSelUI();   // re-evalúa: si no queda nada pendiente, queda deshabilitado
  const ok = [...items.values()].filter(it => it.status === "done").length;
  const bad = [...items.values()].filter(it => it.status === "error").length;
  toast(bad ? t("toast.doneErr", { ok, bad }) : t("toast.done", { ok }), bad ? "" : "ok");
  if (ok > 0) celebrate();
  const first = pending.find(it => it.status === "done");
  if (first) document.getElementById("it" + first.id)?.classList.add("open");
}
function updateZipBtn() {
  const done = [...items.values()].filter(it => it.status === "done");
  $("zipBtn").classList.toggle("hidden", done.length < 2);
}
async function downloadZip() {
  const done = [...items.values()].filter(it => it.status === "done");
  const zip = new JSZip(); const used = {};
  done.forEach(it => { let n = baseName(it.name); if (used[n]) n += "-" + (++used[n]); else used[n] = 1; zip.file(n + ".md", it.result.markdown || ""); });
  const blob = await zip.generateAsync({ type: "blob" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "markitdown.zip"; a.click(); URL.revokeObjectURL(a.href);
  toast(t("toast.zip"), "ok");
}

// ---------- Inputs ----------
const drop = $("drop"), fileInput = $("fileInput");
drop.addEventListener("click", () => fileInput.click());
$("pickBtn").addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener("change", () => { [...fileInput.files].forEach(addFile); fileInput.value = ""; });
["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("drag"); }));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("drag"); }));
drop.addEventListener("drop", e => { [...e.dataTransfer.files].forEach(addFile); });
$("addUrlBtn").addEventListener("click", () => { const u = $("urlInput").value.trim(); if (u) { addUrl(u); $("urlInput").value = ""; } });
$("urlInput").addEventListener("keydown", e => { if (e.key === "Enter") $("addUrlBtn").click(); });
window.addEventListener("paste", e => {
  if (!CAPS) return;
  const files = [...(e.clipboardData?.files || [])];
  if (files.length) { files.forEach(addFile); toast(t("toast.pasted", { n: files.length }), "ok"); }
});
$("convertBtn").addEventListener("click", () => convertAll(true));
$("zipBtn").addEventListener("click", downloadZip);
$("clearBtn").addEventListener("click", () => { items.clear(); render(); });
// Mostrar el selector de intensidad solo cuando hay un modo de anonimización activo.
$("anonMode")?.addEventListener("change", () => {
  $("anonStrict")?.classList.toggle("hidden", $("anonMode").value === "off");
});

// ---------- Gateway de seudonimización: re-hidratar la respuesta del LLM ----------
let PSEUDO_MAP = {};
function collectPseudoMap(data) {
  const m = data && data.pseudonym_map;
  if (m && Object.keys(m).length) {
    Object.assign(PSEUDO_MAP, m);
    $("rehydrateBtn")?.classList.remove("hidden");
  }
}
function rehydrate(text) {
  const tokens = Object.keys(PSEUDO_MAP).sort((a, b) => b.length - a.length);
  for (const t of tokens) text = text.split(t).join(PSEUDO_MAP[t]);
  return text;
}
$("rehydrateBtn")?.addEventListener("click", () => {
  openModal("rehydrateModal");
  $("rehyInfo").textContent = t("rehy.entities", { n: Object.keys(PSEUDO_MAP).length });
});
$("rehyRun")?.addEventListener("click", () => {
  $("rehyOut").textContent = rehydrate($("rehyIn").value || "");
});
$("rehyCopy")?.addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("rehyOut").textContent || ""); toast(t("toast.copied"), "ok"); } catch {}
});

// ---------- Reglas de anonimización propias (Bring Your Own Rules) ----------
const RULES_STORE = "escriba_anon_rules";
function getAnonRules() { try { return localStorage.getItem(RULES_STORE) || ""; } catch { return ""; } }
function rulesStatus(msg) { const e = $("rulesStatus"); if (e) e.textContent = msg || ""; }
(function initAnonRules() {
  const ta = $("anonRules"); if (!ta) return;
  const saved = getAnonRules(); if (saved) ta.value = saved;
  $("saveRulesBtn")?.addEventListener("click", () => {
    const v = ta.value.trim();
    try { v ? localStorage.setItem(RULES_STORE, v) : localStorage.removeItem(RULES_STORE); } catch {}
    rulesStatus(""); toast(v ? t("rules.saved") : t("rules.cleared"));
  });
  $("clearRulesBtn")?.addEventListener("click", () => {
    ta.value = ""; try { localStorage.removeItem(RULES_STORE); } catch {}
    rulesStatus(""); toast(t("rules.cleared"));
  });
  $("validateRulesBtn")?.addEventListener("click", async () => {
    rulesStatus("…");
    const fd = new FormData(); fd.append("anon_rules", ta.value);
    try {
      const r = await fetch("/api/anon_rules/validate", { method: "POST", body: fd });
      const d = await r.json();
      if (r.ok) rulesStatus("✅ " + t("rules.ok", { p: d.patterns || 0, l: d.labels || 0, k: d.keep || 0 }));
      else rulesStatus("⚠️ " + (d.detail || "error"));
    } catch { rulesStatus("⚠️ " + t("rules.neterr")); }
  });
})();

// ---------- Detectores de PII (checkboxes por usuario, en este navegador) ----------
const DET_STORE = "escriba_anon_detectors";
const DET_GROUP_LABEL = { universal: "det.group.universal", regional: "det.group.regional", strict: "det.group.strict" };
function getEnabledDetectors() {
  return Array.from(document.querySelectorAll("#detectorsBox input[type=checkbox]:checked")).map(c => c.value);
}
function saveDetectors() { try { localStorage.setItem(DET_STORE, JSON.stringify(getEnabledDetectors())); } catch {} }
function renderDetectors(catalog) {
  const box = $("detectorsBox"); if (!box || !catalog || !catalog.length) return;
  let saved = null; try { saved = JSON.parse(localStorage.getItem(DET_STORE) || "null"); } catch {}
  const enabled = Array.isArray(saved) ? new Set(saved) : new Set(catalog.filter(d => d.default).map(d => d.id));
  const groups = {}; catalog.forEach(d => { (groups[d.group] = groups[d.group] || []).push(d); });
  box.innerHTML = "";
  ["universal", "regional", "strict"].forEach(g => {
    if (!groups[g]) return;
    const h = document.createElement("div");
    h.className = "adv-note"; h.style.cssText = "margin:8px 0 4px;font-weight:600"; h.textContent = t(DET_GROUP_LABEL[g]);
    box.appendChild(h);
    const wrap = document.createElement("div"); wrap.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:2px 12px";
    groups[g].forEach(d => {
      const lab = document.createElement("label"); lab.style.cssText = "display:flex;align-items:center;gap:7px;cursor:pointer;font-size:13px;margin:0";
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.value = d.id; cb.checked = enabled.has(d.id);
      cb.dataset.group = d.group; cb.style.width = "auto"; cb.addEventListener("change", saveDetectors);
      lab.appendChild(cb); lab.appendChild(document.createTextNode(" " + d.label));
      wrap.appendChild(lab);
    });
    box.appendChild(wrap);
  });
  $("detectorsField")?.classList.remove("hidden");
}
// Preset: "Estricto" prende los detectores agresivos; "Balanceado" los apaga.
$("anonStrict")?.addEventListener("change", () => {
  const on = $("anonStrict").value === "estricto";
  document.querySelectorAll('#detectorsBox input[data-group="strict"]').forEach(cb => { cb.checked = on; });
  saveDetectors();
});
window.addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") convertAll(); });

// ---------- Confeti ----------
const cv = $("confetti"), cx = cv.getContext("2d");
function resize() { cv.width = innerWidth; cv.height = innerHeight; }
resize(); window.addEventListener("resize", resize);
function celebrate() {
  const N = 140, parts = [], colors = ["#f0a98c","#e98e6f","#f5ece4","#e08a66","#ffd2bf"];
  for (let i = 0; i < N; i++) parts.push({ x: innerWidth/2, y: innerHeight/3, vx: (Math.random()-.5)*14, vy: Math.random()*-12-4, g: .35, s: Math.random()*6+4, c: colors[i%colors.length], r: Math.random()*Math.PI, vr: (Math.random()-.5)*.3 });
  let frames = 0;
  (function loop() {
    cx.clearRect(0,0,cv.width,cv.height);
    parts.forEach(p => { p.vy += p.g; p.x += p.vx; p.y += p.vy; p.r += p.vr; cx.save(); cx.translate(p.x,p.y); cx.rotate(p.r); cx.fillStyle = p.c; cx.fillRect(-p.s/2,-p.s/2,p.s,p.s*1.6); cx.restore(); });
    if (frames++ < 130) requestAnimationFrame(loop); else cx.clearRect(0,0,cv.width,cv.height);
  })();
}

// ---------- Proveedor de IA + traer modelos ----------
let lastModelsKey = "";
function serverHasKey() {
  const sp = (CAPS && CAPS.serverProviders) || [];
  const prov = $("provider").value;
  if (prov === "none") return false;
  return sp.length > 0 && (prov === "auto" || sp.includes(prov));
}
async function fetchModels() {
  if ($("provider").value === "none") return;   // sin IA: no hay modelos que traer
  const key = $("apiKey").value.trim();
  if (!key && !serverHasKey()) { toast(t("toast.keyFirst"), "err"); return; }
  const fd = new FormData();
  if (key) fd.append("llm_api_key", key);
  fd.append("llm_provider", $("provider").value);
  if ($("provider").value === "custom") fd.append("llm_base_url", $("baseUrl").value.trim());
  const btn = $("fetchModelsBtn"); const prev = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  try {
    const res = await fetch("/api/models", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error");
    const sel = $("model");
    sel.innerHTML = data.models.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join("");
    const pref = data.models.find(m => /gpt-4o|gemini-2|gemini-1\.5-flash/i.test(m)) || data.models[0];
    if (pref) sel.value = pref;
    toast(t("toast.models", { n: data.models.length }), "ok");
  } catch (e) { toast(e.message, "err"); }
  finally { btn.disabled = false; btn.textContent = prev; }
}
$("fetchModelsBtn").addEventListener("click", fetchModels);
$("apiKey").addEventListener("blur", () => {
  // Si pegás una key con "Sin IA" seleccionado, pasamos a Automático para que se use.
  if ($("apiKey").value.trim() && $("provider").value === "none") { $("provider").value = "auto"; prevProvider = "auto"; }
  persistApiKey();
  const key = $("apiKey").value.trim();
  if (key && key !== lastModelsKey) { lastModelsKey = key; fetchModels(); }
});
$("provider").addEventListener("change", () => {
  // Guardar la key actual bajo el proveedor anterior, luego autocompletar el nuevo.
  if ($("rememberKey").checked) {
    const v = $("apiKey").value.trim();
    if (v && prevProvider !== "none") { KEYS[providerSlot(prevProvider, v)] = v; saveKeys(); }
  }
  const p = $("provider").value;
  prevProvider = p;
  $("baseUrlField").classList.toggle("hidden", p !== "custom");
  if (p === "none") { $("model").innerHTML = `<option value="">${t("prov.none")}</option>`; }
  else if (p !== "auto") $("apiKey").value = KEYS[p] || "";
  if ($("rememberKey").checked) { try { localStorage.setItem(PROV_STORE, p); } catch {} }
  lastModelsKey = "";
  if (p !== "none" && ($("apiKey").value.trim() || serverHasKey())) fetchModels();
});
$("rememberKey").addEventListener("change", persistApiKey);

// ---------- Triggers de modales + header sticky ----------
$("formatsBtn").addEventListener("click", (e) => { e.stopPropagation(); openModal("formatsModal"); });
$("aboutBtn").addEventListener("click", () => { closeHeaderMenu(); openModal("aboutModal"); });
function openSettings(tab) {
  closeHeaderMenu();
  openModal("settingsModal"); ytckShown = false; applyYtckMask();
  if (tab) document.querySelector(`#settingsTabs .tab[data-stab="${tab}"]`)?.click();
}
$("settingsBtn").addEventListener("click", () => openSettings());
$("openOptionsBtn")?.addEventListener("click", () => openSettings("conv"));
// Tabs de Configuración (General / Conversión / IA / Anonimización / YouTube).
document.querySelectorAll("#settingsTabs .tab").forEach(tb => {
  tb.addEventListener("click", () => {
    document.querySelectorAll("#settingsTabs .tab").forEach(t => t.classList.toggle("active", t === tb));
    document.querySelectorAll("#settingsModal .stab-panel").forEach(p => p.classList.toggle("hidden", p.dataset.stabPanel !== tb.dataset.stab));
  });
});
$("aboutVer").textContent = "v" + APP_VERSION;

// ---------- Cookies de YouTube (se guardan SOLO en este navegador) ----------
const YTCK_STORE = "escriba_yt_cookies";
let ytckShown = false;   // por seguridad arrancan OCULTAS (blur)
function getYtCookies() { try { return localStorage.getItem(YTCK_STORE) || ""; } catch { return ""; } }
function ytCookiesStatus(msg) { const e = $("ytCookiesStatus"); if (e) e.textContent = msg || ""; }
function applyYtckMask() {
  const ta = $("ytCookies"); if (!ta) return;
  const has = ta.value.trim().length > 0;
  ta.style.filter = (has && !ytckShown) ? "blur(5px)" : "";   // difumina el contenido sensible
  const btn = $("toggleYtCookiesBtn");
  if (btn) {
    btn.style.display = has ? "" : "none";
    btn.textContent = ytckShown ? t("settings.ytCookiesHide") : t("settings.ytCookiesShow");
  }
}
(function initYtCookies() {
  const ta = $("ytCookies"); if (!ta) return;
  const saved = getYtCookies();
  if (saved) { ta.value = saved; ytCookiesStatus(t("settings.ytCookiesSaved")); }
  applyYtckMask();
  // Al enfocar el campo lo revelamos (no se puede editar borroso).
  ta.addEventListener("focus", () => { ytckShown = true; applyYtckMask(); });
  $("saveYtCookiesBtn")?.addEventListener("click", () => {
    const v = ta.value.trim();
    try { v ? localStorage.setItem(YTCK_STORE, v) : localStorage.removeItem(YTCK_STORE); } catch {}
    ytCookiesStatus(v ? t("settings.ytCookiesSaved") : "");
    toast(v ? t("settings.ytCookiesSaved") : t("settings.ytCookiesCleared"));
    ytckShown = false; applyYtckMask();   // re-ocultar tras guardar
  });
  $("clearYtCookiesBtn")?.addEventListener("click", () => {
    ta.value = ""; try { localStorage.removeItem(YTCK_STORE); } catch {}
    ytCookiesStatus(""); ytckShown = false; applyYtckMask(); toast(t("settings.ytCookiesCleared"));
  });
  $("toggleYtCookiesBtn")?.addEventListener("click", () => { ytckShown = !ytckShown; applyYtckMask(); });
  $("ytGuideBtn")?.addEventListener("click", () => openModal("ytGuideModal"));
})();
window.addEventListener("scroll", () => {
  document.querySelector(".topbar")?.classList.toggle("scrolled", window.scrollY > 8);
}, { passive: true });

// ---------- i18n: panel de idioma + aplicar ----------
(function initI18n() {
  if (!window.I18N) return;
  const sel = $("langSelect");
  sel.innerHTML = I18N.LANGS.map(l => `<option value="${l}">${I18N.NAMES[l]}</option>`).join("");
  sel.value = I18N.lang;
  sel.addEventListener("change", () => I18N.setLang(sel.value));
  window.onI18nChange = () => {
    // Reconstruir textos dinámicos al cambiar de idioma.
    applyLimits();
    if (items.size) render();
    if (CAPS) {
      const sp = CAPS.serverProviders || [];
      if (sp.length) $("apiKey").placeholder = t("ai.keyOptional", { p: sp.join(", ") });
    }
    const s = $("langSelect"); if (s) s.value = I18N.lang;
    applyYtckMask();   // refrescar el label del toggle (Mostrar/Ocultar)
  };
  I18N.apply();
})();

esEnhanceAll(document);   // dropdowns custom para todos los <select> estáticos
loadMe();
