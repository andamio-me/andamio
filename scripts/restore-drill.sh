#!/usr/bin/env bash
# Simulacro de restauración: prueba que el último backup en B2 alcanza para recuperar
# todo, SIN tocar producción, y mide cuánto tarda. Uso (root): sudo scripts/restore-drill.sh
#
# 1. Línea base en vivo: huellas de todos los archivos de Seafile y conteos de las bases.
# 2. restic check (con una muestra de datos) y restore del último snapshot a $T.
# 3. Copias temporales en una red interna propia (drill-*), sin Traefik ni puertos:
#    PostgreSQL y MariaDB con los dumps restaurados, y Seafile con sus archivos.
# 4. Compara copia contra producción y limpia todo al salir (también si falla).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Correr con sudo"; exit 1; }

INFRA=/srv/homelab/infra
T=/srv/restore-drill
NET=drill-net
SEAFILE_IMAGE=$(docker inspect seafile --format '{{.Config.Image}}')
MARIADB_IMAGE=$(docker inspect seafile-mysql --format '{{.Config.Image}}')
PG_IMAGE=$(docker inspect postgres --format '{{.Config.Image}}')
REDIS_IMAGE=$(docker inspect seafile-redis --format '{{.Config.Image}}')

cleanup() {
  docker rm -f drill-pg drill-maria drill-redis drill-seafile > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$T"
}
trap cleanup EXIT
cleanup

declare -A TIME
phase() { TIME[$1]=$(( SECONDS - ${PHASE_START:-0} )); PHASE_START=$SECONDS; }
ok=0; bad=0
check() {  # check <qué> <producción> <restaurado>
  if [ "$2" = "$3" ]; then echo "  ✓ $1: $3"; ok=$((ok + 1)); else echo "  ✗ $1: producción=$2 restaurado=$3"; bad=$((bad + 1)); fi
}
# Huellas de todo lo que exporta seaf-fsck (todas las bibliotecas, archivo por archivo).
seafile_hashes() {  # seafile_hashes <contenedor>
  docker exec "$1" bash -c 'rm -rf /tmp/exp && cd /opt/seafile/seafile-server-latest \
    && ./seaf-fsck.sh --export /tmp/exp > /dev/null 2>&1 \
    && cd /tmp/exp && find . -type f -print0 | sort -z | xargs -0 -r sha256sum; rm -rf /tmp/exp' < /dev/null
}
pg_counts() {  # pg_counts <contenedor> <usuario>: enlaces y clics de short, deploys del dashboard
  docker exec "$1" psql -U "$2" -d shortener -tA -c "SELECT (SELECT count(*) FROM links) || '/' || (SELECT count(*) FROM clicks)" < /dev/null
}

echo "==> 1. Línea base (producción, solo lectura)"
PG_USER=$(docker exec postgres printenv POSTGRES_USER)
BASE_SHORT=$(pg_counts postgres "$PG_USER")
BASE_FILES=$(seafile_hashes seafile)
echo "  short: $BASE_SHORT enlaces/clics · Seafile: $(printf '%s\n' "$BASE_FILES" | grep -c . ) archivos"
PHASE_START=$SECONDS

echo "==> 2. Verificar el repositorio en B2 y restaurar el último snapshot"
set -a; . /etc/restic/env; set +a
echo "  último snapshot: $(restic snapshots --tag homelab --compact | grep -E '^[0-9a-f]{8} ' | tail -n 1)"
restic check --read-data-subset=5% -q
phase check
restic restore latest --tag homelab --target "$T" \
  --include /var/backups/homelab --include /srv/homelab/data/seafile -q
echo "  restaurado: $(du -sh "$T" | cut -f1)"
phase restore

echo "==> 3. Bases temporales con los dumps restaurados"
docker network create --internal "$NET" > /dev/null
docker run -d --name drill-pg --network "$NET" -e POSTGRES_PASSWORD=drill "$PG_IMAGE" > /dev/null
set -a; . "$INFRA/stacks/seafile/.env"; set +a
docker run -d --name drill-maria --network "$NET" --network-alias seafile-mysql \
  -e MARIADB_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" "$MARIADB_IMAGE" > /dev/null
docker run -d --name drill-redis --network "$NET" --network-alias seafile-redis "$REDIS_IMAGE" \
  redis-server --requirepass "$REDIS_PASSWORD" --save "" --appendonly no > /dev/null
# Por TCP: el servidor temporal de la inicialización solo escucha en el socket local.
for _ in $(seq 1 90); do docker exec drill-pg pg_isready -q -h 127.0.0.1 -U postgres < /dev/null && break; sleep 1; done
# Esperar una consulta real: "mariadb-admin ping" da vivo aunque rechace la contraseña,
# y mientras la imagen se inicializa corre un servidor temporal sin ella.
for _ in $(seq 1 90); do
  docker exec drill-maria mariadb -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1" < /dev/null > /dev/null 2>&1 && break
  sleep 1
done
# --clean del dump intenta borrar roles que no existen aquí: esos avisos no importan.
docker exec -i drill-pg psql -q -U postgres -d postgres < "$T/var/backups/homelab/postgres.sql" > /dev/null 2>&1
docker exec -i drill-maria mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" < "$T/var/backups/homelab/seafile-mysql.sql"
docker exec drill-maria mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH PRIVILEGES" < /dev/null
phase bases

echo "==> 4. Seafile temporal con los archivos restaurados"
docker run -d --name drill-seafile --network "$NET" \
  -v "$T/srv/homelab/data/seafile:/shared" \
  -e SEAFILE_SERVER_HOSTNAME="nube.$DOMAIN" -e SEAFILE_SERVER_PROTOCOL=https -e TIME_ZONE=Etc/UTC \
  -e JWT_PRIVATE_KEY="$JWT_PRIVATE_KEY" \
  -e SEAFILE_MYSQL_DB_HOST=seafile-mysql -e SEAFILE_MYSQL_DB_PORT=3306 \
  -e SEAFILE_MYSQL_DB_CCNET_DB_NAME=ccnet_db -e SEAFILE_MYSQL_DB_SEAFILE_DB_NAME=seafile_db \
  -e SEAFILE_MYSQL_DB_SEAHUB_DB_NAME=seahub_db \
  -e SEAFILE_MYSQL_DB_USER=seafile -e SEAFILE_MYSQL_DB_PASSWORD="$SEAFILE_MYSQL_DB_PASSWORD" \
  -e CACHE_PROVIDER=redis -e REDIS_HOST=seafile-redis -e REDIS_PASSWORD="$REDIS_PASSWORD" \
  -e ENABLE_GO_FILESERVER=true -e ENABLE_SEADOC=false -e ENABLE_NOTIFICATION_SERVER=false \
  -e ENABLE_SEAFILE_AI=false -e ENABLE_FACE_RECOGNITION=false \
  "$SEAFILE_IMAGE" > /dev/null
up=no
for _ in $(seq 1 90); do
  docker exec drill-seafile curl -fs -o /dev/null http://localhost/api2/ping/ < /dev/null 2> /dev/null && { up=yes; break; }
  sleep 2
done
phase seafile

echo "==> 5. Comparación"
check "Seafile responde" yes "$up"
check "short (enlaces/clics)" "$BASE_SHORT" "$(pg_counts drill-pg postgres)"
DRILL_FILES=$(seafile_hashes drill-seafile)
check "archivos de Seafile" "$(printf '%s\n' "$BASE_FILES" | grep -c .)" "$(printf '%s\n' "$DRILL_FILES" | grep -c .)"
check "huellas idénticas" yes "$([ "$BASE_FILES" = "$DRILL_FILES" ] && echo yes || echo no)"
if [ "$BASE_FILES" != "$DRILL_FILES" ]; then diff <(printf '%s\n' "$BASE_FILES") <(printf '%s\n' "$DRILL_FILES") | head -n 10; fi
phase compare

echo
echo "Tiempos: check ${TIME[check]}s · restore ${TIME[restore]}s · bases ${TIME[bases]}s · Seafile ${TIME[seafile]}s · comparación ${TIME[compare]}s"
echo "Recuperación (restore + bases + Seafile en marcha): $(( TIME[restore] + TIME[bases] + TIME[seafile] ))s"
echo "Resultado: $ok correctos, $bad con diferencias"
# Los clics nuevos después del backup de la noche explican una diferencia en short:
# corre el backup a mano justo antes del simulacro para comparar contra lo mismo.
[ "$bad" = 0 ]
