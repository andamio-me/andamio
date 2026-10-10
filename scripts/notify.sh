#!/usr/bin/env bash
# Un aviso al celular: ntfy (ANDAMIO_NTFY_URL) y Telegram si está activado. Lo usan las
# alertas (alerts.sh) y las tareas programadas (app-cron.sh). Nunca falla: un aviso que no
# sale no debe tumbar lo que lo llamó.
#   notify.sh <título> <texto> [<detalle>]
#     detalle: salida de un comando; en Telegram va en un bloque de código, aparte del texto.
#   NOTIFY_ONLY=ntfy notify.sh ...   solo ntfy, no Telegram
set -uo pipefail

ENV=/etc/andamio/andamio.env
# shellcheck source=/dev/null   # lo genera Ansible (andamio.env.j2)
[ -r "$ENV" ] && set -a && . "$ENV" && set +a
server=${ANDAMIO_DOMAIN:-$(hostname)}
title=$1 text=$2
detail=$(printf '%s' "${3:-}" | tail -c 2500)   # cabe en un mensaje (Telegram: 4096)

if [ -n "${ANDAMIO_NTFY_URL:-}" ]; then
  # El título va en la URL (?title=): ntfy no acepta UTF-8 en las cabeceras.
  q=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$title · $server")
  curl -s -m 10 --data-binary "$text${detail:+

$detail}" "$ANDAMIO_NTFY_URL?title=$q" > /dev/null || true
fi
if [ "${NOTIFY_ONLY:-}" != ntfy ] && [ -r /etc/andamio/telegram.env ]; then
  esc() { sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
  html="<b>$(printf '%s' "$title" | esc)</b> · <i>$server</i>
$(printf '%s' "$text" | esc)${detail:+
<pre>$(printf '%s' "$detail" | esc)</pre>}"
  # shellcheck source=/dev/null
  ( set -a; . /etc/andamio/telegram.env; set +a
    printf '%s' "$html" | /srv/andamio/infra/scripts/telegram-send.sh --html ) || true
fi
exit 0
