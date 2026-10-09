#!/usr/bin/env bash
# Resumen del estado del VPS. Instalado como /usr/local/bin/system
set -uo pipefail

bar() {  # barra de porcentaje: bar 42
  local p=$1 w=20 i s=""
  for ((i = 0; i < w; i++)); do ((i < p * w / 100)) && s+="#" || s+="."; done
  printf '[%s] %3d%%' "$s" "$p"
}
h() { numfmt --to=iec --suffix=B "$1"; }   # bytes -> legible

echo "== $(hostname) | $(uptime -p) | kernel $(uname -r)"
echo

# CPU
read -r l1 l5 l15 _ < /proc/loadavg
cpus=$(nproc)
cpu_pct=$(awk -v l="$l1" -v c="$cpus" 'BEGIN { p = l / c * 100; print (p > 100 ? 100 : int(p)) }')
printf 'CPU    %s  carga %s %s %s (%s núcleos)\n' "$(bar "$cpu_pct")" "$l1" "$l5" "$l15" "$cpus"

# RAM y swap
read -r mt ma < <(free -b | awk '/^Mem:/ { print $2, $7 }')
printf 'RAM    %s  %s usados de %s\n' "$(bar $(( (mt - ma) * 100 / mt )))" "$(h $((mt - ma)))" "$(h "$mt")"
read -r st su < <(free -b | awk '/^Swap:/ { print $2, $3 }')
if (( st > 0 )); then
  printf 'Swap   %s  %s usados de %s\n' "$(bar $(( su * 100 / st )))" "$(h "$su")" "$(h "$st")"
fi

# Disco
read -r dt du < <(df -B1 --output=size,used / | tail -1)
printf 'Disco  %s  %s usados de %s\n' "$(bar $(( du * 100 / dt )))" "$(h "$du")" "$(h "$dt")"
echo

# Docker
running=$(docker ps -q | wc -l); total=$(docker ps -aq | wc -l)
unhealthy=$(docker ps --filter health=unhealthy --format '{{.Names}}' | paste -sd, -)
echo "Contenedores: $running corriendo de $total${unhealthy:+  | ⚠ unhealthy: $unhealthy}"
docker stats --no-stream --format '  {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | sort -k1 | column -t -s $'\t'
echo

# Sistema
res=$(systemctl show andamio-backup.service -p Result --value)
last=$(systemctl show andamio-backup.service -p ExecMainExitTimestamp --value)
next=$(systemctl show andamio-backup.timer -p NextElapseUSecRealtime --value)
echo "Backup: último ${last:-nunca} (${res}) | próximo ${next:-?}"
failed=$(systemctl --failed --no-legend | wc -l)
updates=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst')
echo "Units fallidas: $failed | Actualizaciones pendientes: $updates | $([ -f /var/run/reboot-required ] && echo '⚠ REINICIO PENDIENTE' || echo 'Sin reinicio pendiente')"
