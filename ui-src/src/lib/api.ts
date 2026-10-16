// Lo que entrega bin/andamio (/api/...). Los datos vienen de tus archivos y del servidor por SSH.

export type Live = {
  state: string;
  health: string;
  started: string;
  restarts: number;
  version: string;
  mem?: string;
  cpu?: string;
};

export type Cron = {
  name: string;
  schedule: string;
  command: string;
  next?: string; // "-" sin aplicar · "*" corriendo ahora · fecha en tu zona
  last?: { rc: number; start: number; secs: number } | null;
};

export type Deploy = {
  id: number; status: string; conclusion: string; title: string; sha: string; full?: string; created: string; url: string; app?: string;
  started?: string; updated?: string;
};

export type Change = {
  sha: string; short: string; at: number; author: string; subject: string; apps: string[];
  kind: "config" | "create" | "destroy" | "secrets" | "platform"; revertible: boolean; lines: string[]; files: number;
};
export type Settings = {
  domain: string; server: string; copy: string; timezone: string; local_timezone: string; tasks: number; timezones: string[];
  monitoring: string; backups: boolean; forge: string; alerts: { ntfy: boolean; telegram: boolean } | null; error: string;
  telegram_on: boolean; updatable: boolean; ntfy_url: string;
  sudo_minutes: number; sudo_choices: number[]; sudo_env: boolean; sudo_remembered: boolean;
};
export type Copy = { path: string; domain: string; current: boolean };
export type EnvCheck = { used: { key: string; where: string }[]; missing: { key: string; where: string }[]; have: string[]; error: string };
export type Suggest = {
  days: number; error: string;
  mem: { peak: number; limit: number; suggest: string | null; why: "up" | "down" | "" } | null;
  cpu: { p95: number; max: number; limit: number; suggest: string | null; why: "up" | "down" | "" } | null;
};
export type Timeline = {
  hours: [number, number | null][]; outages: { start: number; end: number; mins: number; ongoing: boolean }[];
  start: number; end: number; error: string;
};
export type CiFailure = {
  url: string; title: string; conclusion: string; failed: { job: string; steps: string[] }[];
  cause: string; hints: string[]; log: string[]; rejected: boolean; error?: string;
};
export type Service = { name: string; kind: "app" | "worker" | "postgres" | "redis"; status: string; mem: number | null; cpu: number | null };
export type Services = { services: Service[]; error: string };
export type CronRun = { rc: number; start: number; secs: number; output: string };
export type Cert = { host: string; ok: boolean; expires?: number; days?: number; issuer?: string; error?: string };
export type Availability = { apps: Record<string, { "24h": number | null; "7d": number | null }>; error: string };
export type SqlColumn = { name: string; type: string };
export type SqlTable = { schema: string; name: string; rows: number; exact: boolean; columns: SqlColumn[] };
export type SqlResult = { columns: string[]; rows: string[][]; error: string; count?: number; truncated?: boolean; ms?: number };
export type TgChat = { id: string; name: string; username: string; type: string };

export type Range = "1h" | "6h" | "24h" | "7d";
export type Point = [number, number];
export type Metrics = {
  range: Range; start: number; end: number; step: number; error: string;
  series: { cpu?: Point[]; mem?: Point[]; rx?: Point[]; tx?: Point[] };
};

export type Snapshot = { id: string; short: string; time: number | null; secs: number | null; size: number | null; added: number | null; files: number | null };
export type Backups = {
  enabled: boolean; error: string; configured?: boolean; result?: string; last?: number | null; next?: number | null;
  running?: boolean; listed?: boolean; listed_at?: number | null; snapshots?: Snapshot[];
  // /srv/andamio/archive: lo que guardan app destroy y app restore antes de tocar nada.
  archive?: { name: string; size: number; time: number }[]; archive_total?: number; archive_days?: number;
};

export type Platform = {
  backups: { configured: boolean; result: string; last: number | null; next: number | null; running: boolean };
  alerts: { ntfy: boolean; telegram: boolean };
};
export type Security = {
  at: number; ok: number; warn: number; fail: number;
  items: { status: "WARN" | "FAIL"; area: string; what: string; fix: string }[];
};

export type App = {
  name: string;
  url: string;
  host: string;
  path: string;      // varias apps en un repo: el back bajo el host del front (p. ej. /api)
  dir: string;       // su carpeta en el repo ("" = la raíz)
  context: string;   // "." = se construye desde la raíz del repo
  branch: string;    // la rama que despliega (main, production…)
  watch: string[];   // otras rutas que disparan su deploy
  workflow: string;
  access: "public" | "vpn";
  repo: string;
  port: number;
  health: string;
  mem: string;
  cpus: number;
  db: boolean;
  mysql: boolean;    // MariaDB (compatible con MySQL)
  redis: boolean;
  volumes: string[];
  domains: string[];
  cors: string[];
  worker: string;
  cron: Cron[];
  stopped: boolean;
  db_connections: number;   // límite de conexiones a su base (0 = sin límite)
  db_timeout: string;       // tiempo máximo por consulta ("0" = sin límite)
  live: Live | null;
  secrets?: string[];
  deploys?: Deploy[];
  timezone?: string;
};

export type Server = {
  uptime: number;
  load: number;
  cpus: number;
  mem_total: number;
  mem_used: number;
  disk_total: number;
  disk_used: number;
};

export type Meta = {
  lang: "es" | "en"; domain: string; server: string; user: string; copy: string; csrf: string;
  timezone: string; timezone_set: boolean; template: string; owner: string; dashboard_app: string;
};

// Una carpeta de un repo con varias apps: qué es (lenguaje, framework, papel) y si es una librería.
export type Folder = {
  dir: string; dockerfile: boolean; label: string; kind: string; framework: string; role: "api" | "web" | "site" | "worker" | "";
  lib: boolean; declared: boolean;
};
export type RepoItem = { repo: string; private: boolean; updated: string; description: string };
export type Preview = {
  repo: string; private: boolean; instance: string; blocked: boolean; name: string; taken: string[]; hosts: string[];
  error?: string; kind?: string; label?: string; start?: string; dockerfile?: string; has_dockerfile?: boolean;
  port?: string; findings?: { serious: boolean; msg: string; volume: boolean }[];
  env?: { key: string; where: string; required?: boolean; example?: string }[];
  mysql?: boolean;   // el código declara MySQL/MariaDB (un driver, DB_CONNECTION=mysql, Prisma con mysql)
  dir?: string; folders?: Folder[];
  siblings?: { name: string; host: string; path: string; dir: string }[];
  branch?: string;
};
export type CreateBody = {
  name: string; repo: string; host: string; port: string; mem: string; health: string; access: "vpn" | "public";
  db: boolean; mysql: boolean; redis: boolean; volume: string; start: string; precheck_ok: boolean;
  dir: string; context: string; path: string; branch: string;
  domain: string; dns_ok: boolean;   // un dominio propio (api.tuempresa.com), opcional
  secrets: { key: string; value: string }[];
};
export type AppsData = {
  domain: string; server: Server | null; error: string; apps: App[];
  platform: Platform | null; security: Security | null; backups_enabled: boolean;
};
export type AppData = { app: App; error: string; server: Server | null; domain: string };

export type SetValues = Partial<{
  mem: string; cpus: string; port: string; health: string; access: "public" | "vpn"; db_connections: string; db_timeout: string;
}>;
export type DataServices = {
  config: { postgres: Record<string, string>; redis: Record<string, string>; mariadb: Record<string, string> };
  defaults: { postgres: Record<string, string>; redis: Record<string, string>; mariadb: Record<string, string> };
  mariadb_needed: boolean;   // alguna app la usa (si no, está apagada)
  policies: string[];
  engines: string[];
  dragonfly_policies: string[];
  apps: Record<string, { db: boolean; mysql: boolean; redis: boolean; db_connections: number; db_timeout: string }>;
  live: null | {
    postgres: { up?: boolean; mem_used?: number; cpu?: number; version?: string; conns?: Record<string, number>;
      sizes?: Record<string, number>; apps?: Record<string, { role: string; db: string }> };
    redis: { up?: boolean; mem_used?: number; cpu?: number; engine?: string; version?: string; data_used?: number; keys?: number;
      evicted?: number; clients?: Record<string, number> };
    mariadb?: { up?: boolean; mem_used?: number; cpu?: number; version?: string; conns?: Record<string, number>;
      sizes?: Record<string, number>; apps?: Record<string, { role: string; db: string }> };
    server: { cpus: number; mem_total: number };
  };
  error: string;
};
export const dataServices = () => request<DataServices>("/api/data-services");
export type ListKind = "domain" | "cors" | "volume";
export type Action =
  | { action: "estado" }
  | { action: "backup-now" | "backup-list" | "alert-test" | "update-check" }
  | { action: "timezone"; timezone: string }
  | { action: "telegram"; token: string; chat: string }
  | { action: "telegram-off" }
  | { action: "ntfy"; ntfy: string }
  | { action: "revert"; app: string; commit: string }
  | { action: "rollback"; app: string; sha: string }
  | { action: "restore"; app: string; snapshot: string; confirm: string; understood: boolean }
  | { action: "destroy"; app: string; confirm: string; understood: boolean }
  | { action: "create"; create: CreateBody }
  | { action: "stop" | "start" | "retry" | "restart" | "deploy"; app: string }
  | { action: "cron-edit"; app: string; task: string; schedule?: string; command?: string }
  | { action: "set"; app: string; set: SetValues }
  | { action: "services"; service: "postgres" | "redis" | "mariadb"; set: Record<string, string> }
  | { action: "cron-run" | "cron-rm"; app: string; task: string }
  | { action: "cron-add"; app: string; schedule: string; command: string; task: string; timezone?: string }
  | { action: "secret-set"; app: string; key: string; value: string }
  | { action: "secret-rm"; app: string; key: string }
  | { action: "secret-import"; app: string; pairs: { key: string; value: string }[] }
  | { action: "source"; app: string; dir?: string; context?: "." | "-"; watch_add?: string; watch_rm?: string }
  | { action: `${ListKind}-add`; app: string; value: string; dns_ok?: boolean }
  | { action: `${ListKind}-rm`; app: string; value: string };

let csrf = "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly data: Record<string, unknown> = {}) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { credentials: "same-origin", cache: "no-store", ...init });
  const text = await r.text();
  let data: Record<string, unknown> = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text };
  }
  if (!r.ok) throw new ApiError(String(data.error ?? r.status), r.status, data);
  return data as T;
}

export async function meta(): Promise<Meta> {
  const m = await request<Meta>("/api/meta");
  csrf = m.csrf;
  return m;
}

export const apps = () => request<AppsData>("/api/apps");
export const dns = (domain: string) =>
  request<{ ok: boolean; ip?: string; found?: string[]; error?: string }>(`/api/dns?domain=${encodeURIComponent(domain)}`);
export const cronPreview = (schedule: string, tz: string) =>
  request<{ calendar?: string; next?: string; timezone?: string; error?: string }>(
    `/api/cron-preview?schedule=${encodeURIComponent(schedule)}&tz=${encodeURIComponent(tz)}`);
export const app = (name: string) => request<AppData>(`/api/app/${encodeURIComponent(name)}`);
export const deploys = () => request<{ deploys: Deploy[] }>("/api/deploys");
export const appDeploys = (app: string) => request<{ deploys: Deploy[] }>(`/api/deploys?app=${encodeURIComponent(app)}`);
export const metrics = (range: Range, app = "") =>
  request<Metrics>(`/api/metrics?range=${range}${app ? `&app=${encodeURIComponent(app)}` : ""}`);
export const backups = () => request<Backups>("/api/backups");
export const currentJob = () => request<{ id?: string; command?: string; action?: string; state?: string }>("/api/jobs/current");
export const names = () => request<{ apps: { name: string; url: string; stopped: boolean }[] }>("/api/names");
export const history = (app = "") => request<{ changes: Change[] }>(`/api/history${app ? `?app=${encodeURIComponent(app)}` : ""}`);
export const settings = () => request<Settings>("/api/settings");
export const copies = () => request<{ copies: Copy[] }>("/api/copies");
export const repos = () => request<{ repos: RepoItem[] }>("/api/repos");
export const createPreview = (repo: string, dir = "") =>
  request<Preview>(`/api/create/preview?repo=${encodeURIComponent(repo)}${dir ? `&dir=${encodeURIComponent(dir)}` : ""}`);

// Toda acción lleva la clave de sesión en una cabecera propia: otro sitio no puede enviarla.
function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Andamio-CSRF": csrf },
    body: JSON.stringify(body),
  });
}

export const sudoMinutes = (minutes: number) => post<{ ok: boolean }>("/api/sudo", { minutes });
export const sudoForget = () => post<{ ok: boolean }>("/api/sudo", { forget: true });
export const startJob = (a: Action) => post<{ id: string; command: string }>("/api/jobs", a);
export const sendPassword = (id: string, password: string) => post<{ ok: boolean }>(`/api/jobs/${id}/password`, { password });
export const cancelJob = (id: string) => post<{ ok: boolean }>(`/api/jobs/${id}/cancel`, {});
export const switchTo = (path: string) => post<{ url: string }>("/api/switch", { path });
export const envCheck = (app: string) => request<EnvCheck>(`/api/env-check?app=${encodeURIComponent(app)}`);
export const suggest = (app: string) => request<Suggest>(`/api/suggest?app=${encodeURIComponent(app)}`);
export const services = (app: string) => request<Services>(`/api/services?app=${encodeURIComponent(app)}`);
export const timeline = (app: string) => request<Timeline>(`/api/timeline?app=${encodeURIComponent(app)}`);
export const ciFailure = (app: string, run: number) =>
  request<CiFailure>(`/api/ci-failure?app=${encodeURIComponent(app)}&run=${run}`);
export const cronRuns = (app: string, task: string) =>
  request<{ runs: CronRun[] }>(`/api/cron-runs?app=${encodeURIComponent(app)}&task=${encodeURIComponent(task)}`);
export const certs = () => request<{ apps: Record<string, Cert[]>; at: number }>("/api/certs");
export type CiStep = { name: string; status: string; conclusion: string; started: string; completed: string };
export type CiJob = CiStep & { steps: CiStep[] };
export type DeployProgress = { run: Deploy | null; jobs: CiJob[]; error: string };
export const deployProgress = (app: string) => request<DeployProgress>(`/api/deploy-progress?app=${encodeURIComponent(app)}`);
export type Sparks = { sparks: Record<string, Point[]>; start: number; end: number; step: number; error: string };
export const sparks = () => request<Sparks>("/api/sparks");
export const availability = () => request<Availability>("/api/availability");
export type SqlEngine = "postgres" | "mysql";
export const sqlTables = (app: string, engine: SqlEngine = "postgres") =>
  request<{ tables: SqlTable[]; error: string }>(`/api/sql/tables?app=${encodeURIComponent(app)}&engine=${engine}`);
export const sql = (app: string, query: string, engine: SqlEngine = "postgres") => post<SqlResult>("/api/sql", { app, query, engine });
export const telegramCheck = (token: string) => post<{ bot?: string; name?: string; error?: string }>("/api/telegram/check", { token });
export const telegramChats = (token: string, wait = 0) => post<{ chats: TgChat[]; error: string }>("/api/telegram/chats", { token, wait });
