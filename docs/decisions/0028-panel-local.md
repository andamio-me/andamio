# 0028. Panel visual local (`andamio ui`), no en el servidor

- **Estado:** Aceptada (fase 1: solo mirar)
- **Fecha:** 2026-10-10

## Contexto
Se pidió una versión visual. Lo usual (Coolify y similares) es un panel web en el servidor,
con login, que despliega y lee secretos. Eso choca con tres garantías de andamio: no hay nada
que atacar en el servidor más allá de SSH y las apps, la llave de los secretos vive solo en tu
máquina, y todo cambio es un commit en tu repo.

## Decisión
- El panel es un **servidor web en tu máquina** (`bin/andamio ui`, solo biblioteca estándar
  de Python + `ui/index.html`, `app.css`, `app.js`, sin dependencias) que habla con el VPS por
  **SSH**, como la CLI. En el servidor no se instala nada.
- **Solo te responde a ti:** escucha en `127.0.0.1`, puerto al azar; el link trae una clave
  aleatoria (32 bytes) que pasa a una cookie `HttpOnly; SameSite=Strict` con nombre por puerto;
  sin ella, 403. Rechaza un `Host` distinto de `127.0.0.1:<puerto>`/`localhost:<puerto>` (frena
  el DNS rebinding) y un `Origin` ajeno. CSP `default-src 'self'`, sin marcos, sin caché.
- **Datos:** del servidor en una sola conexión SSH (un script de Python por stdin): el
  contenedor más nuevo de cada app, sin los de las tareas, y memoria/CPU leídas de los
  cgroups (`docker stats` tardaba 5 s). Nunca el entorno de un contenedor. La conexión SSH se
  reusa (ControlMaster en `$XDG_RUNTIME_DIR`): la primera carga ~5 s, las siguientes ~1.5 s.
  Deploys por `forge ci-runs` (GitHub Actions), secretos solo por nombre (sops local), tareas
  con la misma consulta que `app cron list`, logs en vivo por server-sent events.
- En la página, todo dato va con `textContent`: nada de logs o nombres se interpreta como HTML.
- **Fase 1, solo mirar:** sin acciones, sin sudo; cualquier método que no sea GET da 405.

## Fases siguientes
2. Acciones simples (stop/start, `app set`, secretos, tareas): cada botón corre el mismo
   comando de la CLI (commit, push y apply como hoy). Necesita que los comandos acepten sus
   respuestas por adelantado y pedir la contraseña de sudo en la página (en memoria, como hoy).
3. Asistente para crear una app.
4. Si hay demanda, app de escritorio (Tauri) con la misma página: en Windows necesita WSL;
   firmar instaladores y actualizaciones.

## Tecnología (acordada para las fases siguientes)
- **Interfaz:** JS sin framework mientras solo mire; desde la fase 2 (formularios),
  **TypeScript + Svelte** compilado a archivos estáticos en `ui/` (Node solo para quien
  desarrolla andamio, no para quien lo usa).
- **Lógica:** la CLI de siempre; el panel la llama, nunca la duplica.
- **App instalable:** **Tauri** (webview del sistema, ~5–10 MB; Electron ~100 MB). Corre
  `andamio ui --no-browser` y muestra esa misma página; el Rust se limita a la ventana y al
  ciclo de vida. Wails (Go) sería equivalente.
- La velocidad la pone la red (SSH), no el lenguaje de la página.

## Consecuencias
- Comparado con un panel en el servidor: menos superficie de ataque, pero se administra solo
  desde la máquina que tiene tus llaves (no desde el celular), y esa máquina pasa a ser la
  llave de todo. Se dice así en el README ("El modelo de seguridad, con honestidad").
