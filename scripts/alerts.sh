#!/usr/bin/env bash
# Alertas sin Grafana: un contenedor caído o enfermo, o el disco casi lleno. Corre con el
# chequeo de salud (cada 30 s, container-health.sh). Avisa una vez cuando un problema dura
# más de un minuto (un deploy no dispara nada) y otra cuando se resuelve.
# Canales: ntfy (ANDAMIO_NTFY_URL, notificaciones al celular sin cuenta) y Telegram si está
# activado. Las apps detenidas con `andamio app stop` no cuentan.
set -uo pipefail

ENV=/etc/andamio/andamio.env
# shellcheck source=/dev/null   # lo genera Ansible (andamio.env.j2)
[ -r "$ENV" ] && set -a && . "$ENV" && set +a
LNG=${ANDAMIO_LANG:-en}
L() { if [ "$LNG" = es ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
STATE=${STATE_DIRECTORY:-/var/lib/andamio-alerts}/state
APPS=/srv/andamio/infra/apps
DISK_ALERT=85   # % para avisar
DISK_OK=80      # % para dar el aviso por resuelto (sin rebotes cerca del límite)

declare -A count was restarts
# Estado: "clave cuenta enviado" por problema, y "r:<id> reinicios" por contenedor.
if [ -f "$STATE" ]; then
  while read -r key n flag; do
    if [[ $key == r:* ]]; then restarts[${key#r:}]=$n; else count[$key]=$n; was[$key]=$flag; fi
  done < "$STATE"
fi
declare -A seen_restarts
declare -A now exists

send() {  # send <título> <texto> [ntfy]   (ntfy: no a Telegram)
  local server=${ANDAMIO_DOMAIN:-$(hostname)}
  if [ -n "${ANDAMIO_NTFY_URL:-}" ]; then
    # El título va en la URL (?title=): ntfy no acepta UTF-8 en las cabeceras.
    local q; q=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1 · $server")
    curl -s -m 10 --data-binary "$2" "$ANDAMIO_NTFY_URL?title=$q" > /dev/null || true
  fi
  if [ "${3:-}" != ntfy ] && [ -r /etc/andamio/telegram.env ]; then
    ( set -a; . /etc/andamio/telegram.env; set +a
      printf '%s · %s\n%s\n' "$1" "$server" "$2" | /srv/andamio/infra/scripts/telegram-send.sh ) || true
  fi
}

# --- Contenedores que deberían estar corriendo (política de reinicio) y no lo están ---
# Clave: app/servicio (hola/app), no el nombre del contenedor, que cambia en cada deploy.
# Si alguna réplica corre sana, el servicio está bien (en un deploy conviven dos).
declare -A ok
while read -r id restart name state health policy project service; do
  case $policy in always | unless-stopped) ;; *) continue ;; esac
  key="c:${project:+$project/}${service:-$name}"
  exists[$key]=1
  seen_restarts[$id]=$restart
  if [ -n "$project" ] && grep -qx 'stopped: true' "$APPS/$project/app.yml" 2> /dev/null; then
    continue   # detenida a propósito
  fi
  # Un contenedor que se cae y Docker reinicia aparece "corriendo" casi siempre: lo delata
  # que sus reinicios suben entre un chequeo y el siguiente.
  if [ -n "${restarts[$id]:-}" ] && [ "$restart" -gt "${restarts[$id]}" ]; then
    now[$key]=$(L "se cae y se reinicia una y otra vez ($restart reinicios)" "keeps crashing and restarting ($restart restarts)")
  elif [ "$state" = running ] && [ "$health" != unhealthy ]; then
    ok[$key]=1
  elif [ "$state" != running ]; then
    now[$key]=$(L "no está corriendo ($state)" "isn't running ($state)")
  else
    now[$key]=$(L "corre, pero su chequeo de salud falla" "runs, but its health check fails")
  fi
done < <(docker ps -aq | xargs -r docker inspect | python3 -c '
import json, sys
for c in json.load(sys.stdin):
    st, lb = c["State"], c["Config"].get("Labels") or {}
    print(c["Id"], c.get("RestartCount", 0), c["Name"].lstrip("/"), st["Status"],
          (st.get("Health") or {}).get("Status", "-"), c["HostConfig"]["RestartPolicy"]["Name"] or "-",
          lb.get("com.docker.compose.project", ""), lb.get("com.docker.compose.service", ""))')
for key in "${!ok[@]}"; do unset 'now[$key]'; done

# --- Disco ---
use=$(df --output=pcent / | tail -n 1 | tr -dc 0-9)
if [ "${use:-0}" -ge "$DISK_ALERT" ] || { [ "${was[disk]:-}" = sent ] && [ "${use:-0}" -ge "$DISK_OK" ]; }; then
  now[disk]="$use%"
fi

# --- Avisar los problemas que duran (2 chequeos seguidos) y los que se resolvieron ---
for key in "${!now[@]}"; do
  n=$(( ${count[$key]:-0} + 1 )); count[$key]=$n
  [ "$n" -ge 2 ] && [ "${was[$key]:-}" != sent ] || continue
  if [ "$key" = disk ]; then
    # Con el monitoreo completo, Grafana ya avisa el disco por Telegram: aquí, solo ntfy.
    only=""; [ "${ANDAMIO_MONITORING_LEVEL:-}" = completo ] && only=ntfy
    send "❌ $(L "Disco al ${now[disk]}" "Disk at ${now[disk]}")" \
      "$(L "Libera espacio: docker system prune, logs viejos o archivos de tus apps. Detalle: andamio estado" \
           "Free some space: docker system prune, old logs or your apps' files. Details: andamio status")" $only
  else
    what=${key#c:}
    send "❌ $(L "Caído: $what" "Down: $what")" \
      "$what ${now[$key]}. $(L "Mira sus logs: andamio app logs ${what%%/*}" "See its logs: andamio app logs ${what%%/*}")"
  fi
  was[$key]=sent
done
for key in "${!count[@]}"; do
  [ -n "${now[$key]:-}" ] && continue
  if [ "${was[$key]:-}" = sent ]; then
    if [ "$key" != disk ] && [ -z "${exists[$key]:-}" ]; then
      :   # ya no existe (app borrada): nada que avisar
    elif [ "$key" = disk ]; then send "✓ $(L "Disco de nuevo bajo el $DISK_OK%" "Disk back under $DISK_OK%")" "$use%"
    else send "✓ $(L "Volvió: ${key#c:}" "Back: ${key#c:}")" "$(L "Corre y está sana otra vez." "It's running and healthy again.")"
    fi
  fi
  unset 'count[$key]' 'was[$key]'
done

# --- Estado para el próximo chequeo ---
tmp=$(mktemp "$STATE.XXXXXX")
{
  for key in "${!count[@]}"; do printf '%s %s %s\n' "$key" "${count[$key]}" "${was[$key]:--}"; done
  for id in "${!seen_restarts[@]}"; do printf 'r:%s %s -\n' "$id" "${seen_restarts[$id]}"; done
} > "$tmp"
mv "$tmp" "$STATE"
