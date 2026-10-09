#!/usr/bin/env bash
# Prueba de restauración (sirve para cualquier servidor andamio): el último backup se
# puede leer y su dump de PostgreSQL carga en una base temporal, que se compara con
# producción. No toca producción. Lo corre `andamio backups`; a mano: sudo scripts/restore-check.sh
#
# Para una prueba completa de tus propios datos (archivos, otras bases), ver
# scripts/restore-drill.sh como ejemplo.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Correr con sudo"; exit 1; }

T=/var/tmp/andamio-restore-check
NET=restore-check-net
PG=restore-check-pg
cleanup() {
  docker rm -f "$PG" > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$T"
}
trap cleanup EXIT
cleanup

ok=0; bad=0
check() {  # check <qué> <producción> <restaurado>
  if [ "$2" = "$3" ]; then echo "  ✓ $1: $3"; ok=$((ok + 1)); else echo "  ✗ $1: producción=$2 restaurado=$3"; bad=$((bad + 1)); fi
}

set -a; . /etc/restic/env; set +a

echo "==> Último backup"
# --latest 1 da uno por grupo de rutas: si cambió lo que se respalda, habría varios.
restic snapshots --tag homelab --compact | grep -E '^[0-9a-f]{8} ' | tail -n 1 | grep . \
  || { echo "  ✗ No hay ningún backup todavía"; exit 1; }

echo "==> Integridad del repositorio (con una muestra del 5% de los datos)"
restic check --read-data-subset=5% -q && echo "  ✓ repositorio íntegro"

echo "==> Restaurar el último backup en $T"
restic restore latest --tag homelab --target "$T" --include /var/backups/homelab -q
D=$T/var/backups/homelab
check "dump de PostgreSQL restaurado" yes "$([ -s "$D/postgres.sql" ] && echo yes || echo no)"
check "snapshot de Redis restaurado" yes "$([ -s "$D/redis.rdb" ] && echo yes || echo no)"

echo "==> PostgreSQL temporal con el dump (red interna, sin puertos)"
PG_IMAGE=$(docker inspect postgres --format '{{.Config.Image}}')
PG_USER=$(docker exec postgres printenv POSTGRES_USER)
docker network create --internal "$NET" > /dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=restore-check "$PG_IMAGE" > /dev/null
# Por TCP: el servidor temporal de la inicialización solo escucha en el socket local.
for _ in $(seq 1 90); do docker exec "$PG" pg_isready -q -h 127.0.0.1 -U postgres < /dev/null && break; sleep 1; done
# --clean del dump intenta borrar roles que aquí no existen: esos avisos no importan.
docker exec -i "$PG" psql -q -U postgres -d postgres < "$D/postgres.sql" > /dev/null 2>&1 || true

# Bases (sin plantillas) y, en cada una, cuántas tablas tiene.
dbs() { docker exec "$1" psql -U "$2" -d postgres -tA -c \
  "SELECT datname FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres' ORDER BY 1" < /dev/null; }
tables() {  # tables <contenedor> <usuario> <base>
  docker exec "$1" psql -U "$2" -d "$3" -tA -c \
    "SELECT count(*) || ' tablas' FROM information_schema.tables
     WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')" < /dev/null
}
PROD_DBS=$(dbs postgres "$PG_USER")
check "bases de datos" "$(tr '\n' ' ' <<< "$PROD_DBS")" "$(dbs "$PG" postgres | tr '\n' ' ')"
for db in $PROD_DBS; do
  check "$db" "$(tables postgres "$PG_USER" "$db")" "$(tables "$PG" postgres "$db")"
done

echo
echo "Resultado: $ok correctos, $bad con diferencias"
# Una app que creó tablas después del backup explica una diferencia: el backup de
# `andamio backups` corre justo antes de esta prueba para comparar contra lo mismo.
[ "$bad" = 0 ]
