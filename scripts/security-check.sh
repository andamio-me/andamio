#!/usr/bin/env bash
# Chequeo de seguridad y salud del servidor, para `andamio estado` (que lo envía por stdin
# y le suma las pruebas desde Internet). Corre como root. Una línea por resultado:
#   OK|área|qué           WARN|área|qué|arreglo           FAIL|área|qué|arreglo
#   LISTEN|tcp|puerto     (puertos que escuchan fuera de localhost; andamio los prueba desde afuera)
# Variables: SSH_PORT, BACKUPS (true/false).
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "FAIL|andamio|El chequeo necesita sudo|"; exit 1; }
SSH_PORT=${SSH_PORT:-22}
BACKUPS=${BACKUPS:-false}

ok() { echo "OK|$1|$2"; }
warn() { echo "WARN|$1|$2|$3"; }
fail() { echo "FAIL|$1|$2|$3"; }
REAPPLY="bin/andamio servidor (vuelve a aplicar el endurecimiento)"

# --- SSH ---
cfg=$(sshd -T 2> /dev/null)
sshv() { awk -v k="$1" '$1 == k { print $2; exit }' <<< "$cfg"; }
[ "$(sshv passwordauthentication)" = no ] && ok SSH "Solo con llave (sin contraseñas)" \
  || fail SSH "Acepta contraseñas: los bots las prueban sin parar" "$REAPPLY"
[ "$(sshv kbdinteractiveauthentication)" = no ] || fail SSH "Acepta login interactivo (otra vía de contraseñas)" "$REAPPLY"
[ "$(sshv permitrootlogin)" = no ] && ok SSH "root no puede entrar" \
  || fail SSH "root puede entrar por SSH" "$REAPPLY"
ss -H -tln "sport = :$SSH_PORT" | grep -q . && ok SSH "Escucha en tu puerto ($SSH_PORT)" \
  || fail SSH "No escucha en el puerto $SSH_PORT de tu configuración" "$REAPPLY"

# --- Firewall ---
ufw=$(ufw status verbose 2> /dev/null)
if grep -q "^Status: active" <<< "$ufw"; then
  grep -q "deny (incoming)" <<< "$ufw" && ok Firewall "UFW activo, entrada denegada por defecto" \
    || fail Firewall "UFW activo pero deja entrar todo por defecto" "$REAPPLY"
else
  fail Firewall "UFW apagado: todo puerto abierto es alcanzable" "$REAPPLY"
fi

# --- Parches ---
systemctl is-enabled -q unattended-upgrades 2> /dev/null && ok Parches "Actualizaciones de seguridad automáticas" \
  || fail Parches "Sin actualizaciones automáticas de seguridad" "$REAPPLY"
if [ -x /usr/lib/update-notifier/apt-check ]; then
  sec=$(/usr/lib/update-notifier/apt-check 2>&1 | cut -d';' -f2)
  [ "${sec:-0}" -gt 0 ] 2> /dev/null && warn Parches "$sec actualizaciones de seguridad pendientes" \
    "llegan solas cada noche; para aplicarlas ya: ssh al servidor y sudo apt upgrade"
fi
if [ -f /var/run/reboot-required ]; then
  pkgs=$(sort -u /var/run/reboot-required.pkgs 2> /dev/null | head -n 3 | paste -sd, -)
  if apt-config dump | grep -q 'Unattended-Upgrade::Automatic-Reboot "true"'; then
    ok Parches "Reinicio pendiente (${pkgs:-kernel}): se hará solo en la ventana configurada"
  else
    warn Parches "Hace falta reiniciar para terminar de aplicar parches (${pkgs:-kernel})" \
      "sudo reboot en el servidor (los contenedores vuelven solos)"
  fi
fi

# --- Recursos ---
disk=$(df -P / | awk 'NR == 2 { gsub("%", "", $5); print $5 }')
if [ "$disk" -ge 90 ]; then fail Disco "Disco al $disk%" "libera espacio: docker system prune (imágenes viejas) o amplía el disco"
elif [ "$disk" -ge 80 ]; then warn Disco "Disco al $disk%" "docker system prune quita imágenes viejas"
else ok Disco "Disco al $disk%"; fi
[ "$(timedatectl show -p NTPSynchronized --value 2> /dev/null)" = yes ] && ok Hora "Reloj sincronizado" \
  || warn Hora "Reloj sin sincronizar (afecta certificados y logs)" "sudo timedatectl set-ntp true"

# --- Backups ---
if [ "$BACKUPS" = true ]; then
  if [ "$(systemctl show homelab-backup.service -p Result --value)" != success ]; then
    fail Backups "El último backup falló" "ssh al servidor: journalctl -u homelab-backup -n 50"
  fi
  last=$(set -a; . /etc/restic/env; set +a
         timeout 60 restic snapshots --tag homelab --json 2> /dev/null \
           | python3 -c 'import json,sys,datetime as d; s=json.load(sys.stdin); t=max(x["time"] for x in s)[:19]; print(int((d.datetime.utcnow()-d.datetime.fromisoformat(t)).total_seconds()//3600))' 2> /dev/null)
  if [ -z "$last" ]; then fail Backups "No pude leer el repositorio de backups" "ssh al servidor: sudo systemctl start homelab-backup y revisa journalctl -u homelab-backup"
  elif [ "$last" -gt 26 ]; then fail Backups "El último backup es de hace $last horas" "ssh al servidor: journalctl -u homelab-backup -n 50"
  else ok Backups "Último backup hace $last h, fuera del servidor y cifrado"; fi
else
  warn Backups "Sin backups: tus datos solo viven en este servidor" "bin/andamio backups"
fi

# --- Certificados (los que sirve Traefik) ---
certs=$(curl -fs -m 5 127.0.0.1:8080/metrics | awk -F'[{}]' '/^traefik_tls_certs_not_after/ {
  match($2, /cn="[^"]*"/); cn = substr($2, RSTART + 4, RLENGTH - 5); print cn, $3 }')
if [ -z "$certs" ]; then
  warn Certificados "Traefik aún no sirve ningún certificado" "revisa: docker logs traefik | grep -i acme"
else
  now=$(date +%s); n=0; soonest=99999
  while read -r cn exp; do
    exp=$(printf '%.0f' "$exp")   # viene en notación científica (1.79e+09)
    days=$(( (exp - now) / 86400 )); n=$((n + 1))
    [ "$days" -lt "$soonest" ] && soonest=$days
    if [ "$days" -lt 14 ]; then fail Certificados "$cn vence en $days días" "docker logs traefik | grep -i acme (o bin/andamio certificado si es propio)"
    elif [ "$days" -lt 25 ]; then warn Certificados "$cn vence en $days días (debería haberse renovado)" "docker logs traefik | grep -i acme"; fi
  done <<< "$certs"
  [ "$soonest" -ge 25 ] && ok Certificados "$n vigentes; el más próximo vence en $soonest días (se renuevan solos)"
fi

# --- Contenedores ---
bad=$(docker ps --format '{{.Names}} {{.Status}}' | grep -E 'unhealthy|Restarting' | cut -d' ' -f1 | paste -sd' ' -)
[ -z "$bad" ] && ok Contenedores "$(docker ps -q | wc -l) corriendo, ninguno con problemas" \
  || fail Contenedores "Con problemas: $bad" "docker logs <nombre> en el servidor"
iso=0
while IFS='|' read -r name priv pid sock ports; do
  name=${name#/}
  if [ "$priv" = true ]; then
    fail Aislamiento "$name es privilegiado: tiene control total del servidor" "quita privileged: true de su compose"; iso=1
  fi
  if [ "$sock" = SI ] && [ "$name" != socket-proxy ]; then
    fail Aislamiento "$name monta el socket de Docker: puede controlar todo el servidor" "usa el socket-proxy (solo lectura)"; iso=1
  fi
  if [ "$pid" = host ] && [ "$name" != node-exporter ]; then
    warn Aislamiento "$name ve los procesos del servidor (pid: host)" "quita pid: host de su compose si no lo necesita"; iso=1
  fi
  for p in $ports; do
    [ "$name" = traefik ] && [[ $p = 80 || $p = 443 ]] && continue
    fail Aislamiento "$name publica el puerto $p en todas las interfaces: Docker se salta UFW" \
      "en su compose usa \"127.0.0.1:$p:...\", o publícalo por Traefik"; iso=1
  done
done < <(docker ps -q | xargs -r docker inspect --format \
  '{{.Name}}|{{.HostConfig.Privileged}}|{{.HostConfig.PidMode}}|{{range .Mounts}}{{if eq .Source "/var/run/docker.sock"}}SI{{end}}{{end}}|{{range $p, $b := .HostConfig.PortBindings}}{{range $b}}{{if or (eq .HostIp "") (eq .HostIp "0.0.0.0") (eq .HostIp "::")}}{{.HostPort}} {{end}}{{end}}{{end}}')
[ "$iso" = 0 ] && ok Aislamiento "Ningún contenedor privilegiado, con el socket de Docker o con puertos fuera de Traefik"

# --- VPN ---
if wg show wg0 > /dev/null 2>&1; then
  ok VPN "WireGuard activo ($(wg show wg0 peers | wc -l) dispositivos)"
else
  warn VPN "WireGuard no está activo: los paneles privados no son alcanzables" "sudo systemctl start wg-quick@wg0"
fi

# --- Puertos que escuchan fuera de localhost (andamio los prueba desde Internet) ---
ss -H -tln | awk '{ print $4 }' | grep -vE '^(127\.|\[::1\]|.*%lo)' | sed 's/.*://' | sort -un \
  | while read -r port; do echo "LISTEN|tcp|$port"; done
