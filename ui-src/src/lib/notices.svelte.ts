// Avisos del panel: cuando termina un deploy (de cualquier app, aunque lo haya lanzado un push)
// o una acción del panel. Arriba a la derecha y, si la pestaña no está a la vista y diste
// permiso, también como notificación del sistema. Mientras el panel está abierto, mira los
// deploys cada 15 s si hay alguno en curso y cada 60 s si no.
import * as api from "./api";
import { since } from "./format";
import { t } from "./i18n.svelte";
import { job, onFinished } from "./job.svelte";

export type Entry = Omit<Toast, "id"> & { at: number };
const HISTORY_KEY = "andamio.notices";
const HISTORY_MAX = 30;

function loadHistory(): Entry[] {
  try {
    const raw = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(raw) ? raw.slice(0, HISTORY_MAX) : [];
  } catch {
    return [];
  }
}

export type Toast = {
  id: number; tone: "ok" | "bad"; title: string; detail?: string;
  link?: { href: string; text: string; external?: boolean };
};

const FAST = 15_000;
const SLOW = 60_000;

class Notices {
  toasts = $state<Toast[]>([]);
  deploys = $state<api.Deploy[] | null>(null);
  permission = $state<NotificationPermission | "unsupported">(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission);
  // Historial: los últimos avisos, en este navegador (sobrevive recargas; no sale de tu máquina).
  history = $state<Entry[]>(loadHistory());
  unread = $state(0);
  private seen = new Map<number, string>();
  private timer: ReturnType<typeof setTimeout> | undefined;
  private started = false;
  private next = 1;
  private loading = false;

  // Los que salieron bien se van solos (5 s); con el mouse o el foco encima, esperan.
  private timers = new Map<number, { left: number; since: number; handle?: ReturnType<typeof setTimeout> }>();

  /** Anota un aviso en el historial (sin mostrarlo). */
  log(entry: Omit<Toast, "id">) {
    this.history = [{ ...entry, at: Date.now() }, ...this.history].slice(0, HISTORY_MAX);
    this.unread += 1;
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(this.history));
    } catch { /* navegación privada: el historial vive solo en esta pestaña */ }
  }

  markRead() {
    this.unread = 0;
  }

  clearHistory() {
    this.history = [];
    this.unread = 0;
    try { localStorage.removeItem(HISTORY_KEY); } catch { /* nada que borrar */ }
  }

  push(toast: Omit<Toast, "id">, ms = 5_000, remember = true) {
    if (remember) this.log(toast);
    const id = this.next++;
    this.toasts = [...this.toasts.slice(-3), { ...toast, id }];
    if (ms) {
      this.timers.set(id, { left: ms, since: Date.now() });
      this.resume(id);
    }
  }

  pause(id: number) {
    const t = this.timers.get(id);
    if (!t?.handle) return;
    clearTimeout(t.handle);
    t.handle = undefined;
    t.left -= Date.now() - t.since;
  }

  resume(id: number) {
    const t = this.timers.get(id);
    if (!t || t.handle) return;
    t.since = Date.now();
    t.handle = setTimeout(() => this.dismiss(id), Math.max(t.left, 1500));
  }

  dismiss(id: number) {
    clearTimeout(this.timers.get(id)?.handle);
    this.timers.delete(id);
    this.toasts = this.toasts.filter((x) => x.id !== id);
  }

  /** El permiso lo pide un botón tuyo: el navegador nunca pregunta solo. */
  async ask() {
    if (this.permission === "unsupported") return;
    this.permission = await Notification.requestPermission();
    if (this.permission === "granted") this.push({ tone: "ok", title: t().notifyOn, detail: t().notifyOnDetail }, 5_000, false);
  }

  private system(title: string, body: string, hash?: string) {
    if (this.permission !== "granted" || !document.hidden) return;
    const n = new Notification(title, { body, tag: `andamio-${title}` });
    n.onclick = () => {
      window.focus();
      if (hash) location.hash = hash;
      n.close();
    };
  }

  start() {
    if (this.started) return;
    this.started = true;
    onFinished((command, ok, rc) => {
      // Con la terminal a la vista ya lo ves: el aviso es para cuando miras otra cosa (otra pestaña,
      // o la terminal minimizada). En el historial queda siempre.
      const s = t();
      const entry = { tone: (ok ? "ok" : "bad") as "ok" | "bad", title: ok ? s.actionOk : s.actionBad(rc), detail: command };
      if (document.hidden || job.minimized) {
        this.push(entry);
        this.system(entry.title, command);
      } else {
        this.log(entry);
      }
      void this.poll();   // un reintento lanza un deploy: mirarlo ya
    });
    void this.poll();
  }

  refresh() {
    void this.poll();
  }

  private async poll() {
    clearTimeout(this.timer);
    if (this.loading) return;
    this.loading = true;
    try {
      const list = (await api.deploys()).deploys;
      const first = this.deploys === null;
      for (const d of list) {
        const before = this.seen.get(d.id);
        // Nuevo y ya terminado entre dos vistazos (un deploy rápido): solo si es de hace poco.
        const fresh = before === undefined && since(d.created) < 15 * 60;
        if (!first && d.status === "completed" && before !== "completed" && (before !== undefined || fresh)) this.announce(d);
        this.seen.set(d.id, d.status);
      }
      this.deploys = list;
    } catch {
      if (this.deploys === null) this.deploys = [];
    } finally {
      this.loading = false;
    }
    const busy = this.deploys?.some((d) => d.status !== "completed");
    this.timer = setTimeout(() => void this.poll(), busy ? FAST : SLOW);
  }

  private announce(d: api.Deploy) {
    const s = t();
    const app = d.app ?? "";
    const ok = d.conclusion === "success";
    const title = ok ? s.deployedOk(app) : s.deployedBad(app);
    const detail = `${d.title} · ${d.sha}`;
    this.push({
      tone: ok ? "ok" : "bad", title, detail,
      link: ok ? { href: `#/app/${app}`, text: s.openApp } : { href: d.url, text: s.seeLog, external: true },
    }, ok ? 5_000 : 0);   // una falla se queda hasta que la cierres
    this.system(title, detail, `#/app/${app}`);
  }
}

export const notices = new Notices();
