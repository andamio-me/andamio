// La acción en curso del panel: una a la vez, como en tu terminal. Se muestra en la terminal
// de la página: el comando con su $, la salida en vivo y, si hace falta, la contraseña de sudo.
import { type Action, ApiError, cancelJob, sendPassword, startJob } from "./api";

export type Phase = "armed" | "starting" | "password" | "running" | "done";
export type Line = { kind: "cmd" | "ok" | "warn" | "bad" | "step" | "out" | "stage"; text: string };

/** Como shlex.quote de Python: el comando que se muestra es el mismo que corre el servidor. */
export function shQuote(s: string): string {
  if (s && /^[\w@%+=:,./-]+$/.test(s)) return s;
  return `'${s.replaceAll("'", `'"'"'`)}'`;
}

/** El comando de la CLI que corre una acción (el servidor arma el mismo). El valor de un
 *  secreto nunca va en el comando: entra por stdin. */
export function commandFor(a: Action): string {
  const q = shQuote;
  switch (a.action) {
    case "estado": return "andamio estado";
    case "backup-now": return "andamio backups now";
    case "backup-list": return "andamio backups list";
    case "alert-test": return "andamio alertas prueba";
    case "telegram": return `andamio telegram --chat ${a.chat} --token-stdin`;
    case "telegram-off": return "andamio telegram desactivar";
    case "ntfy": return `andamio alertas --ntfy ${q(a.ntfy)}`;
    case "update-check": return "andamio update --check";
    case "timezone": return `andamio zona ${q(a.timezone)}`;
    case "services":
      return [`andamio servicios ${a.service}`, ...Object.entries(a.set).map(([k, v]) => `--${k.replace("_", "-")} ${q(v)}`)].join(" ");
    case "revert": return `andamio app revert ${a.app} ${a.commit}`;
    case "rollback": return `andamio app rollback ${a.app} ${a.sha}`;
    case "restore": return `andamio app restore ${a.app} ${a.snapshot}`;
    case "destroy": return `andamio app destroy ${a.app}`;
    case "create": {
      const c = a.create;
      const parts = ["andamio app create", c.name, c.repo && `--repo ${q(c.repo)}`, `--host ${q(c.host || c.name)}`,
        `--port ${c.port}`, `--mem ${c.mem}`, c.health && `--health ${q(c.health)}`,
        c.branch && c.branch !== "main" && `--branch ${q(c.branch)}`, c.domain && `--domain ${q(c.domain)}`, c.dir && `--dir ${q(c.dir)}`, c.dir && c.context && "--context .", c.path && `--path ${q(c.path)}`, c.access === "public" && "--public",
        c.db && "--db", c.mysql && "--mysql", c.redis && "--redis", c.volume && `--volume ${q(c.volume)}`, c.secrets.length && "--env-file -"];
      return parts.filter(Boolean).join(" ");
    }
    case "cron-run": return `andamio app cron run ${a.app} ${q(a.task)}`;
    case "cron-edit":
      return `andamio app cron edit ${a.app} ${q(a.task)}${a.schedule ? ` --schedule ${q(a.schedule)}` : ""}${a.command ? ` --command ${q(a.command)}` : ""}`;
    case "cron-rm": return `andamio app cron rm ${a.app} ${q(a.task)}`;
    case "cron-add":
      return `andamio app cron add ${a.app} ${q(a.schedule)} ${q(a.command)}${a.task ? ` --name ${q(a.task)}` : ""}`;
    case "secret-set": return `andamio app secret set ${a.app} ${q(a.key)}`;
    case "secret-rm": return `andamio app secret rm ${a.app} ${q(a.key)}`;
    case "secret-import": return `andamio app secret import ${a.app} -`;
    case "source": return ["andamio app source", a.app, a.dir && `--dir ${q(a.dir)}`, a.context && `--context ${a.context}`,
      a.watch_add && `--watch-add ${q(a.watch_add)}`, a.watch_rm && `--watch-rm ${q(a.watch_rm)}`].filter(Boolean).join(" ");
    case "set": break;
    default: {
      if ("value" in a) {
        const [kind, op] = a.action.split("-");
        return `andamio app ${kind} ${op} ${a.app} ${q(a.value)}`;
      }
      return `andamio app ${a.action} ${a.app}`;
    }
  }
  const s = a.set;
  const flags = [
    s.mem && `--mem ${s.mem}`,
    s.cpus && `--cpus ${s.cpus}`,
    s.port && `--port ${s.port}`,
    s.health && `--health ${s.health}`,
    s.access && `--${s.access}`,
    s.db_connections && `--db-connections ${s.db_connections}`,
    s.db_timeout && `--db-timeout ${s.db_timeout}`,
  ].filter(Boolean);
  return `andamio app set ${a.app} ${flags.join(" ")}`;
}

function classify(text: string): Line {
  const s = text.trimStart();
  // Las etapas de una acción larga (::stage <clave>): el panel las muestra como progreso.
  if (s.startsWith("::stage ")) return { kind: "stage", text: s.slice(8).trim() };
  if (s.startsWith("$ ")) return { kind: "cmd", text: s.slice(2) };
  if (s.startsWith("✓")) return { kind: "ok", text };
  if (s.startsWith("✗") || s.startsWith("fatal")) return { kind: "bad", text };
  if (s.startsWith("!") || s.startsWith("⏸")) return { kind: "warn", text };
  if (s.startsWith("==>")) return { kind: "step", text: s.slice(4) };
  return { kind: "out", text };
}

/** Quien quiera enterarse de cada acción que termina (los avisos). */
const finished: ((command: string, ok: boolean, rc: number) => void)[] = [];
export const onFinished = (f: (command: string, ok: boolean, rc: number) => void) => void finished.push(f);

// Acciones largas o delicadas: la terminal va al centro, sobre la página bloqueada, hasta que
// terminan (no se puede navegar ni lanzar otra cosa a medias). Las cortas van abajo.
const CRITICAL = new Set(["create", "destroy", "restore", "rollback", "deploy", "revert", "telegram", "telegram-off", "ntfy", "timezone", "backup-now"]);

class Job {
  phase = $state<Phase | null>(null);
  kind = $state("");
  /** Minimizada: una pastilla abajo a la derecha (sigue corriendo; avisa al terminar). */
  minimized = $state(false);
  startedAt = $state(0);
  /** Cada vez que tocas un botón bloqueado: la pastilla o la terminal lo explican. */
  nudges = $state(0);
  action = $state<Action | null>(null);
  command = $state("");
  lines = $state<Line[]>([]);
  /** Cuándo empezó cada etapa (::stage), para mostrar cuánto tardó. */
  stageAt = $state<Record<string, number>>({});
  endedAt = $state(0);
  /** Las etapas vistas, en orden. */
  get stages(): string[] { return this.lines.filter((l) => l.kind === "stage").map((l) => l.text); }
  prompt = $state("");
  rc = $state<number | null>(null);
  id = "";
  private source: EventSource | null = null;
  onDone: ((ok: boolean) => void) | null = null;

  get open() {
    return this.phase !== null;
  }
  get busy() {
    return this.phase === "starting" || this.phase === "password" || this.phase === "running";
  }
  /** Hay una acción preparada o corriendo: ninguna otra se puede lanzar (ni reemplazarla). */
  get locked() {
    return this.phase !== null && this.phase !== "done";
  }
  /** La acción es larga o delicada: la página queda bloqueada hasta que termina (o la minimizas). */
  get critical() {
    return this.phase !== null && CRITICAL.has(this.kind);
  }
  /** La app sobre la que corre (para avisarlo en su página), si es de una app. */
  get app(): string {
    const a = this.action as { app?: string } | null;
    return a?.app ?? this.command.match(/^andamio app [a-z-]+ ([a-z0-9-]+)/)?.[1] ?? "";
  }

  minimize() {
    if (this.busy) this.minimized = true;
  }
  expand() {
    this.minimized = false;
  }
  nudge() {
    this.nudges += 1;
  }

  /** Muestra el comando antes de correrlo; corre con run(). Si ya hay una, no hace nada. */
  arm(a: Action, onDone?: (ok: boolean) => void): boolean {
    if (this.locked) return false;
    this.reset();
    this.action = a;
    this.kind = a.action;
    this.command = commandFor(a);
    this.phase = "armed";
    this.onDone = onDone ?? null;
    return true;
  }

  /** Al recargar la página: vuelve a mostrar la acción que sigue corriendo en el servidor,
   *  con todo lo que ya salió. */
  attach(id: string, command: string, kind: string, state: string) {
    if (this.phase !== null && this.phase !== "done") return;
    this.reset();
    this.id = id;
    this.command = command;
    this.kind = kind;
    this.phase = state === "password" ? "password" : "running";
    this.startedAt = Date.now();
    this.listen();
  }

  async run() {
    if (!this.action || this.phase !== "armed") return;
    this.phase = "starting";
    this.startedAt = Date.now();
    try {
      const { id } = await startJob(this.action);
      // El valor de un secreto ya viajó: no se queda en la memoria de la página.
      if (this.action.action === "secret-set") this.action = { ...this.action, value: "" };
      if (this.action.action === "secret-import") this.action = { ...this.action, pairs: [] };
      if (this.action.action === "telegram") this.action = { ...this.action, token: "" };
      if (this.action.action === "create") this.action = { ...this.action, create: { ...this.action.create, secrets: [] } };
      this.id = id;
      this.listen();
    } catch (e) {
      const err = e as ApiError;
      const running = typeof err.data?.running === "string" ? ` ${err.data.running}` : "";
      this.lines = [{ kind: "cmd", text: this.command }, { kind: "bad", text: `✗ ${err.message}${running}` }];
      this.rc = 1;
      this.phase = "done";
      this.endedAt = Date.now();
    }
  }

  private listen() {
    this.source?.close();
    const es = new EventSource(`/api/jobs/${this.id}/events`);
    this.source = es;
    es.addEventListener("line", (e) => {
      if (this.phase === "starting" || this.phase === "password") this.phase = "running";   // al reconectarse: la contraseña ya se respondió
      const l = classify(JSON.parse((e as MessageEvent).data));
      if (l.kind === "stage") this.stageAt[l.text] = Date.now();
      this.lines.push(l);
    });
    es.addEventListener("prompt", (e) => {
      this.prompt = JSON.parse((e as MessageEvent).data);
      this.phase = "password";
      this.minimized = false;   // pide tu contraseña: se abre sola, no espera escondida
    });
    es.addEventListener("done", (e) => {
      this.rc = Number(JSON.parse((e as MessageEvent).data));
      this.phase = "done";
      this.endedAt = Date.now();
      this.prompt = "";
      es.close();
      this.source = null;
      this.onDone?.(this.rc === 0);
      for (const f of finished) f(this.command, this.rc === 0, this.rc);
    });
  }

  async password(pw: string) {
    if (this.phase !== "password") return;
    this.phase = "running";
    await sendPassword(this.id, pw);
  }

  async cancel() {
    if (this.phase === "armed") return this.reset();
    if (this.phase === "password") await cancelJob(this.id);
  }

  close() {
    if (!this.busy) this.reset();
  }

  private reset() {
    this.source?.close();
    this.source = null;
    this.phase = null;
    this.kind = "";
    this.minimized = false;
    this.startedAt = 0;
    this.action = null;
    this.command = "";
    this.lines = [];
    this.stageAt = {};
    this.endedAt = 0;
    this.prompt = "";
    this.rc = null;
    this.id = "";
  }
}

export const job = new Job();
