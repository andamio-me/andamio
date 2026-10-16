// Claro, oscuro o el del sistema (por defecto). Se guarda en este navegador y se aplica antes de
// dibujar la página (main.ts lo importa primero): sin un destello del otro tema al abrir.
export type Theme = "system" | "light" | "dark";
const KEY = "andamio.theme";

function stored(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function apply(t: Theme) {
  const root = document.documentElement;
  if (t === "system") delete root.dataset.theme;
  else root.dataset.theme = t;
}

class ThemeStore {
  value = $state<Theme>(stored());

  constructor() {
    apply(this.value);
  }

  set(t: Theme) {
    this.value = t;
    apply(t);
    try {
      if (t === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, t);
    } catch { /* sin almacenamiento: vale para esta pestaña */ }
  }
}

export const theme = new ThemeStore();
