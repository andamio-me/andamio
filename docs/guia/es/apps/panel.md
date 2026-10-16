---
title: Panel local
description: Tus apps en el navegador, con su estado, logs en vivo y acciones (apagar, cambiar recursos, correr tareas). Corre en tu máquina, no en el servidor.
---

```bash
andamio ui
```

Abre tu navegador en un panel con un **menú a la izquierda**: arriba tu servidor e "Ir a…"
(Ctrl+K); después Inicio, tus apps (la que abres se despliega con sus secciones) y la
plataforma (Respaldos, Historial, Ajustes); abajo, los avisos y el botón para contraerlo a
íconos. En pantallas chicas se abre con ☰. Cada app tiene sus secciones, cada una con su
propio link: **Resumen** (cómo está y lo que conviene revisar), **Deploys**, **Logs** (a
pantalla completa), **Métricas**, **Variables**, **Tareas**, **Base de datos** y **Ajustes**.

El **Resumen** de una app dice cómo va de un vistazo: su CPU y RAM de las últimas 24 h contra
su límite (con una gráfica mini y el pico), su tráfico, y si estuvo en línea hora por hora. Debajo,
su actividad en una sola línea de tiempo (deploys, cambios de configuración, arranques, caídas y
tareas) y sus piezas: el contenedor web, el worker y los servicios compartidos que usa
(PostgreSQL, Redis) con su salud y RAM, sus tareas, su último respaldo y sus certificados.

Lo que vas a encontrar:

- **El plano de tu servidor**, en vivo: Internet y tu VPN entran por Traefik, que reparte a
  tus apps (públicas y solo por VPN); las que usan base o Redis tienen su flecha. Cada app
  muestra su estado y su RAM; tocarla abre su detalle. Al lado, la cartela con el servidor:
  encendido, carga, RAM y disco.
- **La plataforma**, al pie del plano: el último backup y el próximo, si las alertas al
  celular están activas, y la última revisión de seguridad (con **Revisar ahora**, que corre
  `andamio estado` en la terminal, y sus avisos con su arreglo). Lo que no está configurado se
  ve punteado, con el comando que lo configura.
- **Lo que necesita atención**, arriba de todo y solo si hay algo: una app caída, el disco
  casi lleno, un backup que falló o un problema de seguridad.
- **Tus apps** en una tabla: estado, URL, acceso, RAM, versión y tareas. Se pone al día sola
  cada 30 segundos.
- **El servidor en el tiempo:** CPU, RAM y red de las últimas horas o días (1 h, 6 h, 24 h o
  7 días), de Prometheus del servidor. Al pasar el mouse (o con las flechas del teclado) ves el
  valor de cada momento.
- **Deploys recientes** de todas tus apps juntas, con el link a GitHub.
- **Respaldos** (desde la fila de la plataforma, **Ver respaldos**): cómo va el diario, los que
  hay (fecha, cuánto tardó, tamaño) y **Respaldar ahora**.
- **Cada app:** su configuración, cómo está ahora, su **uso en el tiempo** (CPU, RAM con la
  línea de su límite, y red), sus secretos (solo los nombres), sus
  [tareas programadas](/es/docs/apps/manage/#tareas-programadas), sus últimos deploys (con el
  link a GitHub), sus **logs en vivo** (con búsqueda, "solo errores", 200, 1000 o 5000 líneas
  hacia atrás y **Descargar**) y sus últimos cambios.
- **Historial** (el reloj, arriba): cada cambio de tu configuración, por día, desde los commits
  de tu repo. Los de configuración de una app (RAM, dominios, tareas, CORS, acceso) muestran sus
  líneas y tienen **Deshacer**.
- **Ajustes de una app**: un índice a la derecha y un filtro arriba. **Código** dice de dónde
  sale (repo, rama, carpeta y qué rutas disparan su deploy); **Recursos**, **Red y datos**,
  **Cambios** y la **Zona de peligro**.
- **Ajustes** (en Plataforma): el tema (sistema, claro u oscuro, guardado en tu navegador), alertas activas y **Enviar prueba**, la zona horaria de
  las tareas, **Buscar actualizaciones** de andamio, tus servidores y un resumen de tu
  configuración.

**Ctrl+K** (⌘K en Mac), o el buscador de arriba, abre "Ir a…": escribes parte del nombre de una
app, una página o una acción (apagar o encender una app, respaldar ahora, revisar seguridad) y
Enter. Se maneja entero con el teclado.

Ctrl+C en la terminal lo cierra.

## Acciones

En el detalle de una app:

- **Cambiar RAM, CPU, puerto, salud o acceso:** toca el valor y escribe el nuevo; Enter lo deja
  pendiente. Abajo aparece el comando que se va a correr (`andamio app set web --mem 512m`) y
  **Aplicar**. Es un reinicio con la misma imagen, sin deploy.
- **Apagar y encender** la app.
- **Secretos:** agregar o cambiar uno (el valor se escribe en un campo oculto y entra al
  comando por stdin: no se muestra nunca, ni en la terminal) y quitarlo. **Pegar varias**
  agrega un `.env` entero de una vez, con un solo reinicio.
- **Tareas programadas:** crear una (mientras escribes el horario ves cuándo correrá la
  próxima vez, o qué está mal), correrla ya y quitarla.
- **Dominios propios, CORS y carpetas persistentes:** agregar y quitar. Antes de agregar un
  dominio, el panel revisa si su DNS ya apunta a tu servidor; si no, te da el registro A que
  falta y solo sigue si marcas "Agregarlo igual".
- **Reintentar el último deploy**, si falló (por ejemplo, porque faltaba una variable que ya
  pusiste).

Cada acción corre **el mismo comando de la CLI** (commit, push y aplicar, como siempre) y lo
muestra en una terminal dentro de la página: primero el comando, después su salida real. Una
acción a la vez. Si andamio necesita tu contraseña de sudo, la pide **dentro de esa
terminal**: se verifica contra tu servidor y se recuerda solo en la memoria de tu máquina,
igual que en la CLI: 15 minutos sin uso, o lo que elijas en **Ajustes → Contraseña de sudo**
(hasta 8 h), donde también la olvidas.

- **Borrar la app**, al pie de su detalle (**Zona de peligro**), con doble confirmación como
  en GitHub: marcas que entiendes lo que se borra y escribes su nombre exacto. Corre el mismo
  `andamio app destroy`: respalda la base y archiva sus carpetas antes de borrar; el repo de
  GitHub no se toca. Tu dashboard no se borra desde aquí.

- **Volver a un deploy anterior:** en sus deploys, cada uno que salió bien tiene **Volver a
  esta** (el que corre ahora dice "en producción"). Una ventana muestra la versión de ahora y a
  cuál vuelve; corre `andamio app rollback <app> <commit>`, el mismo deploy sin caída de
  siempre: si esa versión no queda sana, sigue la actual. La base no cambia, y el próximo push
  a `main` vuelve a desplegar lo último.
- **Restaurar desde un respaldo:** en **Respaldos**, cada uno tiene **Restaurar una app…**
  (también se llega desde la Zona de peligro de la app). Una ventana en dos pasos, como la de
  borrar: eliges la app y lees qué se reemplaza (su base y sus carpetas persistentes), qué se
  guarda antes y qué no se toca (Redis, el código, los secretos); después escribes su nombre.
  Corre `andamio app restore <app> <respaldo>`, que prueba el respaldo en una base temporal
  antes de tocar nada y guarda lo de ahora en `/srv/andamio/archive/`.

- **Deshacer un cambio de configuración:** en el Historial (o en los cambios de la app),
  **Deshacer**. La ventana muestra cómo queda su configuración; corre
  `andamio app revert <app> <commit>`: un commit nuevo (el historial no se borra) y aplicar esa
  app. Solo cambios de configuración: nunca secretos, ni crear o borrar una app. Si un cambio
  posterior tocó las mismas líneas, no lo hace y te lo dice.

- **Consultar su base, de solo lectura:** en las apps con PostgreSQL, **Base de datos**: sus
  tablas (un clic la consulta) y un editor (Ctrl+Enter). Corre como un usuario aparte que solo
  puede leer, en una transacción de solo lectura, 5 segundos como máximo y hasta 500 filas:
  nada de ahí puede cambiar datos. Las tablas traen sus filas y columnas (con buscador); el
  resultado se ve como tabla o registro por registro, con las columnas sensibles (contraseñas,
  hashes, secretos) ocultas hasta que las muestres; clic en una celda la muestra completa. Se
  descarga en CSV, y las últimas consultas quedan en un historial.
- **Telegram:** en Ajustes, **Configurar Telegram** en tres pasos (tu bot, tu chat, activar),
  igual que `andamio telegram`. El token se escribe oculto y entra al comando por stdin.
- **ntfy:** en Ajustes, **Configurar ntfy**: un tema nuevo en ntfy.sh o la URL de tu propio
  servidor. Después ves la dirección del tema para suscribirte, la copias y mandas una de prueba.

- **Reiniciar** (arriba, junto a Apagar): sus contenedores, con la misma versión.
- **Desplegar ahora** (en Deploys): lo último de main que se construyó bien, sin hacer push.
- **Tareas:** **Editar** cambia su horario o su comando; **Corridas** muestra las últimas 5
  programadas, con su salida (las que fallaron, abiertas).
- **Logs del worker:** si la app tiene worker, los logs tienen web y worker.
- **Disponibilidad y HTTPS:** en "Ahora", el % del tiempo en línea en 24 h y 7 días (de la
  salud de su contenedor) y cuándo vence el certificado de cada dominio. En el inicio, la columna
  "En línea 24 h", y un aviso arriba si un certificado no es válido o vence en menos de 14 días.

- **Caídas:** los últimos 7 días, una barra por hora (verde en línea, ámbar parcial, roja
  caída, gris sin medición), y la lista de caídas con cuánto duraron.
- **Ver por qué** en un deploy que falló: el paso que falló, la causa, las pistas 💡 del servidor y
  las últimas líneas del log, sin ir a GitHub.
- **Sugerencias de RAM y CPU** (con al menos 2 días de datos): si el pico se acerca al límite,
  subirlo; si sobra mucho, bajarlo. **Usar** lo deja pendiente en la barra de Aplicar: tú decides.
- **Revisar variables** (en Secretos): compara las variables que usa el código (lo último de
  main) con los secretos de la app y avisa cuáles faltan, con **Agregar** al lado. Si el último
  deploy falló, se revisa sola.
- **La campana** (arriba): los últimos 30 avisos (deploys, acciones, fallas), aunque no estuvieras
  mirando. Se guardan solo en tu navegador.

Abrir una app ya vista es instantáneo (se muestra lo de antes y se pone al día sola), y pasar el
mouse sobre una app la trae antes de abrirla. La conexión con el servidor queda lista mientras
el panel está abierto.

## Servicios

**Servicios** (en Plataforma) muestra el PostgreSQL y el Redis que comparten tus apps: memoria,
CPU, conexiones y claves en uso, y qué usa cada app (el tamaño de su base, sus conexiones, sus
límites, sus clientes de Redis). Su configuración se cambia ahí mismo; como reinicia el
servicio, una ventana lo dice antes de correr nada. Ver [PostgreSQL y Redis](/es/docs/server/services/).

## Varios servidores

Cada copia de andamio maneja un servidor (las que anota `andamio use`). Con más de una, el
dominio de arriba es un menú: elegir otra abre **su propio panel** en otra pestaña, con su clave
y sus llaves; nada se mezcla. Los paneles que abras así se cierran con este. También están en
**Ajustes → Tus servidores**.

## Avisos

Mientras el panel está abierto, mira tus deploys (cada 15 segundos si hay alguno en curso, si
no cada minuto). Cuando uno termina, aparece un aviso arriba a la derecha: "web desplegada", con
el link a la app, o "El deploy de web falló", con el link al log (ese se queda hasta que lo
cierres). Vale también para los que lanza un `git push`, no solo el panel.

Con **Avisarme** (arriba, una sola vez) el navegador también te muestra una notificación del
sistema cuando estás en otra pestaña o ventana. El permiso lo pides tú con ese botón: el panel
nunca lo pide solo.

## Crear una app

En el inicio, **Nueva app** abre cinco pasos en la misma página:

1. **El repo:** buscas entre tus repos de GitHub (o escribes `dueño/repo`), o empiezas desde tu
   plantilla. Si el repo es público y tu pipeline es privado, te lo dice antes de seguir.
2. **La revisión:** el panel clona el repo en una carpeta temporal (que reusa unos minutos si
   eliges otra carpeta, y después borra) y te muestra
   lo que diría `andamio app create`, sin cambiar nada: el lenguaje, el Dockerfile (el suyo, o
   el que andamio propone, para que lo leas), el comando de arranque (lo puedes cambiar) y la
   [revisión previa](/es/docs/apps/create/#revisión-previa). Si guarda archivos, un clic le
   agrega una carpeta persistente; si hay algo grave, solo sigues si marcas "crear igual".
3. **Listo para desplegar:** si la revisión salió limpia, un resumen (nombre, dirección,
   puerto, servicios y acceso) y un botón, **Desplegar con lo detectado**, como en Railway.
   PostgreSQL y Redis se encienden solos si el código usa `DATABASE_URL` o `REDIS_*`.
   **Personalizar** abre la configuración completa: nombre, dirección (o el dominio raíz),
   acceso, puerto, salud, RAM, PostgreSQL, Redis y carpeta persistente.
4. **Variables de entorno:** las que el código usa (`os.getenv`, `process.env`, `os.Getenv` o
   un `.env.example`) ya vienen, con dónde las encontró. Las que el código **exige**
   (`getOrThrow`, `os.environ[...]`, `process.env.X!`) van primero, marcadas "requerida"; si
   tienen un valor en `.env.example` que no es secreto, un clic lo usa (nunca se ponen solas).
   Llenas sus valores en campos ocultos, pegas un `.env` entero o agregas otras. Se cifran antes del primer deploy y entran al comando por stdin
   (`--env-file -`): no se ven nunca.
5. **Crear:** el comando exacto (`andamio app create …`) y qué va a pasar. Primero tu
   contraseña de sudo; después, en vez de la salida entera, las etapas con su tiempo (revisión,
   registro, servidor, pipeline, deploy); el detalle queda plegado. Al terminar abre la app, y
   ahí ves el **primer deploy en vivo**: sus tres jobs de GitHub Actions, el paso en curso y una
   barra de avance, y al final si salió bien o por qué falló.

## Corre en tu máquina, no en el servidor

Paneles como Coolify viven en el servidor: una página con login que puede desplegar y leer
tus secretos, expuesta en internet. El de andamio es distinto:

- **En el servidor no hay nada nuevo.** El panel es un pequeño servidor web en tu máquina que
  habla con tu VPS por SSH, igual que los comandos de andamio. Ni una puerta más abierta.
- **Solo te responde a ti.** Escucha solo en `127.0.0.1`, en un puerto al azar. El link que
  muestra `andamio ui` trae una clave que cambia cada vez; sin ella responde "prohibido". Las
  acciones, además, exigen el origen exacto de la página y una clave de sesión que otro sitio
  abierto en tu navegador no puede leer ni enviar.
- **Tus secretos y tus llaves no salen de tu máquina**, y cada cambio es un commit en tu repo,
  como en la CLI.

La contrapartida: se usa desde la máquina que tiene tus llaves, no desde el celular o una
computadora ajena. Para mirar de lejos están las
[alertas al celular](/es/docs/server/monitoring/#alertas-al-celular).

## Opciones

| Opción | Qué hace |
|---|---|
| `--no-browser` | No abre el navegador: solo muestra el link (cópialo tú) |
| `--port 8765` | Usa ese puerto en vez de uno al azar |

En WSL se abre el navegador de Windows, que llega al panel sin configurar nada.
