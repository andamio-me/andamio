// Lo último que se vio de cada app: al volver, aparece al instante (y se pone al día solo).
// Pasar el mouse sobre una app la trae de antes, para que al abrirla ya esté.
import * as api from "./api";

const apps = new Map<string, { at: number; data: api.AppData }>();
const inflight = new Map<string, Promise<api.AppData>>();

export const cachedApp = (name: string): api.AppData | null => apps.get(name)?.data ?? null;

export function rememberApp(name: string, data: api.AppData) {
  apps.set(name, { at: Date.now(), data });
}

/** Trae la app si no se vio en los últimos 15 s (una sola vez aunque se pida varias). */
export function fetchApp(name: string, maxAge = 0): Promise<api.AppData> {
  const hit = apps.get(name);
  if (hit && Date.now() - hit.at < maxAge) return Promise.resolve(hit.data);
  const running = inflight.get(name);
  if (running) return running;
  const p = api.app(name).then((d) => {
    rememberApp(name, d);
    return d;
  }).finally(() => inflight.delete(name));
  inflight.set(name, p);
  return p;
}

export const prefetchApp = (name: string) => void fetchApp(name, 15_000).catch(() => {});
