/**
 * Una línea de log, entendida: su hora (la de Docker), su nivel y sus partes para pintarla.
 *
 * El nivel sale, en orden, de: el formato de NestJS ("[Nest] 1 - fecha  LOG [Contexto] …"), una
 * línea JSON (pino, winston: "level", o "severity"), "level=info" (logfmt), una palabra en
 * mayúsculas al principio (INFO, WARN, ERROR…) y, si nada de eso, palabras como "error" o
 * "warning" en el texto. Los colores ANSI que manda el programa se respetan (solo colores y
 * negrita: cada parte es texto, nunca HTML).
 */
export type Level = "error" | "warn" | "info" | "debug" | "";
export type Seg = { s: string; c?: string };
export type LogLine = { text: string; ts: number | null; level: Level; segs: Seg[]; cont?: boolean };

const TS = /^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) /;
// eslint-disable-next-line no-control-regex
const ESC = /\u001b\[([0-9;?]*)([ -/]*[@-~])/g;
const WORD: Record<string, Level> = {
  fatal: "error", critical: "error", crit: "error", error: "error", err: "error", panic: "error", emerg: "error", alert: "error",
  warning: "warn", warn: "warn", info: "info", log: "info", notice: "info", debug: "debug", verbose: "debug", trace: "debug",
};
const NEST = /^\[Nest\]\s+\d+\s+-\s+.*?\s+(LOG|ERROR|WARN|DEBUG|VERBOSE|FATAL)\s+(?:\[([^\]]+)\]\s*)?/;
const TOKEN = /(?:^|[\s[|(])(FATAL|CRITICAL|ERROR|ERR|WARNING|WARN|INFO|LOG|NOTICE|DEBUG|TRACE|VERBOSE)(?=[\s\]:|)]|$)/;
// Al principio, en minúsculas (winston: "info: …", "[warn] …").
const LEAD = /^\s*\[?(fatal|error|warn|warning|info|debug|trace|notice)\]?[:\s]/i;
const KV = /\b(?:level|lvl|severity)[=:]\s*"?([A-Za-z]+)"?/;
const ERRORS = /\b(error|errors|exception|fatal|traceback|panic|critical|failed|failure)\b|\b5\d\d\b/i;
const WARNS = /\b(warn|warning|deprecat\w*)\b/i;
// La continuación de un error (la pila): hereda su nivel.
const CONT = /^\s+(at\s|\.\.\.|File\s|\^|[|│])|^\s{4,}\S|^(Caused by|During handling)/;
const COLORS = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"];
const PINO: [number, Level][] = [[50, "error"], [40, "warn"], [30, "info"], [0, "debug"]];

/** Los colores ANSI (SGR) a partes con clase; el resto de las secuencias se descarta. */
function ansi(raw: string): Seg[] {
  const out: Seg[] = [];
  let fg = "", bold = false, dim = false, i = 0;
  const push = (s: string) => {
    if (!s) return;
    const c = [fg && `a-${fg}`, bold && "a-b", dim && "a-d"].filter(Boolean).join(" ");
    out.push(c ? { s, c } : { s });
  };
  for (const m of raw.matchAll(ESC)) {
    push(raw.slice(i, m.index));
    i = m.index! + m[0].length;
    if (m[2] !== "m") continue;
    const codes = (m[1] || "0").split(";").map(Number);
    for (let k = 0; k < codes.length; k++) {
      const n = codes[k]!;
      if (n === 0) { fg = ""; bold = false; dim = false; }
      else if (n === 1) bold = true;
      else if (n === 2) dim = true;
      else if (n === 22) { bold = false; dim = false; }
      else if (n === 39) fg = "";
      else if (n >= 30 && n <= 37) fg = COLORS[n - 30]!;
      else if (n >= 90 && n <= 97) fg = COLORS[n - 90]!;
      else if (n === 38 || n === 48) k += codes[k + 1] === 5 ? 2 : 4;   // 256 colores o RGB: se ignoran
    }
  }
  push(raw.slice(i));
  return out;
}

function fromJson(text: string): { level: Level; segs: Seg[] } | null {
  if (!text.startsWith("{")) return null;
  let o: Record<string, unknown>;
  try {
    o = JSON.parse(text);
  } catch {
    return null;
  }
  if (!o || typeof o !== "object") return null;
  const lv = o.level ?? o.severity ?? o.lvl;
  const level: Level = typeof lv === "number" ? PINO.find(([n]) => lv >= n)![1]
    : typeof lv === "string" ? WORD[lv.toLowerCase()] ?? "" : "";
  const msg = o.msg ?? o.message;
  if (typeof msg !== "string") return { level, segs: [{ s: text }] };
  const rest = Object.fromEntries(Object.entries(o).filter(([k]) =>
    !["level", "severity", "lvl", "msg", "message", "time", "timestamp", "pid", "hostname", "v"].includes(k)));
  const extra = Object.keys(rest).length ? JSON.stringify(rest) : "";
  return { level, segs: extra ? [{ s: msg }, { s: "  " + extra, c: "a-d" }] : [{ s: msg }] };
}

export function parseLog(raw: string, prev?: LogLine): LogLine {
  let ts: number | null = null;
  const m = TS.exec(raw);
  if (m) {
    ts = Date.parse(m[1]!);
    raw = raw.slice(m[0].length);
  }
  let segs = ansi(raw);
  const text = segs.map((x) => x.s).join("");
  let level: Level = "";

  const nest = NEST.exec(text);
  const json = nest ? null : fromJson(text);
  if (nest) {
    // NestJS: el prefijo repite la hora (ya está a la izquierda) y el nivel va de etiqueta.
    level = WORD[nest[1]!.toLowerCase()]!;
    segs = [...(nest[2] ? [{ s: `[${nest[2]}] `, c: "ctx" }] : []), { s: text.slice(nest[0].length) }];
  } else if (json) {
    ({ level, segs } = json);
  } else {
    const kv = KV.exec(text);
    const tok = TOKEN.exec(text.slice(0, 60));
    level = (kv && WORD[kv[1]!.toLowerCase()]) || (tok && WORD[tok[1]!.toLowerCase()]) || WORD[LEAD.exec(text)?.[1]?.toLowerCase() ?? ""] || "";
  }
  if (!level && prev && (prev.level === "error" || prev.level === "warn") && CONT.test(text)) {
    return { text, ts, level: prev.level, segs, cont: true };
  }
  if (!level) level = ERRORS.test(text) ? "error" : WARNS.test(text) ? "warn" : "";
  return { text, ts, level, segs };
}
