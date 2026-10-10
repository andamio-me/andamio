#!/usr/bin/env bash
# Envía la entrada estándar a Telegram como bloque <pre>.
#   telegram-send.sh          texto plano (se escapa y va en <pre>)
#   telegram-send.sh --html   HTML ya armado y escapado por quien llama (notify.sh)
# Requiere TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en el entorno.
set -uo pipefail
if [ "${1:-}" = --html ]; then
  text=$(cat)
else
  text="<pre>$(head -c 3800 | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')</pre>"
fi
# El token va en un config de curl por descriptor (-K), no en la línea de comandos:
# cualquier usuario del servidor puede leer los argumentos de un proceso con ps.
curl -s -m 15 -K <(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TELEGRAM_TOKEN") \
  -d chat_id="$TELEGRAM_CHAT_ID" -d parse_mode=HTML \
  --data-urlencode text="$text" > /dev/null
