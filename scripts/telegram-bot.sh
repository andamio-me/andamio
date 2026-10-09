#!/usr/bin/env bash
# Bot de Telegram de andamio (long polling). Solo responde al chat autorizado.
# Variables (vía systemd EnvironmentFile): TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
set -uo pipefail

# El token nunca va en la línea de comandos (cualquiera lo ve con ps): la URL viaja en
# un config de curl por un descriptor de archivo (-K), escrito con printf (interno de bash).
api() {  # api <método>?<parámetros>
  curl -s -m 60 -K <(printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$TELEGRAM_TOKEN" "$1")
}
DIR=$(dirname "$(readlink -f "$0")")
OFFSET=0

send() { printf '%s' "$1" | "$DIR/telegram-send.sh"; }

cmd_containers() {
  docker ps -a --format '{{.Names}}\t{{.Status}}' | sort | column -t -s $'\t'
}

cmd_logs() {
  local s=${1:-}
  if [[ ! $s =~ ^[a-z0-9_-]+$ ]] || ! docker ps -a --format '{{.Names}}' | grep -qx "$s"; then
    echo "Uso: /logs <servicio>"; echo; docker ps -a --format '{{.Names}}' | sort; return
  fi
  docker logs --tail 30 "$s" 2>&1 | tail -c 3500
}

cmd_certs() {
  curl -s -m 5 http://127.0.0.1:8080/api/http/routers | jq -r '.[].rule // empty' \
    | grep -o 'Host(`[^`]*`)' | sed 's/^Host(`//; s/`)$//' | sort -u \
    | while read -r d; do
        end=$(echo | timeout 10 openssl s_client -connect 127.0.0.1:443 -servername "$d" 2>/dev/null \
              | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$end" ]; then
          printf '%-35s %3d días\n' "$d" $(( ($(date -d "$end" +%s) - $(date +%s)) / 86400 ))
        else
          printf '%-35s sin certificado\n' "$d"
        fi
      done
}

cmd_backup_now() {
  systemctl start --no-block andamio-backup.service 2>&1 \
    && echo "Backup iniciado. Te aviso cuando termine."
}

HELP="Comandos:
/system      estado del VPS
/containers  estado de los contenedores
/logs <svc>  últimas 30 líneas de logs
/certs       días restantes de cada certificado
/backup_now  lanzar un backup ahora"

echo "Bot iniciado"
while true; do
  resp=$(api "getUpdates?timeout=50&offset=$OFFSET") || { sleep 5; continue; }
  while IFS=$'\t' read -r id chat text; do
    OFFSET=$((id + 1))
    [ "$chat" = "$TELEGRAM_CHAT_ID" ] || { echo "Ignorado: chat $chat"; continue; }
    read -r cmd arg _ <<< "$text"
    cmd=${cmd%%@*}                       # /logs@mibot -> /logs
    echo "Comando: $cmd ${arg:-}"
    case "$cmd" in
      /system)      send "$(/usr/local/bin/system 2>&1)" ;;
      /containers)  send "$(cmd_containers)" ;;
      /logs)        send "$(cmd_logs "${arg:-}")" ;;
      /certs)       send "$(cmd_certs)" ;;
      /backup_now)  send "$(cmd_backup_now)" ;;
      /start|/help) send "$HELP" ;;
    esac
  done < <(printf '%s' "$resp" | jq -r '.result[]? | [.update_id, (.message.chat.id // ""), (.message.text // "")] | @tsv')
done
