# 0028. Panel visual local (`andamio ui`), no en el servidor

- **Estado:** Aceptada (fases 1, 2a, 2b, el inicio completo y la 3, hechas)
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

## Fase 2a: acciones (hecha)
- Interfaz en **Svelte 5 + TypeScript** (`ui-src/`), compilada a `ui/` dentro de Docker
  (`tools/ui-build.sh`): quien usa andamio no necesita Node. El CI compila y falla si `ui/` no
  corresponde a `ui-src/`.
- Diseño con la identidad de ejemplo.com: el inicio es **el plano vivo del servidor** en
  cianotipia (Internet y VPN → Traefik → apps públicas / solo VPN → PostgreSQL, Redis), con la
  **cartela** del plano para los datos del servidor; la terminal de la web para las acciones.
- Acciones: apagar/encender, `app set` (editando en el lugar, con el comando a la vista) y
  correr una tarea. Cada una corre **el mismo comando de la CLI** en un proceso sin terminal
  (`start_new_session`) con `ANDAMIO_ASSUME=default`: cada pregunta toma su respuesta por
  defecto, así que las de "¿seguro?" frenan en vez de seguir. Una acción a la vez.
- Contraseña de sudo **dentro de la terminal de la página**: se verifica contra el servidor y
  se guarda con el mismo mecanismo de la CLI (memoria, 15 min). Nunca va en una URL ni en un
  log; tres intentos.
- Cada POST exige la cookie, el `Origin` exacto, una clave de sesión en `X-Andamio-CSRF`
  (otro sitio no puede leerla) y JSON. Los valores se validan antes de llegar al comando
  (lista de argumentos, sin shell). Tests de mutación: quitar cualquiera de esas defensas hace
  fallar la suite.
- Fuera, a propósito: borrar, rollback y crear app.

## Fase 2b: el resto del día a día (hecha)
- Secretos (agregar, cambiar, quitar): el valor entra al comando por **stdin**, como
  `... | andamio app secret set`; nunca en la línea de comandos, en el comando mostrado ni en la
  salida (hay un test que lo busca). En la página, se borra apenas se envía.
- Tareas: crear con vista previa del horario (`/api/cron-preview`, el mismo conversor que
  Ansible) y quitar. La primera vez, la zona horaria del navegador (`ANDAMIO_TIMEZONE`).
- Dominios, CORS y carpetas. Un dominio cuyo DNS no apunta al servidor no se agrega salvo
  que marques "Agregarlo igual" (`ANDAMIO_DNS_OK=1`): con la respuesta por defecto de la
  CLI, frena.
- `andamio app retry <app>` (nuevo en la CLI): reintenta el último deploy fallido.

## El inicio completo (hecho)
- Al pie del plano, como en ejemplo.com, la fila **La plataforma**: backups (resultado y hora
  del último y del próximo, de systemd, sin sudo), alertas (solo si están activas: la
  dirección de ntfy no sale del servidor, quien la conozca lee tus avisos) y seguridad.
- Seguridad: `andamio estado` guarda su resumen en tu máquina (`~/.cache/andamio/estado-*.json`),
  lo corras desde la CLI o desde el panel ("Revisar ahora", con sudo en la terminal).
- Una franja de lo que necesita atención, solo si hay algo.
- Deploys recientes de todas las apps (`forge ci-runs` en paralelo), cargados aparte para
  que el plano no espere a GitHub.
- UX: las secciones del detalle siguen un solo patrón (título, una línea de qué es, la acción
  a la derecha, filas en una caja; el formulario de agregar es la primera fila). Los secretos
  tienen su sección.

## Fase 3: crear una app (hecha)
- "Nueva app", en cuatro pasos en la página: repo (`forge repos`, con buscador) o plantilla;
  revisión (`/api/create/preview`: clona en una carpeta temporal, con las mismas funciones que
  `app create`: `detect_kind`, el Dockerfile propuesto, `precheck_findings`; las consultas a
  GitHub van en paralelo); configuración; y el comando exacto.
- Crear corre el mismo `andamio app create`. Lo que se decidió en la página llega como
  respuestas, no como atajos: `ANDAMIO_CREATE_OK` (el "¿Crear?"), `ANDAMIO_PRECHECK_OK` (solo
  si marcaste "crear igual"), `ANDAMIO_START_CMD` (el comando de arranque). Cualquier otra
  pregunta toma su respuesta por defecto.

## Borrar desde el panel (agregado)
- Al pie del detalle, "Zona de peligro", con doble confirmación como GitHub: marcar que
  entiendes lo que se borra (y qué no) y escribir el nombre exacto. El servidor del panel lo
  vuelve a comprobar y la CLI pide el nombre otra vez (va por stdin). Corre el mismo
  `andamio app destroy` (respaldo de la base y de las carpetas antes de borrar). El dashboard,
  protegido.

## Avisos, historial de uso, rollback y respaldos (agregado 2026-10-11)
- **Avisos:** mientras el panel está abierto mira `/api/deploys` (15 s con uno en curso, 60 s
  si no; solo corridas `push` de main) y avisa cuando uno termina, también los de un `git push`.
  Notificación del sistema solo si la pestaña no está a la vista y diste permiso con un botón.
- **Historial de uso:** Prometheus del servidor (cAdvisor por contenedor, node-exporter),
  consultado por SSH en `127.0.0.1:9091` del servidor; nada nuevo abierto. Gráficas en SVG propio
  (sin librerías), colores validados para daltonismo en claro y oscuro.
- **Rollback desde el panel:** `andamio app rollback <app> [<commit>]` toma los deploys de la
  forja (también en apps sin base) y usa el deploy sin caída de siempre; si la imagen falta o no
  queda sana, sigue la actual. Una ventana de confirmación (no doble: es reversible).
- **Respaldos:** `backup.sh` deja al terminar una lista sin secretos
  (`/var/lib/andamio-backup/snapshots.json`, la escribe `scripts/backup-list.sh`) que el panel
  lee sin sudo. `andamio backups now|list`. Restaurar UNA app (`andamio app restore`,
  `scripts/app-restore.sh`, con sudo): base y carpetas persistentes; el respaldo se prueba en un
  PostgreSQL temporal antes de tocar nada, lo de ahora se guarda en `/srv/andamio/archive/`, y si
  cargar la base falla se repone la anterior. No toca Redis, código ni secretos. Doble
  confirmación, como borrar.

## Logs, Ctrl+K, historial, ajustes y varios servidores (agregado 2026-10-11)
- **Logs:** búsqueda y "solo errores" en la página (lo que llegó), 200/1000/5000 líneas hacia
  atrás (el servidor del panel solo acepta esos tres), descarga como .txt.
- **Ctrl+K:** ir a apps y páginas o armar acciones; los nombres salen de tus archivos
  (`/api/names`), sin SSH. Las acciones se arman en la terminal como cualquier botón.
- **Historial:** `git log` de tu copia (local). Deshacer solo commits que modificaron únicamente
  `apps/<app>/app.yml` (y su compose): `andamio app revert` aplica el inverso de app.yml con
  `git apply -R` (si un cambio posterior tocó esas líneas, falla sin tocar nada), regenera el
  compose, hace un commit nuevo y aplica. Nunca secretos, ni crear o borrar apps.
- **Ajustes:** alertas (solo sí/no, nunca la dirección de ntfy), `andamio alertas prueba` (desde
  el servidor, notify.sh), `andamio zona <tz>` (commit y aplicar), `andamio update --check`.
  Activar alertas y aplicar una actualización siguen en la terminal (necesitan el celular o
  resolver conflictos).
- **Varios servidores:** cada copia abre su propio panel (su proceso, puerto y clave) en otra
  pestaña; nada se mezcla. Los abiertos así se cierran con el principal.

## Consola SQL, Telegram guiado y accesibilidad (agregado 2026-10-11)
- **SQL de solo lectura** (`scripts/app-sql.sh`, `andamio app sql`, sección Base de datos): rol
  `<rol>_ro` sin contraseña (solo entra por el socket local del contenedor; por red pg_hba pide
  contraseña), solo SELECT (los permisos se ponen al día en cada uso), NOINHERIT y sin poder
  pasarse a otro rol, `default_transaction_read_only` y `statement_timeout = 5s`; salida cortada
  a 4 MB y 500 filas en el panel. El script es el de tu copia (va por SSH con la consulta por
  stdin): no depende de la versión del servidor. Probado contra la base real: DELETE, DROP,
  desactivar el solo-lectura, SET ROLE y pg_sleep(8) fallan.
- **Telegram guiado** (`andamio telegram`): token comprobado con getMe, chat encontrado con
  getUpdates (sin IDs), cifrado con sops, commit, push y aplicar; `desactivar` apaga el bot y
  el resumen y borra /etc/andamio/telegram.env. Desde el panel, el token va por stdin
  (`--token-stdin`).
- **Accesibilidad y modo claro:** contraste medido en todas las páginas y ventanas (ambos
  temas): verde, ámbar y rojo como texto usan tonos propios (`--ok-text`…) que pasan 4.5:1;
  título h1 en el inicio, foco al contenido al cambiar de página, menú de servidores como
  panel desplegable (Esc vuelve al botón), barra superior compacta a 375 px sin scroll lateral.

## Auditoría de UX (2026-10-11, con la skill ui-ux-pro-max)
- **Una acción a la vez, en serio:** con una acción preparada o corriendo, todos los botones de
  acción se desactivan (`job.locked`) y ninguna puede reemplazar a otra. Las largas o delicadas
  (crear, borrar, restaurar, rollback, deshacer, Telegram, zona horaria, respaldar) muestran la
  terminal al centro en un `<dialog>` modal: el resto de la página queda inerte, no se puede
  navegar (ni con Atrás) y Esc no la cierra hasta que termina. Las cortas, abajo.
- **Recargar no pierde nada:** `/api/jobs/current` dice qué acción corre; la página se vuelve a
  conectar y repite lo que ya salió. Cerrar la pestaña mientras corre pide confirmación.
- **Ventanas:** el fondo no se mueve (`html:has(dialog[open])`), con algo escrito un clic afuera o
  Esc no las cierran, y borrar usa la misma ventana que las demás.
- **No perder cambios:** las páginas con cambios sin aplicar se anotan (`lib/guard.svelte.ts`); al
  irse, una ventana pregunta (Quedarme / Salir y descartar). Atrás vuelve al mismo scroll.
- **Carga y avisos:** esqueletos con la forma de la página y una barra fina arriba; avisos de
  éxito 5 s (se pausan con el mouse o el foco), fallas hasta cerrarlas; "Buscar
  actualizaciones" solo en copias que vienen de un template; botones de 40-44 px con el dedo.

## Terminal minimizable (2026-10-11)
- Mientras corre, la terminal se minimiza a una pastilla abajo a la derecha (lo que corre y cuánto
  lleva); un clic la vuelve a abrir. Si pide la contraseña de sudo, se abre sola. Al terminar queda
  verde o roja, con aviso (y notificación del sistema si diste permiso).
- Minimizada se puede navegar y mirar, pero las acciones siguen bloqueadas: una a la vez, porque
  cada una hace commit, push y aplica en el servidor (dos a la vez chocarían en git y en Ansible).
  Tocar un botón bloqueado explica por qué; la app afectada muestra "Se está borrando…" (u otra).

## Reiniciar, desplegar ahora, tareas, worker, disponibilidad y HTTPS (2026-10-11)
- `andamio app restart` (docker compose restart, sin sudo) y `andamio app deploy` (el último
  build exitoso de main por el deploy sin caída de siempre).
- Tareas: `cron edit` (horario o comando) y `cron runs`: app-cron.sh guarda las últimas 5 corridas
  programadas con su salida en /var/lib/andamio-cron/<app>.<tarea>.runs (0640, grupo del usuario
  de andamio: pueden traer datos); se borran con la tarea.
- Logs del worker (`--worker`, y en el panel).
- Disponibilidad: avg_over_time de "hay un contenedor web sano" (andamio_container_health), solo
  sobre el tiempo con medición. Certificados: desde tu máquina, TLS a cada dominio (sirve también
  para los solo VPN: el certificado se ve antes del filtro de IP); 30 min en caché.

## Velocidad y "entender qué pasó" (2026-10-12)
- Velocidad: la conexión SSH compartida dura 15 min con el panel abierto y un latido cada 90 s
  (en frío tardaba hasta 8 s); los deploys (GitHub) van aparte con 30 s de caché; la página de una
  app ya vista se muestra al instante y se pone al día; pasar el mouse la precarga. Medido: volver
  a una app, de 3-9 s a ~25 ms; la primera vez, ~1,7 s.
- Caídas por hora (7 días) y lista de caídas, de andamio_container_health en Prometheus.
- "Ver por qué": `forge ci-failure` (la API del log del job: `gh run view --log-failed` vuelve vacío
  con workflows reutilizables), recortado alrededor del último error, con las pistas 💡.
- Sugerencias: pico de RAM y p95/máximo de CPU en 7 días (mínimo 2 días); solo dejan el cambio
  pendiente.
- Variables que faltan: clona lo último de main en una carpeta temporal y compara con los
  secretos (60 s de caché). Antes de cada deploy no se puede: lo dispara el push en GitHub.
- Historial de avisos: los últimos 30, en localStorage de tu navegador.

## Sidebar y secciones por app (2026-10-12)
- El detalle de una app tenía todo en una página. Ahora: un sidebar (servidor, Ir a…, Inicio, apps,
  plataforma, avisos; contraíble a íconos, recordado en el navegador; con ☰ en pantallas chicas)
  y 8 secciones por app con su link (#/app/<app>/<sección>): Resumen, Deploys, Logs, Métricas,
  Variables, Tareas, Base de datos, Ajustes. Cada sección pide solo lo suyo; los cambios
  pendientes no se pierden al cambiar de sección. Ctrl+K también va a una sección ("web logs").

## Resumen de una app como tablero (2026-10-12)
- El Resumen eran dos cajas de datos sueltos y el último deploy. Ahora: el pulso de 24 h (CPU y
  RAM contra el límite, tráfico, con gráfica mini y pico; de /api/metrics), En línea por hora
  (de /api/timeline), la actividad mezclada (deploys, historial, arranque, caídas, última
  corrida de cada tarea) y las piezas: /api/services lee de Prometheus la salud, RAM y CPU del
  contenedor web, el worker y PostgreSQL/Redis compartidos (sin socket de Docker ni sudo), más
  tareas, respaldo y certificados. Cabecera con Logs y Desplegar a mano.

## Varias apps en un repo (2026-10-12)
- Front y back en un mismo repo: `dir:` (carpeta y su Dockerfile), `context:` (desde dónde se
  construye), `watch:` (qué más dispara el deploy) y `path:` (una ruta bajo el host de otra app,
  PathPrefix en Traefik, sin quitar el prefijo). Cada app: su workflow (`andamio-<app>.yml` con
  `paths:`), su imagen (`dueño/<app>`) y su llave (`DEPLOY_SSH_KEY_<APP>`, sigue limitada a su
  app en el servidor). app-build.yml gana `dir`, `context` y `deploy_key` (v9); las apps de
  siempre no cambian (mismo compose, mismo `andamio.yml`). forge filtra corridas con
  `--workflow`. El panel detecta las carpetas del repo y agrupa las apps de un repo.

## Detección de carpetas y fuente editable (2026-10-13)
- La detección lee primero lo que el repo declara (workspaces de pnpm/npm/yarn, lerna, go.work),
  después busca hasta 3 niveles; separa apps (Dockerfile, script start, framework de servidor o
  de front, `package main`) de librerías, salta las carpetas dentro de una app y etiqueta el
  papel (front, API, worker, sitio). Como Railway, la fuente se edita después: `andamio app
  source` (carpeta, contexto, rutas) reescribe el pipeline de la app; Ajustes → Código, con
  índice y filtro. Las rutas aceptan carpetas, archivos o patrones; con contexto en la raíz se
  suman los manifiestos de la raíz.

## Crear, borrar, apagar o encender una app sin repasar todo (2026-10-13)
- Esas cuatro acciones corrían el apply completo (unas 130 tareas: las otras apps, Traefik,
  Cockpit, units, certificados). Ahora el registro de apps (Prometheus, llaves de deploy,
  usuarios de Redis, tareas de apps borradas) vive en roles/andamio/tasks/registry.yml, y
  una-app.yml corre el registro y esa app (`_apply <app> --registry`), o solo el registro al
  borrarla (`_apply --registry`). El apply completo queda para la plataforma.

## Crear y desplegar más rápido, primer bloque (2026-10-13)
- Medido con un backend real: ~9-10 min hasta la primera respuesta; la imagen (1.08 GB) y su
  descarga en el servidor eran la mitad. Primer bloque: apps.yml solo con la app que cambia
  (7.1 s → 2.9 s con 3 apps, y ya no crece), el pipeline revisa y construye en paralelo (los
  tests frenan el deploy, no el build; gitleaks y Trivy siguen frenando publicar), caché diaria de
  la base de Trivy, y deploy-app.sh ya no escribe en la base de la app si no tiene su tabla
  deployments. ci-update abre un PR si la rama lo exige.

## Fases siguientes
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
