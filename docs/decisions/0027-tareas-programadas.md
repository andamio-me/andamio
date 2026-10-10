# 0027. Tareas programadas por app

- **Estado:** Aceptada
- **Fecha:** 2026-10-10

## Contexto
Casi toda app necesita algo que corra solo: limpiar datos viejos, mandar un reporte,
sincronizar. Sin soporte, cada quien metía un cron dentro del contenedor (se pierde en cada
deploy) o en el servidor a mano (fuera del repo, sin avisos).

## Decisión
- `cron:` en `app.yml` (`name`, `schedule`, `command`), manejado con `andamio app cron
  add|list|run|rm`. Horario en formato cron: el que todos conocen.
- En el servidor, **un timer de systemd por tarea** (`andamio-cron-<app>.<tarea>`), no cron:
  `Persistent=` (corre al encender si se perdió una hora), sin solapes (un `oneshot` activo no
  arranca dos veces), logs en el journal y nada que instalar.
- La traducción cron → `OnCalendar` vive en un solo lugar (`ansible/filter_plugins/andamio_cron.py`):
  la usan Ansible y la CLI (para validar y mostrar la próxima vez). Lo que no se traduce igual
  se rechaza: día del mes **y** día de la semana a la vez (cron corre si coincide cualquiera;
  systemd exige los dos) y `@reboot`.
- **Zona horaria del usuario** (`andamio_timezone`, detectada de su máquina y confirmada), en
  el `OnCalendar`: el servidor sigue en UTC.
- Corre con `docker compose run` del servicio de la app: misma imagen, secretos, redes,
  carpetas y límites, en un contenedor de una sola vez que se borra. Comprobado en el
  servidor: `compose ps` no lo cuenta (el deploy no se confunde), no hereda la política de
  reinicio y lleva `traefik.enable=false` (no recibe tráfico). Las alertas, `app logs` e
  `info` ignoran los contenedores de una sola vez.
- El comando va como entrypoint (sin el de la imagen), en un archivo aparte
  (`/etc/andamio/cron/<app>.<tarea>.cmd`): sin comillas que escapar en el unit. Con
  metacaracteres de shell pasa por `sh -c`.
- Si falla (o pasa de una hora): aviso por ntfy/Telegram con el final de su salida, solo
  cuando empieza a fallar y cuando vuelve a andar (sin un aviso por cada vez que corre)
  (`scripts/notify.sh`, compartido con las alertas). El resultado de la última vez queda en
  `/var/lib/andamio-cron/` para `app cron list`.

## Consecuencias
- Una tarea no reinicia ni redespliega la app: aplicar es solo crear o quitar timers.
- Las imágenes distroless no traen `sh`: ahí, comandos simples.
- Una app borrada (`app destroy`) se lleva sus timers en el apply completo.
