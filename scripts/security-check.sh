#!/usr/bin/env bash
# Chequeo de seguridad y salud del servidor, para `andamio estado` (que lo envía por stdin
# y le suma las pruebas desde Internet). Corre como root. Una línea por resultado:
#   OK|área|qué           WARN|área|qué|arreglo           FAIL|área|qué|arreglo
#   LISTEN|tcp|puerto     (puertos que escuchan fuera de localhost; andamio los prueba desde afuera)
# Variables: SSH_PORT, BACKUPS (true/false), ANDAMIO_LANG (es/en), SOLO (seguridad: andamio seguridad,
# sin plataforma: sin backups, certificados, contenedores, alertas ni VPN).
set -uo pipefail
# Con sudo el entorno se pierde: entonces vale el idioma de /etc/andamio/andamio.env.
LNG=en; lang=${ANDAMIO_LANG:-$(sed -n 's/^ANDAMIO_LANG=//p' /etc/andamio/andamio.env 2> /dev/null || true)}
[[ ${lang:-} == es* ]] && LNG=es
L() { if [ "$LNG" = es ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
[ "$(id -u)" = 0 ] || { echo "FAIL|andamio|$(L "El chequeo necesita sudo" "The check needs sudo")|"; exit 1; }
SSH_PORT=${SSH_PORT:-22}
BACKUPS=${BACKUPS:-false}

ok() { echo "OK|$1|$2"; }
warn() { echo "WARN|$1|$2|$3"; }
fail() { echo "FAIL|$1|$2|$3"; }
REAPPLY=$(L "andamio servidor (vuelve a aplicar el endurecimiento)" "andamio server (re-applies the hardening)")
ONSERVER=$(L "en el servidor" "on the server")
A_FW=Firewall; A_PATCH=$(L Parches Patches); A_DISK=$(L Disco Disk); A_TIME=$(L Hora Clock)
A_CERT=$(L Certificados Certificates); A_CT=$(L Contenedores Containers); A_ISO=$(L Aislamiento Isolation)

# --- SSH ---
cfg=$(sshd -T 2> /dev/null)
sshv() { awk -v k="$1" '$1 == k { print $2; exit }' <<< "$cfg"; }
if [ "$(sshv passwordauthentication)" = no ]; then ok SSH "$(L "Solo con llave (sin contraseñas)" "Keys only (no passwords)")"
else fail SSH "$(L "Acepta contraseñas: los bots las prueban sin parar" "Accepts passwords: bots keep guessing them")" "$REAPPLY"; fi
[ "$(sshv kbdinteractiveauthentication)" = no ] \
  || fail SSH "$(L "Acepta login interactivo (otra vía de contraseñas)" "Accepts interactive login (another way in with passwords)")" "$REAPPLY"
if [ "$(sshv permitrootlogin)" = no ]; then ok SSH "$(L "root no puede entrar" "root can't log in")"
else fail SSH "$(L "root puede entrar por SSH" "root can log in over SSH")" "$REAPPLY"; fi
if ss -H -tln "sport = :$SSH_PORT" | grep -q .; then ok SSH "$(L "Escucha en tu puerto ($SSH_PORT)" "Listens on your port ($SSH_PORT)")"
else fail SSH "$(L "No escucha en el puerto $SSH_PORT de tu configuración" "Doesn't listen on port $SSH_PORT from your configuration")" "$REAPPLY"; fi
if [ "$(sshv maxauthtries)" -le 4 ] 2> /dev/null && [ "$(sshv x11forwarding)" = no ] && [ "$(sshv allowagentforwarding)" = no ]; then
  ok SSH "$(L "Pocos intentos por conexión, sin reenvíos innecesarios" "Few tries per connection, no needless forwarding")"
else
  warn SSH "$(L "SSH permite muchos intentos por conexión o reenvíos que no se usan" "SSH allows many tries per connection or forwarding nobody uses")" "$REAPPLY"
fi
if [ "$(passwd -S root 2> /dev/null | awk '{ print $2 }')" = L ]; then
  ok SSH "$(L "Contraseña de root bloqueada (tampoco sirve en la consola del proveedor)" "root password locked (it doesn't work on the provider's console either)")"
else
  warn SSH "$(L "root tiene contraseña: sirve en la consola web del proveedor" "root has a password: it works on the provider's web console")" "$REAPPLY"
fi
if systemctl is-active --quiet fail2ban && fail2ban-client status sshd > /dev/null 2>&1; then
  banned=$(fail2ban-client status sshd 2> /dev/null | sed -n 's/.*Currently banned:[[:space:]]*//p')
  ok SSH "$(L "fail2ban bloquea a quien insiste (${banned:-0} IPs bloqueadas ahora)" "fail2ban blocks whoever insists (${banned:-0} IPs blocked now)")"
else
  fail SSH "$(L "Sin fail2ban: nadie frena a los bots que prueban SSH" "No fail2ban: nothing stops bots probing SSH")" "$REAPPLY"
fi

# --- Firewall ---
ufw=$(ufw status verbose 2> /dev/null)
if grep -q "^Status: active" <<< "$ufw"; then
  if grep -q "deny (incoming)" <<< "$ufw"; then ok $A_FW "$(L "UFW activo, entrada denegada por defecto" "UFW active, incoming denied by default")"
  else fail $A_FW "$(L "UFW activo pero deja entrar todo por defecto" "UFW active but lets everything in by default")" "$REAPPLY"; fi
else
  fail $A_FW "$(L "UFW apagado: todo puerto abierto es alcanzable" "UFW off: every open port is reachable")" "$REAPPLY"
fi

# --- Parches ---
if systemctl is-enabled -q unattended-upgrades 2> /dev/null; then
  ok "$A_PATCH" "$(L "Actualizaciones de seguridad automáticas" "Automatic security updates")"
else
  fail "$A_PATCH" "$(L "Sin actualizaciones automáticas de seguridad" "No automatic security updates")" "$REAPPLY"
fi
if [ -x /usr/lib/update-notifier/apt-check ]; then
  sec=$(/usr/lib/update-notifier/apt-check 2>&1 | cut -d';' -f2)
  [ "${sec:-0}" -gt 0 ] 2> /dev/null && warn "$A_PATCH" "$(L "$sec actualizaciones de seguridad pendientes" "$sec security updates pending")" \
    "$(L "llegan solas cada noche; para aplicarlas ya: sudo apt upgrade $ONSERVER" "they arrive every night; to apply them now: sudo apt upgrade $ONSERVER")"
fi
if [ -f /var/run/reboot-required ]; then
  pkgs=$(sort -u /var/run/reboot-required.pkgs 2> /dev/null | head -n 3 | paste -sd, -)
  if apt-config dump | grep -q 'Unattended-Upgrade::Automatic-Reboot "true"'; then
    ok "$A_PATCH" "$(L "Reinicio pendiente (${pkgs:-kernel}): se hará solo en la ventana configurada" \
                       "Reboot pending (${pkgs:-kernel}): it will happen by itself in the configured window")"
  else
    warn "$A_PATCH" "$(L "Hace falta reiniciar para terminar de aplicar parches (${pkgs:-kernel})" "A reboot is needed to finish applying patches (${pkgs:-kernel})")" \
      "$(L "sudo reboot $ONSERVER (los contenedores vuelven solos)" "sudo reboot $ONSERVER (containers come back by themselves)")"
  fi
fi

# --- Recursos ---
disk=$(df -P / | awk 'NR == 2 { gsub("%", "", $5); print $5 }')
prune=$(L "docker system prune quita imágenes viejas" "docker system prune removes old images")
if [ "$disk" -ge 90 ]; then fail "$A_DISK" "$(L "Disco al $disk%" "Disk at $disk%")" "$prune; $(L "o amplía el disco" "or grow the disk")"
elif [ "$disk" -ge 80 ]; then warn "$A_DISK" "$(L "Disco al $disk%" "Disk at $disk%")" "$prune"
else ok "$A_DISK" "$(L "Disco al $disk%" "Disk at $disk%")"; fi
if [ "$(timedatectl show -p NTPSynchronized --value 2> /dev/null)" = yes ]; then ok "$A_TIME" "$(L "Reloj sincronizado" "Clock synchronized")"
else warn "$A_TIME" "$(L "Reloj sin sincronizar (afecta certificados y logs)" "Clock not synchronized (affects certificates and logs)")" "sudo timedatectl set-ntp true"; fi

# Lo de la plataforma (andamio servidor). andamio seguridad solo blinda: no lo revisa.
if [ "${SOLO:-}" != seguridad ]; then

# --- Backups ---
journal=$(L "journalctl -u andamio-backup -n 50 $ONSERVER" "journalctl -u andamio-backup -n 50 $ONSERVER")
if [ "$BACKUPS" = true ]; then
  if [ "$(systemctl show andamio-backup.service -p Result --value)" != success ]; then
    fail Backups "$(L "El último backup falló" "The last backup failed")" "$journal"
  fi
  last=$(set -a; . /etc/restic/env; set +a
         timeout 60 restic snapshots --tag andamio --json 2> /dev/null \
           | python3 -c 'import json,sys,datetime as d; s=json.load(sys.stdin); t=max(x["time"] for x in s)[:19]; print(int((d.datetime.utcnow()-d.datetime.fromisoformat(t)).total_seconds()//3600))' 2> /dev/null)
  if [ -z "$last" ]; then fail Backups "$(L "No pude leer el repositorio de backups" "Couldn't read the backup repository")" \
    "$(L "sudo systemctl start andamio-backup $ONSERVER y revisa" "sudo systemctl start andamio-backup $ONSERVER and check") $journal"
  elif [ "$last" -gt 26 ]; then fail Backups "$(L "El último backup es de hace $last horas" "The last backup is $last hours old")" "$journal"
  else ok Backups "$(L "Último backup hace $last h, fuera del servidor y cifrado" "Last backup $last h ago, off the server and encrypted")"; fi
else
  warn Backups "$(L "Sin backups: tus datos solo viven en este servidor" "No backups: your data only lives on this server")" "andamio backups"
fi

# --- Certificados (los que sirve Traefik) ---
acme=$(L "docker logs traefik | grep -i acme $ONSERVER" "docker logs traefik | grep -i acme $ONSERVER")
certs=$(curl -fs -m 5 127.0.0.1:8080/metrics | awk -F'[{}]' '/^traefik_tls_certs_not_after/ {
  match($2, /cn="[^"]*"/); cn = substr($2, RSTART + 4, RLENGTH - 5); print cn, $3 }')
if [ -z "$certs" ]; then
  warn "$A_CERT" "$(L "Traefik aún no sirve ningún certificado" "Traefik isn't serving any certificate yet")" "$acme"
else
  now=$(date +%s); n=0; soonest=99999
  while read -r cn exp; do
    exp=$(printf '%.0f' "$exp")   # viene en notación científica (1.79e+09)
    days=$(( (exp - now) / 86400 )); n=$((n + 1))
    [ "$days" -lt "$soonest" ] && soonest=$days
    if [ "$days" -lt 14 ]; then fail "$A_CERT" "$(L "$cn vence en $days días" "$cn expires in $days days")" \
      "$acme $(L "(o andamio certificado si es propio)" "(or andamio certificate if it's your own)")"
    elif [ "$days" -lt 25 ]; then warn "$A_CERT" "$(L "$cn vence en $days días (debería haberse renovado)" "$cn expires in $days days (it should have renewed)")" "$acme"; fi
  done <<< "$certs"
  [ "$soonest" -ge 25 ] && ok "$A_CERT" "$(L "$n vigentes; el más próximo vence en $soonest días (se renuevan solos)" \
                                            "$n valid; the next one expires in $soonest days (they renew themselves)")"
fi

# --- Contenedores ---
bad=$(docker ps --format '{{.Names}} {{.Status}}' | grep -E 'unhealthy|Restarting' | cut -d' ' -f1 | paste -sd' ' -)
if [ -z "$bad" ]; then ok "$A_CT" "$(L "$(docker ps -q | wc -l) corriendo, ninguno con problemas" "$(docker ps -q | wc -l) running, none with problems")"
else fail "$A_CT" "$(L "Con problemas: $bad" "With problems: $bad")" "docker logs <$(L nombre name)> $ONSERVER"; fi
# Docker seguro por defecto (daemon.json): puertos locales y sin escalar privilegios.
dj=/etc/docker/daemon.json
if [ "$(jq -r '.ip // empty' "$dj" 2> /dev/null)" = 127.0.0.1 ] && [ "$(jq -r '."no-new-privileges" // false' "$dj" 2> /dev/null)" = true ]; then
  ok "$A_ISO" "$(L "Docker publica en 127.0.0.1 por defecto y sin escalar privilegios" "Docker publishes on 127.0.0.1 by default, with no privilege escalation")"
else
  warn "$A_ISO" "$(L "Docker publica en todas las interfaces por defecto (se salta UFW)" "Docker publishes on all interfaces by default (it bypasses UFW)")" "$REAPPLY"
fi
iso=0
while IFS='|' read -r name priv pid sock ports; do
  name=${name#/}
  if [ "$priv" = true ]; then
    fail "$A_ISO" "$(L "$name es privilegiado: tiene control total del servidor" "$name is privileged: it has full control of the server")" \
      "$(L "quita privileged: true de su compose" "remove privileged: true from its compose")"; iso=1
  fi
  if [ "$sock" = SI ] && [ "$name" != socket-proxy ]; then
    fail "$A_ISO" "$(L "$name monta el socket de Docker: puede controlar todo el servidor" "$name mounts the Docker socket: it can control the whole server")" \
      "$(L "usa el socket-proxy (solo lectura)" "use the socket-proxy (read-only)")"; iso=1
  fi
  if [ "$pid" = host ] && [ "$name" != node-exporter ]; then
    warn "$A_ISO" "$(L "$name ve los procesos del servidor (pid: host)" "$name sees the server's processes (pid: host)")" \
      "$(L "quita pid: host de su compose si no lo necesita" "remove pid: host from its compose if it doesn't need it")"; iso=1
  fi
  for p in $ports; do
    [ "$name" = traefik ] && [[ $p = 80 || $p = 443 ]] && continue
    fail "$A_ISO" "$(L "$name publica el puerto $p en todas las interfaces: Docker se salta UFW" "$name publishes port $p on all interfaces: Docker bypasses UFW")" \
      "$(L "en su compose usa \"127.0.0.1:$p:...\", o publícalo por Traefik" "in its compose use \"127.0.0.1:$p:...\", or publish it through Traefik")"; iso=1
  done
done < <(docker ps -q | xargs -r docker inspect --format \
  '{{.Name}}|{{.HostConfig.Privileged}}|{{.HostConfig.PidMode}}|{{range .Mounts}}{{if eq .Source "/var/run/docker.sock"}}SI{{end}}{{end}}|{{range $p, $b := .HostConfig.PortBindings}}{{range $b}}{{if or (eq .HostIp "") (eq .HostIp "0.0.0.0") (eq .HostIp "::")}}{{.HostPort}} {{end}}{{end}}{{end}}')
[ "$iso" = 0 ] && ok "$A_ISO" "$(L "Ningún contenedor privilegiado, con el socket de Docker o con puertos fuera de Traefik" \
                                   "No privileged containers, none with the Docker socket or ports outside Traefik")"

# --- Alertas (scripts/alerts.sh: contenedor caído, disco casi lleno) ---
A_AL=$(L Alertas Alerts)
ntfy=$(sed -n 's/^ANDAMIO_NTFY_URL=//p' /etc/andamio/andamio.env 2> /dev/null)
ch=""; [ -n "$ntfy" ] && ch=ntfy
[ -r /etc/andamio/telegram.env ] && ch="${ch:+$ch + }Telegram"
if [ -n "$ch" ]; then
  ok "$A_AL" "$(L "Te avisan si algo se cae o el disco se llena ($ch)" "You're notified if something goes down or the disk fills up ($ch)")"
else
  warn "$A_AL" "$(L "Nadie te avisa si algo se cae o el disco se llena" "Nobody tells you if something goes down or the disk fills up")" \
    "bin/andamio $(L alertas alerts)"
fi

# --- VPN ---
if wg show wg0 > /dev/null 2>&1; then
  ok VPN "$(L "WireGuard activo ($(wg show wg0 peers | wc -l) dispositivos)" "WireGuard active ($(wg show wg0 peers | wc -l) devices)")"
else
  warn VPN "$(L "WireGuard no está activo: los paneles privados no son alcanzables" "WireGuard isn't active: private panels can't be reached")" \
    "sudo systemctl start wg-quick@wg0"
fi

fi   # fin de lo de la plataforma

# --- Puertos que escuchan fuera de localhost (andamio los prueba desde Internet) ---
ss -H -tln | awk '{ print $4 }' | grep -vE '^(127\.|\[::1\]|.*%lo)' | sed 's/.*://' | sort -un \
  | while read -r port; do echo "LISTEN|tcp|$port"; done
