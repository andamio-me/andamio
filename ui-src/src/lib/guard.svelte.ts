// Cambios sin aplicar: la página que los tiene se anota aquí. Antes de irte a otra página (o de
// cerrar la pestaña), el panel pregunta: nada se pierde en silencio.
type Check = () => boolean;
const checks = new Set<Check>();

/** Anota una página con cambios pendientes; devuelve cómo borrarla (para el return de onMount). */
export function guard(check: Check): () => void {
  checks.add(check);
  return () => void checks.delete(check);
}

export const dirty = (): boolean => [...checks].some((c) => c());
