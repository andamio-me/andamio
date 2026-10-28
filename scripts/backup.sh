#!/usr/bin/env bash
# Backup diario de andamio con restic (destino: RESTIC_REPOSITORY en /etc/restic/env,
# p. ej. B2 o S3). Lo ejecuta andamio-backup.service (root).
set -euo pipefail

set -a; . /etc/restic/env; . /etc/andamio/andamio.env; set +a
STAGING=/var/backups/andamio
install -d -m 700 "$STAGING"

# Aviso a Uptime Kuma (monitor push "Backup diario")
notify() {
  # Uptime Kuma solo existe en el monitoreo completo: sin su contenedor, avisarle da 404.
  if [ -n "${KUMA_PUSH_URL:-}" ] && docker ps --format '{{.Names}}' | grep -qx uptime-kuma; then
    curl -fsS -m 10 --retry 3 "${KUMA_PUSH_URL}?status=$1&msg=$2" > /dev/null || true
  fi
  if [ -f /etc/andamio/telegram.env ]; then
    local icon="✅"; [ "$1" = "up" ] || icon="❌"
    ( set -a; . /etc/andamio/telegram.env; set +a
      echo "$icon Backup: $2 (${SECONDS}s)" | /srv/andamio/infra/scripts/telegram-send.sh ) || true
  fi
}
trap 'notify down "fallo_en_linea_$LINENO"' ERR
# systemd lo corta si pasa de TimeoutStartSec (andamio-backup.service): avisar igual.
trap 'notify down "cortado_por_tiempo"; exit 1' TERM

echo "==> PostgreSQL (pg_dumpall)"
docker exec postgres sh -c 'pg_dumpall -U "$POSTGRES_USER" --clean --if-exists' > "$STAGING/postgres.sql.tmp"
mv "$STAGING/postgres.sql.tmp" "$STAGING/postgres.sql"

echo "==> Redis (snapshot)"
docker exec redis redis-cli SAVE > /dev/null
docker cp redis:/data/dump.rdb "$STAGING/redis.rdb"

# MariaDB de las apps (mysql: true): solo si alguna la usa.
if docker ps --format '{{.Names}}' | grep -qx mariadb; then
  echo "==> MariaDB de las apps (dump coherente)"
  docker exec mariadb sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --all-databases --single-transaction --routines --events' \
    > "$STAGING/mariadb.sql.tmp"
  mv "$STAGING/mariadb.sql.tmp" "$STAGING/mariadb.sql"
fi

echo "==> Seafile (MariaDB, dump coherente)"
# Los archivos de Seafile ya están en /srv/andamio/data/seafile; su base, en un
# volumen de Docker: se respalda con un dump (copiar archivos de una base viva no sirve).
if docker ps --format '{{.Names}}' | grep -qx seafile-mysql; then
  docker exec seafile-mysql sh -c 'mariadb-dump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases --single-transaction --routines'     > "$STAGING/seafile-mysql.sql.tmp"
  mv "$STAGING/seafile-mysql.sql.tmp" "$STAGING/seafile-mysql.sql"
fi

# Vaultwarden: su base SQLite (con WAL) copiada en vivo podría quedar a medias. En pausa un
# instante (no recibe peticiones, sus archivos quietos) se copia la carpeta entera, coherente.
if docker ps --format '{{.Names}}' | grep -qx vaultwarden; then
  echo "==> Vaultwarden (copia coherente)"
  docker pause vaultwarden > /dev/null
  tar czf "$STAGING/vaultwarden.tgz" -C /srv/andamio/data/vaultwarden . || true
  docker unpause vaultwarden > /dev/null
fi

# Solo en el nivel de monitoreo completo (en el mínimo no hay Uptime Kuma).
if docker volume inspect uptime-kuma_kuma_data > /dev/null 2>&1; then
  echo "==> Uptime Kuma (volumen)"
  docker run --rm -v uptime-kuma_kuma_data:/data:ro -v "$STAGING":/out alpine \
    tar czf /out/uptime-kuma.tgz -C /data .
fi

# Lo que guardaron app destroy y app restore: pasados ANDAMIO_ARCHIVE_DAYS días (90) se borra.
# Ya está en los respaldos mensuales, que se guardan 6 meses más.
DAYS=${ANDAMIO_ARCHIVE_DAYS:-90}
if [[ $DAYS =~ ^[0-9]+$ ]] && [ "$DAYS" -gt 0 ] && [ -d /srv/andamio/archive ]; then
  echo "==> Archivo: lo de más de $DAYS días"
  n=$(find /srv/andamio/archive -maxdepth 1 -type f -mtime +"$DAYS" -print -delete | wc -l)
  echo "  $n borrados"
fi

echo "==> Subiendo al repositorio restic"
# Secretos del host (el repo restic va cifrado): llaves de host SSH (el servidor
# reconstruido conserva su huella), VPN, Telegram, deploy key del repo y login de
# GHCR. /etc/restic no: sin su contraseña no se puede leer el repo; vive en el
# gestor de contraseñas.
# Cada paso contra el destino con límite de tiempo: una petición colgada (pasó el 2026-10-08,
# forget --prune 10 h sin salida) cuenta como fallo y avisa, en vez de bloquear las
# noches siguientes. Duran segundos o pocos minutos; los límites sobran de largo.
timeout 2h restic backup "$STAGING" /srv/andamio /etc/ssh /etc/wireguard /etc/andamio \
  "/home/$ANDAMIO_USER/.ssh" "/home/$ANDAMIO_USER/.docker/config.json" \
  --tag andamio --exclude-caches

echo "==> Retención: 7 diarios, 4 semanales, 6 mensuales"
timeout 1h restic forget --tag andamio --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

echo "==> Verificación del repositorio"
timeout 30m restic check

# La lista sin secretos que muestra el panel (andamio ui); si falla, el backup ya está hecho.
/srv/andamio/infra/scripts/backup-list.sh > /dev/null || echo "⚠ backup-list.sh falló (el backup está bien)"

notify up "OK"
echo "==> OK"
