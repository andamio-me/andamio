// Las secciones de una app (el sidebar las lista; cada una con su link #/app/<app>/<sección>).
export type Section = "overview" | "deploys" | "logs" | "metrics" | "variables" | "tasks" | "database" | "settings";

export const SECTIONS: Section[] = ["overview", "deploys", "logs", "metrics", "variables", "tasks", "database", "settings"];

export const appHref = (app: string, s: Section = "overview") => `#/app/${app}${s === "overview" ? "" : `/${s}`}`;

/** #/app/<app>[/<sección>] → { app, section }, o null si no es una app. */
export function parseApp(hash: string): { app: string; section: Section } | null {
  const m = hash.match(/^#\/app\/([a-z0-9-]+)(?:\/([a-z]+))?$/);
  if (!m) return null;
  const s = (m[2] ?? "overview") as Section;
  return { app: m[1]!, section: SECTIONS.includes(s) ? s : "overview" };
}
