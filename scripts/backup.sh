#!/usr/bin/env bash
# Backup diario del homelab con restic (destino: RESTIC_REPOSITORY en /etc/restic/env,
# p. ej. B2 o S3). Lo ejecuta homelab-backup.service (root).
set -euo pipefail

set -a; . /etc/restic/env; . /etc/homelab/andamio.env; set +a
STAGING=/var/backups/homelab
install -d -m 700 "$STAGING"

# Aviso a Uptime Kuma (monitor push "Backup diario")
notify() {
  [ -n "${KUMA_PUSH_URL:-}" ] && curl -fsS -m 10 --retry 3 "${KUMA_PUSH_URL}?status=$1&msg=$2" > /dev/null || true
  if [ -f /etc/homelab/telegram.env ]; then
    local icon="✅"; [ "$1" = "up" ] || icon="❌"
    ( set -a; . /etc/homelab/telegram.env; set +a
      echo "$icon Backup: $2 (${SECONDS}s)" | /srv/homelab/infra/scripts/telegram-send.sh ) || true
  fi
}
trap 'notify down "fallo_en_linea_$LINENO"' ERR
# systemd lo corta si pasa de TimeoutStartSec (homelab-backup.service): avisar igual.
trap 'notify down "cortado_por_tiempo"; exit 1' TERM

echo "==> PostgreSQL (pg_dumpall)"
docker exec postgres sh -c 'pg_dumpall -U "$POSTGRES_USER" --clean --if-exists' > "$STAGING/postgres.sql.tmp"
mv "$STAGING/postgres.sql.tmp" "$STAGING/postgres.sql"

echo "==> Redis (snapshot)"
docker exec redis redis-cli SAVE > /dev/null
docker cp redis:/data/dump.rdb "$STAGING/redis.rdb"

echo "==> Seafile (MariaDB, dump coherente)"
# Los archivos de Seafile ya están en /srv/homelab/data/seafile; su base, en un
# volumen de Docker: se respalda con un dump (copiar archivos de una base viva no sirve).
if docker ps --format '{{.Names}}' | grep -qx seafile-mysql; then
  docker exec seafile-mysql sh -c 'mariadb-dump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases --single-transaction --routines'     > "$STAGING/seafile-mysql.sql.tmp"
  mv "$STAGING/seafile-mysql.sql.tmp" "$STAGING/seafile-mysql.sql"
fi

# Solo en el nivel de monitoreo completo (en el mínimo no hay Uptime Kuma).
if docker volume inspect uptime-kuma_kuma_data > /dev/null 2>&1; then
  echo "==> Uptime Kuma (volumen)"
  docker run --rm -v uptime-kuma_kuma_data:/data:ro -v "$STAGING":/out alpine \
    tar czf /out/uptime-kuma.tgz -C /data .
fi

echo "==> Subiendo al repositorio restic"
# Secretos del host (el repo restic va cifrado): llaves de host SSH (el servidor
# reconstruido conserva su huella), VPN, Telegram, deploy key del repo y login de
# GHCR. /etc/restic no: sin su contraseña no se puede leer el repo; vive en el
# gestor de contraseñas.
# Cada paso contra el destino con límite de tiempo: una petición colgada (pasó el 2026-10-08,
# forget --prune 10 h sin salida) cuenta como fallo y avisa, en vez de bloquear las
# noches siguientes. Duran segundos o pocos minutos; los límites sobran de largo.
timeout 2h restic backup "$STAGING" /srv/homelab /etc/ssh /etc/wireguard /etc/homelab \
  "/home/$HOMELAB_USER/.ssh" "/home/$HOMELAB_USER/.docker/config.json" \
  --tag homelab --exclude-caches

echo "==> Retención: 7 diarios, 4 semanales, 6 mensuales"
timeout 1h restic forget --tag homelab --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

echo "==> Verificación del repositorio"
timeout 30m restic check

notify up "OK"
echo "==> OK"
