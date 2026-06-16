"use strict";
const $ = (id) => document.getElementById(id);
const t = (k, v) => (window.I18N ? I18N.t(k, v) : k);   // atajo i18n
// Nota del backend: el campo "note" llega como CLAVE estable (p.ej. "noVoice");
// la traducimos con note.<clave>. Si la clave no existe, mostramos el valor crudo y nunca rompemos.
function noteText(n) { const k = "note." + n, tr = t(k); return tr === k ? n : tr; }

// Los bloques de código se renderizan sin resaltado de color (a propósito): se quitó
// highlight.js para no arrastrar una dependencia de CDN extra que, además, nunca se aplicaba.
const renderMd = (md) => DOMPurify.sanitize(marked.parse(md || ""), {
  USE_PROFILES: { html: true },
  FORBID_TAGS: ["style", "form"],
  ALLOW_DATA_ATTR: false,
});
// Forzar rel=noopener noreferrer y target=_blank en enlaces (defensa en profundidad).
if (window.DOMPurify) {
  DOMPurify.addHook("afterSanitizeAttributes", (node) => {
    if (node.tagName === "A" && node.getAttribute("href")) {
      node.setAttribute("rel", "noopener noreferrer");
      node.setAttribute("target", "_blank");
    }
  });
}

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
  try {
    const me = await (await fetch("/api/me")).json();
    if (me.authenticated) onAuthed(me); else showLogin();
  } catch { showLogin(); }   // respuesta no-JSON o red caída: degradar a login
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
    toast(t("toast.welcome", { label: data.label || data.role || "" }), "ok");
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
      if (CAPS.stats === "full" && typeof s.cpu_percent === "number") {
        const cpu = Number(s.cpu_percent) || 0, ram = Number(s.ram_percent) || 0;
        $("stCpu").textContent = cpu.toFixed(0) + "%";
        $("stCpuBar").style.width = Math.min(100, cpu) + "%";
        $("stRam").textContent = s.ram_used_gb + "/" + s.ram_total_gb + "G";
        $("stRamBar").style.width = ram + "%";
        $("stCores").textContent = s.cores;
        // chip colapsado: un puntito de color por recurso (CPU y RAM) según uso
        const lvl = (p, w, c) => "status-dot" + (p >= c ? " crit" : (p >= w ? " warn" : ""));
        if ($("cpuDot")) $("cpuDot").className = lvl(cpu, 70, 90);
        if ($("ramDot")) $("ramDot").className = lvl(ram, 65, 85);
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
const DEFAULT_NAME = () => t("res.fallbackName");
const stripPath = (n) => (n || "").split(/[\\/]/).pop();
const baseName = (n) => stripPath(n || DEFAULT_NAME()).replace(/\.[^.]+$/, "") || DEFAULT_NAME();

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

// Actualiza SOLO las partes mutables de un nodo .item ya creado (sin tocar .item-body).
function updateItemNode(it, root) {
  // (a) chip de estado
  const chip = root.querySelector("#chip" + it.id);
  if (chip) { chip.className = "chip " + it.status; chip.innerHTML = chipLabel(it); }
  // (b) subtítulo
  const small = root.querySelector(".meta .small");
  if (small) small.textContent = itemSub(it);
  // (c) barra de progreso: presente solo si converting
  const top = root.querySelector(".item-top");
  let pbar = root.querySelector(".pbar");
  if (it.status === "converting") {
    if (!pbar) {
      top.insertAdjacentHTML("afterend", `<div class="pbar"><span id="pb${it.id}" style="width:${it.progress}%"></span></div>`);
    } else {
      const sp = pbar.querySelector("span"); if (sp) sp.style.width = it.progress + "%";
    }
  } else if (pbar) {
    pbar.remove();
  }
  // (d) checkbox de selección: presente solo si NO está done
  let cb = root.querySelector(".sel");
  if (it.status === "done") {
    if (cb) cb.remove();
  } else if (!cb) {
    top.insertAdjacentHTML("afterbegin", `<input type="checkbox" class="sel" ${it.selected !== false ? "checked" : ""} title="${escapeHtml(t("queue.selectOne"))}" aria-label="${escapeHtml(t("queue.selectOne"))}" />`);
    const ncb = top.querySelector(".sel");
    ncb.addEventListener("click", e => e.stopPropagation());
    ncb.addEventListener("change", () => { it.selected = ncb.checked; updateSelUI(); });
  } else {
    cb.checked = it.selected !== false;
  }
  // (e) botón de páginas: solo PDFs pendientes (en cola / error)
  const wantPk = isPdfItem(it) && (it.status === "queued" || it.status === "error");
  const pk = root.querySelector(".pg-pick");
  if (!wantPk) { if (pk) pk.remove(); }
  else if (!pk) { mountPagesPick(root, it); }
  else { const sp = pk.querySelector("span"); if (sp) sp.textContent = pagesBtnLabel(it.pages || ""); }
}

function ensureQhead(q) {
  let qhead = q.querySelector(".qhead");
  if (!qhead) {
    q.insertAdjacentHTML("afterbegin",
      `<div class="qhead">
         <h3></h3>
         <div class="spacer" style="flex:1"></div>
         <label class="selall"><input type="checkbox" id="selAll"/> ${t("queue.all")}</label>
       </div>`);
    qhead = q.querySelector(".qhead");
    qhead.querySelector("#selAll").addEventListener("change", (e) => {
      const v = e.target.checked;
      items.forEach(i => { i.selected = v; });
      // Actualizar checkboxes en su lugar SIN re-renderizar (no destruir nada).
      items.forEach(it => {
        const cb = document.querySelector("#it" + it.id + " .sel");
        if (cb) cb.checked = v;
      });
      updateSelUI();
    });
  }
  return qhead;
}

function render() {
  const q = $("queue");
  $("appWrap").classList.toggle("has-files", items.size > 0);
  if (items.size === 0) { q.innerHTML = ""; updateZipBtn(); return; }

  const qhead = ensureQhead(q);
  // El "Seleccionar todo" solo gobierna ítems con checkbox (los que aún no están done).
  const selectable = [...items.values()].filter(i => i.status !== "done");
  const selCount = selectable.filter(i => i.selected !== false).length;
  qhead.querySelector("h3").textContent = t("queue.title", { n: items.size });
  qhead.querySelector("#selAll").checked = selectable.length > 0 && selCount === selectable.length;

  // Crear/actualizar cada ítem por clave (id), conservando el DOM existente.
  items.forEach(it => {
    let root = document.getElementById("it" + it.id);
    if (!root) {
      q.insertAdjacentHTML("beforeend", itemHtml(it));
      root = document.getElementById("it" + it.id);
      root.querySelector(".item-top").addEventListener("click", (e) => {
        if (e.target.closest(".x") || e.target.closest(".sel") || e.target.closest(".pg-pick")) return;
        if (it.status === "done") root.classList.toggle("open");
      });
      root.querySelector(".pg-pick")?.addEventListener("click", (e) => { e.stopPropagation(); openPagesFor(it, e.currentTarget); });
      const cb = root.querySelector(".sel");
      if (cb) { cb.addEventListener("click", e => e.stopPropagation()); cb.addEventListener("change", () => { it.selected = cb.checked; updateSelUI(); }); }
      const x = root.querySelector(".x");
      if (x) x.addEventListener("click", () => {
        // Si el ítem se está convirtiendo, abortar el XHR y limpiar el timer para no dejar
        // recursos vivos ni un resolve() pendiente que reactive el render.
        if (it.status === "converting" && it._xhr) { it._aborted = true; try { it._xhr.abort(); } catch {} }
        items.delete(it.id); render(); updateZipBtn();
      });
    } else {
      updateItemNode(it, root);
    }
    // Cablear el resultado EXACTAMENTE una vez, conservando su estado en renders posteriores.
    if (it.status === "done" && root.dataset.wired !== "1") {
      wireResult(root, it);
      root.dataset.wired = "1";
    }
  });

  // Quitar del DOM cualquier .item cuyo id ya no esté en items.
  q.querySelectorAll(".item").forEach(node => {
    const id = +node.id.slice(2);
    if (!items.has(id)) node.remove();
  });

  // Mantener el orden del DOM acorde al orden de inserción de items.
  let prev = qhead;
  items.forEach(it => {
    const node = document.getElementById("it" + it.id);
    if (!node) return;
    if (prev.nextElementSibling !== node) q.insertBefore(node, prev.nextElementSibling);
    prev = node;
  });

  updateZipBtn();
  updateSelUI();
}
function updateSelUI() {
  const all = [...items.values()];
  // El "Seleccionar todo" solo aplica a ítems con checkbox (no done).
  const selectable = all.filter(i => i.status !== "done");
  const sel = selectable.filter(i => i.selected !== false).length;
  // Solo se puede convertir lo que está pendiente (en cola o con error) y seleccionado.
  const pending = all.filter(i => i.selected !== false && (i.status === "queued" || i.status === "error")).length;
  const cv = $("convertBtn");
  if (cv) { cv.textContent = pending ? t("queue.convertSel", { n: pending }) : t("act.convertAll"); cv.disabled = converting || pending === 0; }
  const cnt = $("abCount"); if (cnt) cnt.textContent = t("queue.title", { n: items.size });
  const a = $("selAll"); if (a) a.checked = selectable.length > 0 && sel === selectable.length;
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
function itemSub(it) {
  let sub;
  if (it.status === "done" && it.result) {
    const w = it.result.words || 0, c = it.result.chars || 0;
    sub = t("sub.stats", { w: w.toLocaleString(), c: c.toLocaleString(), ms: it.result.elapsed_ms, min: Math.max(1, Math.round(w / 200)) }) + pdfBadge(it.result);
    if (it.result.anonymized) sub += ` · ${t("sub.anon", { n: it.result.pii_count ?? 0 })}`;
    if (it.result.note) sub += ` · ⚠️ ${noteText(it.result.note)}`;
  } else if (it.status === "error") sub = it.error;
  else sub = it.isUrl ? t("sub.url") : humanSize(it.size);
  return sub;
}
function chipLabel(it) {
  return { queued: t("chip.queued"), converting: chipText(it), done: t("chip.done"), error: t("chip.error") }[it.status];
}
function itemHtml(it) {
  const chip = chipLabel(it);
  const sub = itemSub(it);
  const pbar = it.status === "converting"
    ? `<div class="pbar"><span id="pb${it.id}" style="width:${it.progress}%"></span></div>` : "";
  const checkbox = it.status === "done"
    ? "" : `<input type="checkbox" class="sel" ${it.selected !== false ? "checked" : ""} title="${escapeHtml(t("queue.selectOne"))}" aria-label="${escapeHtml(t("queue.selectOne"))}" />`;
  return `
    <div class="item" id="it${it.id}">
      <div class="item-top">
        ${checkbox}
        ${fileChip(it.name, it.isUrl)}
        <div class="meta"><div class="name">${escapeHtml(it.name)}</div><div class="small">${escapeHtml(sub)}</div></div>
        ${pagesPickHtml(it)}
        <span class="chip ${it.status}" id="chip${it.id}">${chip}</span>
        <button type="button" class="x" title="${escapeHtml(t("act.remove"))}" aria-label="${escapeHtml(t("act.remove"))}">✕</button>
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
  const ttsGroup = (CAPS && CAPS.tts)
    ? `<optgroup label="${t("dl.audio")}"><option value="tts">${t("tts.opt")}</option></optgroup>` : "";
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
        ${expGroup}${ttsGroup}${redactGroup}
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
    go.textContent = dl.value === "redact" ? t("res.redact")
      : (dl.value === "tts" ? t("tts.open") : t("dl.download"));
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
  if (value === "redact") return openRedactLevel(it);
  if (value === "tts") return openTtsModal(it);
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
    if (!res.ok) throw new Error(await errFromRes(res));
    const ext = res.headers.get("X-Export-Ext") || fmt;
    const blob = await res.blob();
    triggerDownload(blob, baseName(it.name) + "." + ext);
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
  // Por defecto NO se muestra ningún modelo: el usuario los agrega desde el
  // desplegable "Simular costo por modelo". Si ya eligió algunos, se respetan.
  try { const v = JSON.parse(localStorage.getItem(PANEL_STORE)); if (Array.isArray(v)) return v.filter(id => MODELS_BY_ID[id]); } catch {}
  return [];
}
function setPanelModels(ids) { try { localStorage.setItem(PANEL_STORE, JSON.stringify(ids)); } catch {} }
const ctxLabel = (n) => n >= 1e6 ? (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "M" : n >= 1000 ? Math.round(n / 1000) + "K" : "" + n;
const usd = (v) => v <= 0 ? t("llm.free") : v < 0.01 ? "$" + v.toFixed(4) : v < 1 ? "$" + v.toFixed(3) : "$" + v.toFixed(2);

// ---------- Panel LLM: render + interacción ----------
function mountPanel(wrap, it) {
  const d = it.result.llm; if (!d) return;
  const nf = (n) => (n || 0).toLocaleString();
  const sel = panelModels();
  const rows = sel.map(id => {
    const m = MODELS_BY_ID[id]; if (!m || !m.ctx) return "";
    const hasPrice = m.in != null;
    const cost = hasPrice ? d.tokens / 1e6 * m.in : null, ok = d.tokens <= m.ctx;
    return `<tr>
      <td class="lm-name" title="${escapeHtml(m.id)}">${escapeHtml(m.name)}</td>
      <td class="lm-cost">${hasPrice ? "~" + usd(cost) : "—"}</td>
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
      <div class="llm-tok"><b>${nf(d.tokens)}</b> ${t("llm.tokens")}</div>
      <span class="llm-sub">${subParts.join(" · ")}</span>
    </div>
    ${rows ? `<table class="llm-tbl"><thead><tr><th>${t("llm.model")}</th><th>${t("llm.cost")}</th><th>${t("llm.context")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : ""}
    <select class="llm-add"><option value="">${t("llm.simCost")}</option>${opts}</select>
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
async function downloadProcessed(url, it, btn, filename) {
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  try {
    const fd = new FormData();
    fd.append("text", it.result.markdown || "");
    const res = await fetch(url, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await errFromRes(res));
    const blob = await res.blob();
    triggerDownload(blob, filename);
  } catch (e) { toast(e.message, "err"); }
  finally { btn.disabled = false; btn.textContent = orig; }
}

// ---------- Texto → audio (TTS / podcast) ----------
let _ttsVoices = null;   // catálogo de voces (cacheado)
let _ttsBlob = null;     // último MP3 generado

function appendLlmFields(fd) {
  const prov = $("provider") ? $("provider").value : "";
  const key = $("apiKey") ? $("apiKey").value.trim() : "";
  if (prov === "none") { fd.append("llm_provider", "none"); return; }
  if (key || (typeof serverHasKey === "function" && serverHasKey())) {
    fd.append("llm_provider", prov || "auto");
    const m = $("model") ? $("model").value.trim() : ""; if (m) fd.append("llm_model", m);
    if (key) fd.append("llm_api_key", key);
    if (prov === "custom") { const b = $("baseUrl") ? $("baseUrl").value.trim() : ""; if (b) fd.append("llm_base_url", b); }
  }
}

function _ttsGenderMark(g) { return g === "f" ? " ♀" : g === "m" ? " ♂" : ""; }
function _ttsFillVoices(sel, voices) {
  const piper = voices.filter(v => v.engine === "piper");
  const cloud = voices.filter(v => v.engine === "openai");
  let html = "";
  if (piper.length)
    html += `<optgroup label="${t("tts.local")}">` +
      piper.map(v => `<option value="${v.id}">${escapeHtml(v.label)}${_ttsGenderMark(v.gender)}</option>`).join("") + "</optgroup>";
  if (cloud.length)
    html += `<optgroup label="${t("tts.cloud")}">` +
      cloud.map(v => `<option value="${v.id}">${escapeHtml(v.label)}</option>`).join("") + "</optgroup>";
  sel.innerHTML = html || `<option value="">—</option>`;
}

async function openTtsModal(it) {
  const status = $("ttsStatus"), audio = $("ttsAudio"), dlBtn = $("ttsDownload");
  status.textContent = ""; audio.classList.add("hidden"); audio.removeAttribute("src");
  dlBtn.disabled = true; _ttsBlob = null;
  if (!_ttsVoices) {
    try { const r = await fetch("/api/tts_voices"); _ttsVoices = r.ok ? ((await r.json()).voices || []) : []; }
    catch { _ttsVoices = []; }
  }
  _ttsFillVoices($("ttsVoice"), _ttsVoices);
  _ttsFillVoices($("ttsVoiceB"), _ttsVoices);
  const opts = $("ttsVoiceB").options;            // 2da voz por defecto distinta
  if (opts.length > 1) $("ttsVoiceB").selectedIndex = 1;
  const syncMode = () => {
    const podcast = document.querySelector("#ttsModal input[name=ttsMode]:checked")?.value === "podcast";
    $("ttsVoiceBRow").classList.toggle("hidden", !podcast);
    $("ttsPodNote").classList.toggle("hidden", !podcast);
  };
  document.querySelectorAll("#ttsModal input[name=ttsMode]").forEach(r => r.onchange = syncMode);
  // reset a narración por defecto
  const nar = document.querySelector("#ttsModal input[name=ttsMode][value=narration]"); if (nar) nar.checked = true;
  syncMode();
  $("ttsGo").onclick = () => runTts(it);
  dlBtn.onclick = () => { if (_ttsBlob) triggerDownload(_ttsBlob, baseName(it.name) + (currentTtsMode() === "podcast" ? "-podcast.mp3" : ".mp3")); };
  openModal("ttsModal");
}

function currentTtsMode() {
  return document.querySelector("#ttsModal input[name=ttsMode]:checked")?.value || "narration";
}

async function runTts(it) {
  const go = $("ttsGo"), status = $("ttsStatus"), audio = $("ttsAudio"), dlBtn = $("ttsDownload");
  const mode = currentTtsMode();
  const fd = new FormData();
  fd.append("text", it.result.markdown || "");
  fd.append("mode", mode);
  fd.append("voice", $("ttsVoice").value || "");
  if (mode === "podcast") fd.append("voice_b", $("ttsVoiceB").value || "");
  fd.append("pitch", $("ttsPitch").value);
  fd.append("speed", $("ttsSpeed").value);
  fd.append("volume", $("ttsVolume").value);
  appendLlmFields(fd);
  go.disabled = true; dlBtn.disabled = true; _ttsBlob = null;
  audio.classList.add("hidden"); audio.removeAttribute("src");
  status.textContent = t(mode === "podcast" ? "tts.workingPod" : "tts.working");
  try {
    const res = await fetch("/api/tts", { method: "POST", body: fd });
    if (!res.ok) throw new Error(await errFromRes(res));
    _ttsBlob = await res.blob();
    audio.src = URL.createObjectURL(_ttsBlob);
    audio.classList.remove("hidden");
    dlBtn.disabled = false;
    status.textContent = t("tts.ready");
  } catch (e) { status.textContent = ""; toast(e.message, "err"); }
  finally { go.disabled = false; }
}

// Censura visual: re-envía el archivo original y baja el PDF tachado.
// Niveles de intensidad de anonimización que acepta el backend (anon_strict).
const REDACT_LEVELS = { default: "balanceado", strict: "estricto" };
let _redactStrict = REDACT_LEVELS.default;
function redactFormData(it, preview, strict) {
  const fd = new FormData();
  fd.append("file", it.file);
  const lang = $("lang")?.value; if (lang) fd.append("lang", lang);
  fd.append("anon_strict", strict || _redactStrict || REDACT_LEVELS.default);
  fd.append("anon_detectors", getEnabledDetectors().join(","));
  const rules = getAnonRules(); if (rules) fd.append("anon_rules", rules);
  if (preview) fd.append("preview", "1");
  return fd;
}

// Paso 1: elegir el NIVEL de censura.
function openRedactLevel(it) {
  const cards = document.querySelectorAll("#redactLevelModal .rl-card");
  cards.forEach(c => { c.classList.toggle("rl-on", c.dataset.level === _redactStrict); c.onclick = () => { cards.forEach(x => x.classList.remove("rl-on")); c.classList.add("rl-on"); }; });
  $("rlGo").onclick = () => {
    const lvl = document.querySelector("#redactLevelModal .rl-card.rl-on")?.dataset.level || REDACT_LEVELS.default;
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
    if (!res.ok) throw new Error(await errFromRes(res));
    openRedactPreview(it, await res.json());
  } catch (e) { toast(e.message, "err"); }
}

// Tipo de PII → clave i18n (redact.type.*); se resuelve con t() en openRedactPreview.
const REDACT_TYPES = { PERSONA: "redact.type.persona", DOMICILIO: "redact.type.domicilio", EMAIL: "redact.type.email", TEL: "redact.type.tel", ID: "redact.type.id", FECHA: "redact.type.fecha", URL: "redact.type.url", SECRETO: "redact.type.secreto", DATO: "redact.type.dato" };
function redactTypeLabel(type) { const k = REDACT_TYPES[type]; return k ? t(k) : type; }
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
      `<span class="rp-type">${escapeHtml(redactTypeLabel(e.type))}</span>` +
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
    if (!res.ok) throw new Error(await errFromRes(res));
    const n = res.headers.get("X-Redacted-Entities") || "0";
    const blob = await res.blob();
    triggerDownload(blob, baseName(it.name) + "-censurado.pdf");
    toast(t("redact.done", { n }), "ok");
  } catch (e) { toast(e.message, "err"); }
}

// ---------- Modales ----------
const _modalState = new Map();   // id -> { prevFocus, onKeydown }
function _focusables(root) {
  return Array.from(root.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter(el => el.offsetParent !== null || el === document.activeElement);
}
function openModal(id) {
  const el = $(id); if (!el) return;
  el.classList.remove("hidden");
  if (_modalState.has(id)) return;
  const prevFocus = document.activeElement;
  el.setAttribute("tabindex", "-1");
  // Mover el foco al primer control enfocable, o al propio modal.
  const f = _focusables(el);
  (f[0] || el).focus();
  // Focus trap sobre Tab dentro del modal.
  const onKeydown = (e) => {
    if (e.key !== "Tab") return;
    const items = _focusables(el);
    if (!items.length) { e.preventDefault(); el.focus(); return; }
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  el.addEventListener("keydown", onKeydown);
  _modalState.set(id, { prevFocus, onKeydown });
}
function closeModal(id) {
  const el = $(id); if (!el) return;
  el.classList.add("hidden");
  const st = _modalState.get(id);
  if (st) {
    el.removeEventListener("keydown", st.onKeydown);
    _modalState.delete(id);
    if (st.prevFocus && typeof st.prevFocus.focus === "function") st.prevFocus.focus();
  }
}
function openResultModal(it) {
  $("rmTitle").textContent = stripPath(it.name || DEFAULT_NAME());
  $("rmBody").innerHTML = renderMd(it.result.markdown);
  $("rmCopy").onclick = async () => { await navigator.clipboard.writeText(it.result.markdown || ""); toast(t("toast.copied"), "ok"); };
  $("rmDl").onclick = () => downloadMd(baseName(it.name), it.result.markdown || "");
  openModal("resultModal");
}
document.querySelectorAll(".modal-backdrop").forEach(bd => {
  bd.addEventListener("click", (e) => {
    // Cierra SOLO si: clic en el fondo, en la ✕, o en un control con [data-close]
    // que NO sea el propio backdrop (el backdrop también lleva data-close, y un
    // closest() ingenuo lo encontraría en CUALQUIER clic interno → cerraba siempre).
    const dc = e.target.closest("[data-close]");
    if (e.target === bd || e.target.closest(".modal-close") || (dc && dc !== bd)) {
      if (bd.id) closeModal(bd.id); else bd.classList.add("hidden");
    }
  });
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.querySelectorAll(".modal-backdrop:not(.hidden)").forEach(m => {
    if (m.id) closeModal(m.id); else m.classList.add("hidden");
  });
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
  document.querySelectorAll(".es-wrap.open").forEach(w => {
    if (w === except) return;
    if (w._esClose) w._esClose();
    else { w.classList.remove("open"); w.querySelector(".es-pop")?.classList.add("hidden"); }
  });
}
let _esSeq = 0;
function esEnhanceAll(root) { (root || document).querySelectorAll("select:not([data-es])").forEach(esEnhance); }
function esEnhance(sel) {
  sel.dataset.es = "1";
  const inline = sel.id === "anonStrict";
  const wrap = document.createElement("div");
  wrap.className = "es-wrap" + (inline ? " es-inline" : "");
  sel.parentNode.insertBefore(wrap, sel);
  wrap.appendChild(sel); sel.classList.add("es-native");
  const popId = "es-pop-" + (++_esSeq);
  const trigger = document.createElement("button");
  trigger.type = "button"; trigger.className = "es-trigger";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-controls", popId);
  // Copiar el nombre accesible del control nativo al trigger, si lo hubiera.
  if (sel.getAttribute("aria-label")) trigger.setAttribute("aria-label", sel.getAttribute("aria-label"));
  else if (sel.getAttribute("aria-labelledby")) trigger.setAttribute("aria-labelledby", sel.getAttribute("aria-labelledby"));
  trigger.innerHTML = `<span class="es-val"></span>${ES_CHEV}`;
  const pop = document.createElement("div");
  pop.className = "es-pop hidden"; pop.id = popId; pop.setAttribute("role", "listbox");
  wrap.appendChild(trigger); wrap.appendChild(pop);
  const valEl = trigger.querySelector(".es-val");
  let rows = [], active = -1;
  let typeBuf = "", typeTimer = null;   // type-ahead

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
    if (rows[active]) {
      rows[active].classList.add("active"); rows[active].scrollIntoView({ block: "nearest" });
      pop.setAttribute("aria-activedescendant", rows[active].id);
    } else {
      pop.removeAttribute("aria-activedescendant");
    }
  };
  const choose = (v) => { sel.value = v; sel.dispatchEvent(new Event("change", { bubbles: true })); syncTrigger(); close(); trigger.focus(); };
  const typeAhead = (ch) => {
    typeBuf += ch.toLowerCase();
    if (typeTimer) clearTimeout(typeTimer);
    typeTimer = setTimeout(() => { typeBuf = ""; }, 600);
    const idx = rows.findIndex(r => esNorm(r.textContent).startsWith(esNorm(typeBuf)));
    if (idx >= 0) setActive(idx);
  };
  function onKey(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(rows.length - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (rows[active]) rows[active].click(); }
    else if (e.key === "Escape") { e.preventDefault(); close(); trigger.focus(); }
    else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { typeAhead(e.key); }
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
        row.id = popId + "-opt-" + shown;
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", o.v === sel.value ? "true" : "false");
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
    trigger.setAttribute("aria-expanded", "true");
    const selIdx = rows.findIndex(r => r.classList.contains("es-sel"));
    setActive(selIdx < 0 ? 0 : selIdx);
  };
  const close = () => {
    wrap.classList.remove("open"); pop.classList.add("hidden");
    trigger.setAttribute("aria-expanded", "false");
    pop.removeAttribute("aria-activedescendant");
  };
  wrap._esClose = close; wrap._esTrigger = trigger;
  trigger.addEventListener("click", (e) => { e.stopPropagation(); wrap.classList.contains("open") ? close() : open(); });
  trigger.addEventListener("keydown", (e) => {
    if (!wrap.classList.contains("open")) { if (["ArrowDown", "Enter", " "].includes(e.key)) { e.preventDefault(); open(); } }
    else onKey(e);
  });
}
document.addEventListener("click", (e) => {
  if (!e.target.closest(".es-wrap")) {
    // Si el foco quedó dentro de un pop que cerramos por click afuera, devolverlo al trigger.
    document.querySelectorAll(".es-wrap.open").forEach(w => {
      const focusInside = w.contains(document.activeElement);
      w._esClose ? w._esClose() : (w.classList.remove("open"), w.querySelector(".es-pop")?.classList.add("hidden"));
      if (focusInside && w._esTrigger) w._esTrigger.focus();
    });
  }
});
async function errFromRes(res){ let m = "Error " + res.status; try { m = (await res.json()).detail || m; } catch {} return m; }
function triggerDownload(blob, filename){ const a = document.createElement("a"); const url = URL.createObjectURL(blob); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 60000); }
function downloadMd(name, md) {
  const blob = new Blob([md], { type: "text/markdown" });
  triggerDownload(blob, name + ".md");
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
    if (it.pages) fd.append("pages", it.pages);   // selección por-archivo del asistente (solo aplica a PDF)
    // Anonimización de PII (si está habilitada y el usuario eligió un modo).
    if (CAPS.anonimal) {
      const am = $("anonMode")?.value;
      if (am && am !== "off") {
        fd.append("anonymize", am);
        fd.append("anon_strict", $("anonStrict")?.value || REDACT_LEVELS.default);
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
    it._xhr = xhr;
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
      it._procTimer = procTimer;
    };
    const finish = () => { if (procTimer) { clearInterval(procTimer); procTimer = null; } it._procTimer = null; it._xhr = null; };
    // El ítem fue borrado con la X: no tocar estado ni re-renderizar.
    const settleAborted = () => { finish(); resolve(); };

    xhr.onload = () => {
      finish();
      if (it._aborted) return resolve();
      // Parsear primero: un 2xx con cuerpo no-JSON NO debe perder silenciosamente el resultado.
      let data = null, parseErr = false;
      try { data = JSON.parse(xhr.responseText); } catch { parseErr = true; }
      if (xhr.status >= 200 && xhr.status < 300 && !parseErr) {
        it.progress = 100; updateProgressDom(it); it.result = data; it.status = "done";
        try { collectPseudoMap(data); } catch {}
      } else {
        it.status = "error";
        it.error = (data && data.detail) || (parseErr ? t("toast.netErr") : `Error ${xhr.status}`);
      }
      render(); resolve();
    };
    xhr.onerror = () => { finish(); if (it._aborted) return resolve(); it.status = "error"; it.error = t("toast.netErr"); render(); resolve(); };
    xhr.ontimeout = () => { finish(); if (it._aborted) return resolve(); it.status = "error"; it.error = t("toast.netErr"); render(); resolve(); };
    xhr.onabort = settleAborted;
    xhr.send(fd);
  });
}
async function convertAll(onlySelected = false) {
  let pending = [...items.values()].filter(it => it.status === "queued" || it.status === "error");
  if (onlySelected) pending = pending.filter(it => it.selected !== false);
  if (pending.length === 0) { toast(onlySelected ? t("toast.noSel") : t("toast.noQueue"), "err"); return; }
  converting = true; $("convertBtn").disabled = true;
  pending.forEach(it => { it.status = "queued"; it.progress = 0; }); render();
  // Pool de concurrencia: no disparar TODA la cola en paralelo (limita carga server/red).
  const POOL = 3;
  const queue = pending.slice();
  while (queue.length) {
    await Promise.all(queue.splice(0, POOL).map(convertOne));
  }
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
  triggerDownload(blob, "markitdown.zip");
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
$("clearBtn").addEventListener("click", () => { items.clear(); PSEUDO_MAP = {}; $("rehydrateBtn")?.classList.add("hidden"); render(); });
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
// Re-hidrata en UN solo pase con una regex de alternancia («TIPO_N»), evitando colisiones
// cuando un token es substring de otro y la reinyección O(tokens × longitud).
function rehydrate(text) {
  if (!Object.keys(PSEUDO_MAP).length) return text;
  return text.replace(/«[A-Z]+_\d+»/g, (m) => (m in PSEUDO_MAP ? String(PSEUDO_MAP[m]) : m));
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
const confettiCv = $("confetti"), confettiCx = confettiCv.getContext("2d");
function resize() { confettiCv.width = innerWidth; confettiCv.height = innerHeight; }
resize(); window.addEventListener("resize", resize);
let _confettiRAF = null;
function celebrate() {
  // Cancelar cualquier loop previo para no apilar rAF sobre el mismo canvas en conversiones seguidas.
  if (_confettiRAF) cancelAnimationFrame(_confettiRAF);
  const N = 140, parts = [], colors = ["#f0a98c","#e98e6f","#f5ece4","#e08a66","#ffd2bf"];
  for (let i = 0; i < N; i++) parts.push({ x: innerWidth/2, y: innerHeight/3, vx: (Math.random()-.5)*14, vy: Math.random()*-12-4, g: .35, s: Math.random()*6+4, c: colors[i%colors.length], r: Math.random()*Math.PI, vr: (Math.random()-.5)*.3 });
  let frames = 0;
  (function loop() {
    confettiCx.clearRect(0,0,confettiCv.width,confettiCv.height);
    parts.forEach(p => { p.vy += p.g; p.x += p.vx; p.y += p.vy; p.r += p.vr; confettiCx.save(); confettiCx.translate(p.x,p.y); confettiCx.rotate(p.r); confettiCx.fillStyle = p.c; confettiCx.fillRect(-p.s/2,-p.s/2,p.s,p.s*1.6); confettiCx.restore(); });
    if (frames++ < 130) { _confettiRAF = requestAnimationFrame(loop); }
    else { _confettiRAF = null; confettiCx.clearRect(0,0,confettiCv.width,confettiCv.height); }
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
$("aboutBtn").addEventListener("click", () => { closeMenus(); openModal("aboutModal"); });
function openSettings(tab) {
  closeMenus();
  openModal("settingsModal"); ytckShown = false; applyYtckMask();
  if (tab) document.querySelector(`#settingsTabs .tab[data-stab="${tab}"]`)?.click();
}
$("settingsBtn").addEventListener("click", () => openSettings());
$("openOptionsBtn")?.addEventListener("click", () => openSettings());
// Tabs de Configuración (General / Conversión / IA / Anonimización / YouTube).
document.querySelectorAll("#settingsTabs .tab").forEach(tb => {
  tb.addEventListener("click", () => {
    document.querySelectorAll("#settingsTabs .tab").forEach(t => t.classList.toggle("active", t === tb));
    document.querySelectorAll("#settingsModal .stab-panel").forEach(p => p.classList.toggle("hidden", p.dataset.stabPanel !== tb.dataset.stab));
  });
});

// ---------- Cookies de YouTube (se guardan SOLO en este navegador, SOLO en esta sesión) ----------
// Defensa en profundidad: las cookies de YouTube son credenciales de sesión de Google.
// Por defecto NO se persisten en disco (localStorage); viven en sessionStorage y se
// borran al cerrar la pestaña. Se migra y limpia cualquier valor legado de localStorage.
const YTCK_STORE = "escriba_yt_cookies";
const ytckStore = (() => { try { return window.sessionStorage; } catch { return null; } })();
(function migrateYtCookies() {
  try {
    const legacy = localStorage.getItem(YTCK_STORE);
    if (legacy != null) {
      if (ytckStore && !ytckStore.getItem(YTCK_STORE)) ytckStore.setItem(YTCK_STORE, legacy);
      localStorage.removeItem(YTCK_STORE);   // dejar de persistir credenciales en disco
    }
  } catch {}
})();
let ytckShown = false;   // por seguridad arrancan OCULTAS (blur)
function getYtCookies() { try { return (ytckStore && ytckStore.getItem(YTCK_STORE)) || ""; } catch { return ""; } }
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
    try { if (ytckStore) { v ? ytckStore.setItem(YTCK_STORE, v) : ytckStore.removeItem(YTCK_STORE); } localStorage.removeItem(YTCK_STORE); } catch {}
    ytCookiesStatus(v ? t("settings.ytCookiesSaved") : "");
    toast(v ? t("settings.ytCookiesSaved") : t("settings.ytCookiesCleared"));
    ytckShown = false; applyYtckMask();   // re-ocultar tras guardar
  });
  $("clearYtCookiesBtn")?.addEventListener("click", () => {
    ta.value = ""; try { if (ytckStore) ytckStore.removeItem(YTCK_STORE); localStorage.removeItem(YTCK_STORE); } catch {}
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

// ---------- Asistente de selección de páginas: POR ARCHIVO (solo PDF) ----------
// Cada ítem guarda su propia selección en it.pages ("" = todas; "1-23" rango; "1,6,9" sueltas).
let _pagesItem = null;       // ítem que se está editando en el modal
let _pagesBtnEl = null;      // referencia directa al botón .pg-pick que se tocó
const _pgChips = [];         // páginas sueltas del modal abierto

const IC_PAGES = '<svg class="pg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>';

const PG_MAX = 10000;   // tope de páginas (espeja MAX_PAGES_SPEC del backend; evita rangos enormes)
function parsePagesSpec(spec) {
  // Devuelve {count} si la spec es válida (1-23 / 1:23 / 1,6,9 / combinaciones), o null.
  spec = (spec || "").replace(/\s+/g, "");
  if (!spec) return null;
  const set = new Set();
  for (const part of spec.split(",")) {
    if (!part) continue;
    const m = part.match(/^(\d{1,7})[-:](\d{1,7})$/);   // tope de dígitos: frena rangos astronómicos
    if (m) {
      const a = +m[1], b = +m[2];
      if (a < 1 || b < 1) return null;
      const lo = Math.min(a, b), hi = Math.max(a, b);
      if (hi - lo + 1 > PG_MAX) return null;            // rango demasiado grande
      for (let n = lo; n <= hi; n++) set.add(n);
    } else if (/^\d{1,7}$/.test(part) && +part >= 1) { set.add(+part); }
    else { return null; }
    if (set.size > PG_MAX) return null;                 // tope global
  }
  return set.size ? { count: set.size } : null;
}
const pagesCount = (spec) => { const r = parsePagesSpec(spec); return r ? r.count : 0; };
const isPdfItem = (it) => !it.isUrl && /\.pdf$/i.test(it.name || "");
const pagesBtnLabel = (spec) => spec || t("pages.pickAll");   // compacto: "2-4" / "1,6,9" / "Todas"

// El botoncito al lado del chip "En cola" (solo PDFs pendientes).
function pagesPickInnerHtml(it) {
  return `<button type="button" class="pg-pick" title="${escapeHtml(t("pages.label"))}">${IC_PAGES}<span>${escapeHtml(pagesBtnLabel(it.pages || ""))}</span></button>`;
}
function pagesPickHtml(it) {
  return (isPdfItem(it) && (it.status === "queued" || it.status === "error")) ? pagesPickInnerHtml(it) : "";
}
function mountPagesPick(root, it) {
  if (root.querySelector(".pg-pick")) return;
  const chip = root.querySelector(".chip"); if (!chip) return;
  chip.insertAdjacentHTML("beforebegin", pagesPickInnerHtml(it));
  root.querySelector(".pg-pick").addEventListener("click", (e) => { e.stopPropagation(); openPagesFor(it, e.currentTarget); });
}

const _pgMode = () => (document.querySelector('input[name="pgMode"]:checked') || {}).value || "all";
function _pgSetMode(mode) {
  document.querySelectorAll('input[name="pgMode"]').forEach(r => { r.checked = (r.value === mode); });
  // Los sub-controles quedan SIEMPRE visibles e invitan a usarlos; el modo se
  // activa solo al tocarlos (ver listeners). Atenuamos el que no está activo.
  $("pgRangeRow").classList.toggle("pg-dim", mode !== "range");
  $("pgSingleRow").classList.toggle("pg-dim", mode !== "single");
  _pgUpdateSummary();
}
function _pgRenderChips() {
  const box = $("pgChips");
  const startOf = (s) => parseInt(s, 10) || 0;   // ordena por la primera página
  box.innerHTML = _pgChips.slice().sort((a, b) => startOf(a) - startOf(b)).map(s =>
    `<span class="pg-chip">${escapeHtml(s)}<button type="button" data-c="${escapeHtml(s)}" title="${t("llm.remove")}">✕</button></span>`).join("");
  box.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    const i = _pgChips.indexOf(b.dataset.c); if (i >= 0) _pgChips.splice(i, 1);
    _pgRenderChips(); _pgUpdateSummary();
  }));
}
function _pgBuildSpec() {
  const m = _pgMode();
  if (m === "range") {
    let a = parseInt($("pgFrom").value, 10) || 1, b = parseInt($("pgTo").value, 10) || 1;
    a = Math.max(1, a); b = Math.max(1, b); if (a > b) { [a, b] = [b, a]; }
    return a === b ? String(a) : a + "-" + b;
  }
  if (m === "single") return _pgChips.join(",");   // mezcla sueltas y rangos: "1,2,5-67"
  return "";
}
function _pgCommit(spec) {
  // Guarda la selección EN VIVO en el ítem y refleja el badge al instante.
  // No depende del botón "Aplicar" (que en algunos navegadores no disparaba).
  if (!_pagesItem) return;
  _pagesItem.pages = spec;
  if (_pagesBtnEl) _pagesBtnEl.innerHTML = IC_PAGES + "<span>" + escapeHtml(pagesBtnLabel(spec)) + "</span>";
}
function _pgUpdateSummary() {
  const spec = _pgBuildSpec(), el = $("pgSummary");
  _pgCommit(spec);   // guardado en vivo
  if (!spec) { el.textContent = t("pages.summaryAll"); $("pgApply").disabled = false; return; }
  const n = pagesCount(spec);
  el.textContent = n ? t("pages.summaryN", { n }) : t("pages.summaryEmpty");
  $("pgApply").disabled = !n;
}
function _pgAddChip() {
  if (_pgMode() !== "single") _pgSetMode("single");   // tocar "Agregar" activa el modo sueltas/rangos
  const raw = ($("pgChipInput").value || "").trim().replace(/\s+/g, "");
  let chip = null;
  if (/^\d{1,7}$/.test(raw) && +raw >= 1) {
    chip = raw;                                        // página suelta: "7"
  } else {
    const m = raw.match(/^(\d{1,7})[-:](\d{1,7})$/);   // rango: "5-67" o "5:67"
    if (m && +m[1] >= 1 && +m[2] >= 1) {
      let a = +m[1], b = +m[2]; if (a > b) { [a, b] = [b, a]; }
      if (b - a + 1 <= PG_MAX) chip = a === b ? String(a) : a + "-" + b;   // rechaza rangos enormes
    }
  }
  if (chip && !_pgChips.includes(chip)) { _pgChips.push(chip); _pgRenderChips(); }
  _pgUpdateSummary();
  $("pgChipInput").value = ""; $("pgChipInput").focus();
}
function _pgSetTotal(n) {
  const el = $("pgTotal"); if (!el) return;
  if (n > 0) {
    el.textContent = t("pages.total", { n });
    ["pgFrom", "pgTo", "pgChipInput"].forEach(id => { const e = $(id); if (e) e.max = n; });
  } else { el.textContent = ""; }
}
async function _pgLoadCount(it) {
  if (it._pageCount != null) { _pgSetTotal(it._pageCount); return; }
  const el = $("pgTotal"); if (el) el.textContent = t("pages.totalLoading");
  try {
    const fd = new FormData(); fd.append("file", it.file);
    const r = await fetch("/api/pdf_pages", { method: "POST", body: fd });
    it._pageCount = (await r.json()).pages || 0;
  } catch { it._pageCount = 0; }
  if (_pagesItem === it) {   // el modal sigue abierto para este archivo
    _pgSetTotal(it._pageCount);   // solo muestra el total + fija el max; NO toca lo que el usuario eligió
  }
}
function openPagesFor(it, btnEl) {
  _pagesItem = it; _pagesBtnEl = btnEl || null; _pgChips.length = 0;
  const spec = it.pages || "";
  $("pgFrom").value = "1"; $("pgTo").value = it._pageCount > 0 ? it._pageCount : "1";
  _pgSetTotal(it._pageCount != null ? it._pageCount : 0);
  _pgLoadCount(it);
  if (!spec) { _pgSetMode("all"); }
  else if (/^\d+(-\d+)?$/.test(spec)) {
    const [a, b] = spec.split("-"); $("pgFrom").value = a; $("pgTo").value = b || a; _pgSetMode("range");
  } else {
    spec.split(",").forEach(tok => { tok = tok.trim(); if (tok && !_pgChips.includes(tok)) _pgChips.push(tok); });
    _pgRenderChips(); _pgSetMode("single");
  }
  openModal("pagesModal");
}

(function wirePagesModal() {
  if (!$("pgApply")) return;
  document.querySelectorAll('input[name="pgMode"]').forEach(r => r.addEventListener("change", () => _pgSetMode(r.value)));
  // A prueba de dummies: tocar los campos de un modo SELECCIONA ese modo solo.
  const useRange = () => { if (_pgMode() !== "range") _pgSetMode("range"); else _pgUpdateSummary(); };
  ["pgFrom", "pgTo"].forEach(id => {
    $(id).addEventListener("focus", useRange);
    $(id).addEventListener("input", useRange);
  });
  $("pgChipInput").addEventListener("focus", () => { if (_pgMode() !== "single") _pgSetMode("single"); });
  $("pgChipAdd").addEventListener("click", _pgAddChip);
  $("pgChipInput").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); _pgAddChip(); } });
  $("pgApply").addEventListener("click", () => {
    if (_pagesItem) {
      _pagesItem.pages = _pgBuildSpec();
      const label = pagesBtnLabel(_pagesItem.pages || "");
      // (1) Botón EXACTO que se tocó (referencia directa, sin querySelector): a prueba de balas.
      if (_pagesBtnEl) _pagesBtnEl.innerHTML = IC_PAGES + "<span>" + escapeHtml(label) + "</span>";
      // (2) Backstop por el camino de render (por si el nodo se hubiera recreado).
      const root = document.getElementById("it" + _pagesItem.id);
      if (root) updateItemNode(_pagesItem, root);
    }
    closeModal("pagesModal");
  });
})();

esEnhanceAll(document);   // dropdowns custom para todos los <select> estáticos
loadMe();
