import { t } from "./i18n.svelte";

export function ago(seconds: number): string {
  if (seconds < 45) return t().now;
  for (const [n, u] of [[86400, "d"], [3600, "h"], [60, "min"]] as const) {
    if (seconds >= n) return t().ago(`${Math.floor(seconds / n)} ${u}`);
  }
  return t().ago(`${Math.round(seconds)} s`);
}

export const since = (iso: string) => (Date.now() - new Date(iso).getTime()) / 1000;

export function bytes(n: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  // Un decimal en valores chicos con fracción (0.4 B/s, 1.5 KB): si no, todo bajo 1 se ve "0".
  return `${n.toFixed(n < 10 && (i > 1 || n % 1 !== 0) ? 1 : 0)} ${units[i]}`;
}

export function uptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  return d ? `${d} d ${h} h` : `${h} h ${Math.floor((s % 3600) / 60)} min`;
}

/** "256m" (app.yml) y "5MiB" (servidor) → "256 MiB", "5 MiB": las mismas unidades. */
export function mib(v: string | undefined): string {
  const s = String(v ?? "");
  const conf = s.match(/^(\d+(?:\.\d+)?)\s*([mg])$/i);
  if (conf) return `${conf[1]} ${conf[2]!.toLowerCase() === "g" ? "GiB" : "MiB"}`;
  return s.replace(/^(\d+(?:\.\d+)?)([KMG]iB)$/, "$1 $2");
}

export type Tone = "ok" | "warn" | "bad" | "";

/** Estado de una app: tono del punto y texto. */
export function status(a: { stopped: boolean; live: { state: string; health: string } | null }): { tone: Tone; text: string } {
  const s = t();
  if (a.stopped) return { tone: "", text: s.stopped };
  if (!a.live) return { tone: "", text: s.notDeployed };
  if (a.live.state !== "running") return { tone: "bad", text: a.live.state };
  if (a.live.health === "unhealthy") return { tone: "bad", text: s.unhealthy };
  if (a.live.health === "starting") return { tone: "warn", text: s.starting };
  return { tone: "ok", text: s.running };
}

/** Para algo que viene: "en 3 h". */
export function until(epoch: number): string {
  const s = Math.max(0, epoch - Date.now() / 1000);
  for (const [n, u] of [[86400, "d"], [3600, "h"], [60, "min"]] as const) {
    if (s >= n) return t().inTime(`${Math.floor(s / n)} ${u}`);
  }
  return t().inTime("1 min");
}
