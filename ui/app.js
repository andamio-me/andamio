// Panel de andamio (fase 1: solo mirar). Los datos vienen de bin/andamio (/api/...), que los
// toma de tus archivos y del servidor por SSH. Todo dato se pone con textContent: nada de lo
// que llega (logs, nombres, comandos) se interpreta como HTML.
"use strict";

const T = {
  es: {
    refresh: "Actualizar", updated: "actualizado", ago: (s) => `hace ${s}`, now: "recién",
    loading: "Cargando…", server: "Servidor", uptime: "Encendido", load: "Carga", ram: "RAM", disk: "Disco",
    apps: "Apps", app: "App", url: "URL", access: "Acceso", status: "Estado", using: "En uso", version: "Versión",
    tasks: "Tareas", noApps: "Todavía no tienes apps. Crea una: andamio app create <nombre> --repo dueño/repo",
    public: "pública", vpn: "VPN", running: "corriendo", stopped: "detenida", notDeployed: "sin desplegar",
    starting: "arrancando", unhealthy: "con fallas", restarts: (n) => `${n} reinicios`, started: "arrancó",
    back: "← Tus apps", config: "Configuración", live: "Ahora", repo: "Repo", port: "Puerto", health: "Salud",
    limits: "Límites", data: "Datos", folders: "Carpetas", domains: "Dominios", cors: "CORS", worker: "Worker",
    secrets: "Secretos", secretsNote: "solo los nombres", none: "ninguno",
    schedule: "Horario", command: "Comando", next: "Próxima", last: "Última", notApplied: "sin aplicar",
    runningNow: "corriendo ahora", notRun: "todavía no ha corrido", code: (n) => `código ${n}`,
    noTasks: "Sin tareas programadas. Agrega una: andamio app cron add <app> \"0 3 * * *\" \"python limpiar.py\"",
    deploys: "Deploys", noDeploys: "Sin deploys (o no pude leerlos de GitHub).", inProgress: "en curso",
    logs: "Logs en vivo", pause: "Pausar", resume: "Seguir", clear: "Limpiar", connecting: "Conectando…",
    ended: "— el contenedor dejó de emitir logs —", lost: "— se cortó la conexión; se reintenta sola —",
    serverErr: "Sin datos del servidor", noSuch: "No existe esa app en esta copia.",
    copy: "copia", cpu: "CPU", ofLimit: (a, b) => `${a} de ${b}`, restartsLabel: "Reinicios",
  },
  en: {
    refresh: "Refresh", updated: "updated", ago: (s) => `${s} ago`, now: "just now",
    loading: "Loading…", server: "Server", uptime: "Up", load: "Load", ram: "RAM", disk: "Disk",
    apps: "Apps", app: "App", url: "URL", access: "Access", status: "Status", using: "In use", version: "Version",
    tasks: "Tasks", noApps: "No apps yet. Create one: andamio app create <name> --repo owner/repo",
    public: "public", vpn: "VPN", running: "running", stopped: "stopped", notDeployed: "not deployed",
    starting: "starting", unhealthy: "unhealthy", restarts: (n) => `${n} restarts`, started: "started",
    back: "← Your apps", config: "Configuration", live: "Now", repo: "Repo", port: "Port", health: "Health",
    limits: "Limits", data: "Data", folders: "Folders", domains: "Domains", cors: "CORS", worker: "Worker",
    secrets: "Secrets", secretsNote: "names only", none: "none",
    schedule: "Schedule", command: "Command", next: "Next", last: "Last", notApplied: "not applied",
    runningNow: "running now", notRun: "not run yet", code: (n) => `exit code ${n}`,
    noTasks: "No scheduled tasks. Add one: andamio app cron add <app> \"0 3 * * *\" \"python cleanup.py\"",
    deploys: "Deploys", noDeploys: "No deploys (or couldn't read them from GitHub).", inProgress: "in progress",
    logs: "Live logs", pause: "Pause", resume: "Resume", clear: "Clear", connecting: "Connecting…",
    ended: "— the container stopped emitting logs —", lost: "— connection lost; it retries by itself —",
    serverErr: "No data from the server", noSuch: "No such app in this copy.",
    copy: "copy", cpu: "CPU", ofLimit: (a, b) => `${a} of ${b}`, restartsLabel: "Restarts",
  },
};
let t = T.es;
let meta = {};
let lastLoad = 0;
let logSource = null;
let timer = null;
const $ = (id) => document.getElementById(id);

// el("tag", {class, href, ...}, hijos...): crea nodos; los textos van como texto, nunca como HTML.
function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const k of kids.flat(Infinity)) if (k !== null && k !== undefined && k !== false) n.append(k instanceof Node ? k : String(k));
  return n;
}

// Reemplaza el contenido de un nodo; lo vacío (un aviso que no hace falta) no se pinta.
const fill = (node, ...kids) => node.replaceChildren(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
// "256m" (app.yml) y "5MiB" (servidor) → "256 MiB", "5 MiB": las mismas unidades.
const mib = (v) => String(v || "").replace(/^(\d+(?:\.\d+)?)\s*([mg])$/i, (_, n, u) => `${n} ${u.toLowerCase() === "g" ? "GiB" : "MiB"}`)
  .replace(/^(\d+(?:\.\d+)?)([KMG]iB)$/, "$1 $2");

async function api(path) {
  const r = await fetch(path, { credentials: "same-origin", cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

function agoText(seconds) {
  if (seconds < 45) return t.now;
  const units = [[86400, "d"], [3600, "h"], [60, "min"]];
  for (const [n, u] of units) if (seconds >= n) return t.ago(`${Math.floor(seconds / n)} ${u}`);
  return t.ago(`${Math.round(seconds)} s`);
}
const since = (iso) => (Date.now() - new Date(iso).getTime()) / 1000;
function bytes(n) {
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n < 10 && i > 1 ? 1 : 0)} ${u[i]}`;
}
function uptime(s) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
  return d ? `${d} d ${h} h` : `${h} h ${Math.floor((s % 3600) / 60)} min`;
}
function bar(used, total) {
  const pct = total ? Math.min(100, (used / total) * 100) : 0;
  const fill = el("i");
  fill.style.width = `${pct.toFixed(1)}%`;   // por element.style: la CSP no deja atributos style
  return el("div", { class: `bar${pct >= 90 ? " full" : pct >= 80 ? " hot" : ""}`, role: "img",
                     "aria-label": `${Math.round(pct)}%` }, fill);
}

// Estado de una app: punto de color + texto.
function status(a) {
  const lv = a.live;
  let cls = "", text;
  if (a.stopped) text = t.stopped;
  else if (!lv) text = t.notDeployed;
  else if (lv.state === "running") {
    cls = lv.health === "unhealthy" ? "bad" : lv.health === "starting" ? "warn" : "ok";
    text = lv.health === "unhealthy" ? t.unhealthy : lv.health === "starting" ? t.starting : t.running;
  } else { cls = "bad"; text = lv.state; }
  return el("span", { class: "status" }, el("span", { class: `dot ${cls}` }), text);
}

function banner(msg) { return msg ? el("div", { class: "banner", role: "alert" }, `${t.serverErr}: ${msg}`) : null; }

function serverRow(s) {
  if (!s) return null;
  const metric = (k, v, extra) => el("div", { class: "metric" }, el("span", { class: "k" }, k), el("span", { class: "v" }, v), extra);
  return el("section", { class: "server", "aria-label": t.server },
    metric(t.uptime, uptime(s.uptime)),
    metric(t.load, `${s.load.toFixed(2)} / ${s.cpus} ${t.cpu}`),
    metric(t.ram, t.ofLimit(bytes(s.mem_used), bytes(s.mem_total)), bar(s.mem_used, s.mem_total)),
    metric(t.disk, t.ofLimit(bytes(s.disk_used), bytes(s.disk_total)), bar(s.disk_used, s.disk_total)));
}

// ---------- vista: tus apps ----------
async function showApps() {
  const view = $("view");
  view.replaceChildren(el("p", { class: "loading" }, t.loading));
  const data = await api("/api/apps");
  lastLoad = Date.now();
  const rows = data.apps.map((a) => el("tr", { onclick: (e) => { if (!e.target.closest("a")) location.hash = `#/app/${a.name}`; } },
    el("td", {}, el("a", { class: "name", href: `#/app/${a.name}` }, a.name)),
    el("td", {}, status(a), a.live && a.live.restarts ? el("div", { class: "muted" }, t.restarts(a.live.restarts)) : null),
    el("td", {}, el("a", { href: a.url, target: "_blank", rel: "noopener noreferrer" }, a.url.replace("https://", ""))),
    el("td", {}, el("span", { class: `tag${a.access === "public" ? " public" : ""}` }, a.access === "public" ? t.public : t.vpn)),
    el("td", { class: "num" }, a.live && a.live.mem ? t.ofLimit(mib(a.live.mem), mib(a.mem)) : el("span", { class: "muted" }, mib(a.mem))),
    el("td", { class: "num mono" }, a.live ? a.live.version : "—"),
    el("td", { class: "num" }, a.cron.length || el("span", { class: "muted" }, "—"))));
  fill(view,
    banner(data.error),
    el("h1", {}, data.domain),
    serverRow(data.server),
    el("h2", {}, t.apps),
    rows.length
      ? el("table", { class: "apps" },
          el("thead", {}, el("tr", {}, [t.app, t.status, t.url, t.access, t.ram, t.version, t.tasks].map((h) => el("th", { scope: "col" }, h)))),
          el("tbody", {}, rows))
      : el("p", { class: "empty" }, t.noApps));
}

// ---------- vista: una app ----------
function kv(pairs) {
  return el("dl", { class: "kv" }, pairs.filter(([, v]) => v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
}

function cronList(a) {
  if (!a.cron.length) return el("p", { class: "empty" }, t.noTasks);
  return el("ul", { class: "list" }, a.cron.map((c) => {
    const next = c.next === "-" ? t.notApplied : c.next === "*" ? t.runningNow : c.next || "?";
    let last = el("span", { class: "muted" }, t.notRun);
    if (c.last) {
      const ok = c.last.rc === 0;
      last = el("span", { class: "status" }, el("span", { class: `dot ${ok ? "ok" : "bad"}` }),
        `${ok ? "✓" : t.code(c.last.rc)} · ${agoText(Date.now() / 1000 - c.last.start)} · ${c.last.secs} s`);
    }
    return el("li", {},
      el("div", { class: "grow" }, el("strong", {}, c.name), " ", el("code", {}, c.schedule), el("div", { class: "mono muted" }, c.command)),
      el("div", {}, el("div", {}, el("span", { class: "muted" }, `${t.next}: `), next), el("div", {}, el("span", { class: "muted" }, `${t.last}: `), last)));
  }));
}

function deployList(a) {
  if (!a.deploys.length) return el("p", { class: "empty" }, t.noDeploys);
  return el("ul", { class: "list" }, a.deploys.map((d) => {
    const done = d.status === "completed";
    const cls = !done ? "warn" : d.conclusion === "success" ? "ok" : "bad";
    const word = !done ? t.inProgress : d.conclusion === "success" ? "✓" : `✗ ${d.conclusion}`;
    return el("li", {},
      el("span", { class: "status" }, el("span", { class: `dot ${cls}` }), word),
      el("span", { class: "grow" }, el("a", { href: d.url, target: "_blank", rel: "noopener noreferrer" }, d.title)),
      el("code", { class: "muted" }, d.sha),
      el("span", { class: "muted num" }, agoText(since(d.created))));
  }));
}

function logPanel(name) {
  const pre = el("pre", { class: "logs", tabindex: "0", "aria-label": t.logs }, el("span", { class: "sys" }, t.connecting));
  let paused = false;
  const pause = el("button", { type: "button", class: "btn", onclick: () => { paused = !paused; pause.textContent = paused ? t.resume : t.pause; } }, t.pause);
  const clear = el("button", { type: "button", class: "btn", onclick: () => pre.replaceChildren() }, t.clear);
  closeLogs();
  logSource = new EventSource(`/api/logs/${encodeURIComponent(name)}`);
  let first = true;
  const add = (text, sys) => {
    if (first) { pre.replaceChildren(); first = false; }
    pre.append(sys ? el("span", { class: "sys" }, text + "\n") : text + "\n");
    while (pre.childNodes.length > 3000) pre.firstChild.remove();
    if (!paused) pre.scrollTop = pre.scrollHeight;
  };
  logSource.onmessage = (e) => add(JSON.parse(e.data));
  logSource.addEventListener("end", () => { add(t.ended, true); closeLogs(); });
  logSource.onerror = () => add(t.lost, true);
  return el("section", {}, el("div", { class: "logbar" }, el("h2", {}, t.logs), el("span", { class: "spacer" }), pause, clear), pre);
}
function closeLogs() { if (logSource) { logSource.close(); logSource = null; } }

async function showApp(name) {
  const view = $("view");
  view.replaceChildren(el("a", { class: "back", href: "#/" }, t.back), el("p", { class: "loading" }, t.loading));
  let data;
  try { data = await api(`/api/app/${encodeURIComponent(name)}`); }
  catch (e) { view.replaceChildren(el("a", { class: "back", href: "#/" }, t.back), el("p", {}, t.noSuch)); return; }
  lastLoad = Date.now();
  const a = data.app, lv = a.live;
  const liveBits = lv ? [
    [t.started, agoText(since(lv.started))],
    [t.version, el("code", {}, lv.version)],
    [t.ram, lv.mem ? t.ofLimit(mib(lv.mem), mib(a.mem)) : mib(a.mem)],
    [t.cpu, lv.cpu ? t.ofLimit(lv.cpu, `${a.cpus} ${t.cpu}`) : `${a.cpus} ${t.cpu}`],
    [t.restartsLabel, lv.restarts ? String(lv.restarts) : null],
  ] : [];
  fill(view,
    el("a", { class: "back", href: "#/" }, t.back),
    banner(data.error),
    el("div", { class: "head" }, el("h1", {}, a.name), status(a),
      el("a", { href: a.url, target: "_blank", rel: "noopener noreferrer" }, a.url.replace("https://", "")),
      el("span", { class: `tag${a.access === "public" ? " public" : ""}` }, a.access === "public" ? t.public : t.vpn)),
    el("div", { class: "cols" },
      el("section", {}, el("h2", {}, t.config), kv([
        [t.repo, a.repo], [t.port, a.port], [t.health, a.health], [t.limits, `${mib(a.mem)} · ${a.cpus} ${t.cpu}`],
        [t.data, [a.db ? "PostgreSQL" : "", a.redis ? "Redis" : ""].filter(Boolean).join(", ")],
        [t.folders, a.volumes.join(", ")], [t.domains, a.domains.join(", ")], [t.cors, a.cors.join(", ")],
        [t.worker, a.worker ? el("code", {}, a.worker) : ""],
        [t.secrets, a.secrets.length ? el("div", { class: "tags" }, a.secrets.map((s) => el("code", { class: "tag" }, s))) : el("span", { class: "muted" }, t.none)],
      ])),
      el("section", {}, el("h2", {}, t.live), lv ? kv(liveBits) : el("p", { class: "empty" }, a.stopped ? t.stopped : t.notDeployed))),
    el("h2", {}, t.tasks, " ", el("span", { class: "tz" }, a.timezone)), cronList(a),
    el("h2", {}, t.deploys), deployList(a),
    logPanel(a.name));
}

// ---------- navegación ----------
async function route() {
  closeLogs();
  const m = location.hash.match(/^#\/app\/([a-z0-9-]+)$/);
  try { await (m ? showApp(m[1]) : showApps()); }
  catch (e) { $("view").replaceChildren(banner(String(e.message || e))); }
  stamp();
}
function stamp() { $("stamp").textContent = lastLoad ? `${t.updated} ${agoText((Date.now() - lastLoad) / 1000)}` : ""; }

async function main() {
  meta = await api("/api/meta");
  t = T[meta.lang] || T.en;
  document.documentElement.lang = meta.lang;
  document.title = `andamio · ${meta.domain}`;
  $("where").textContent = `${meta.domain} · ${meta.server}`;
  $("refresh").textContent = t.refresh;
  $("refresh").addEventListener("click", route);
  window.addEventListener("hashchange", route);
  setInterval(stamp, 15000);
  // La lista se pone al día sola cada 30 s mientras la miras (el detalle tiene sus logs en vivo).
  timer = setInterval(() => { if (!document.hidden && !location.hash.startsWith("#/app/")) route(); }, 30000);
  route();
}
main().catch((e) => $("view").replaceChildren(el("div", { class: "banner" }, String(e.message || e))));
