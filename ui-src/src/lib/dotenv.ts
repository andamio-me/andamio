// Un .env pegado: CLAVE=valor por línea, "export" opcional, comillas alrededor del valor y
// comentarios con #. Devuelve cada línea con su número (para decir dónde está un problema).
export type EnvLine = { n: number; key: string; value: string; hasEq: boolean };

export function parseDotenv(text: string): EnvLine[] {
  const out: EnvLine[] = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const l = raw.trim();
    if (!l || l.startsWith("#")) return;
    const body = l.replace(/^export\s+/, "");
    const eq = body.indexOf("=");
    const key = (eq < 0 ? body : body.slice(0, eq)).trim();
    let value = eq < 0 ? "" : body.slice(eq + 1).trim();
    if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) value = value.slice(1, -1);
    out.push({ n: i + 1, key, value, hasEq: eq >= 0 });
  });
  return out;
}
