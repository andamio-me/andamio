#!/usr/bin/env bash
# Prueba de restauración (sirve para cualquier servidor andamio): el último backup se
# puede leer y sus dumps de PostgreSQL y de MariaDB (si alguna app la usa) cargan en bases
# temporales, que se comparan con producción. No toca producción. Lo corre `andamio backups`; a mano: sudo scripts/restore-check.sh
#
# Los datos de tus stacks propios (archivos en /srv/andamio/data, lo de sus backup-hook.sh) van
# en el mismo backup: restaurarlos es docs/runbooks/restaurar-backup.md.
set -euo pipefail
# Con sudo el entorno se pierde: entonces vale el idioma de /etc/andamio/andamio.env.
LNG=en; lang=${ANDAMIO_LANG:-$(sed -n 's/^ANDAMIO_LANG=//p' /etc/andamio/andamio.env 2> /dev/null || true)}
[[ ${lang:-${LANG:-}} == es* ]] && LNG=es
L() { if [ "$LNG" = es ]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
[ "$(id -u)" = 0 ] || { L "Correr con sudo" "Run with sudo"; exit 1; }

T=/var/tmp/andamio-restore-check
NET=restore-check-net
PG=restore-check-pg
MD=restore-check-mariadb
cleanup() {
  docker rm -f "$PG" "$MD" > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$T"
}
trap cleanup EXIT
cleanup

ok=0; bad=0
check() {  # check <qué> <producción> <restaurado>
  if [ "$2" = "$3" ]; then echo "  ✓ $1: $3"; ok=$((ok + 1))
  else L "  ✗ $1: producción=$2 restaurado=$3" "  ✗ $1: production=$2 restored=$3"; bad=$((bad + 1)); fi
}

set -a; . /etc/restic/env; set +a

L "==> Último backup" "==> Latest backup"
# --latest 1 da uno por grupo de rutas: si cambió lo que se respalda, habría varios.
restic snapshots --tag andamio --compact | grep -E '^[0-9a-f]{8} ' | tail -n 1 | grep . \
  || { L "  ✗ No hay ningún backup todavía" "  ✗ There are no backups yet"; exit 1; }

L "==> Integridad del repositorio (con una muestra del 5% de los datos)" "==> Repository integrity (with a 5% sample of the data)"
restic check --read-data-subset=5% -q && L "  ✓ repositorio íntegro" "  ✓ repository intact"

L "==> Restaurar el último backup en $T" "==> Restoring the latest backup into $T"
restic restore latest --tag andamio --target "$T" --include /var/backups/andamio -q
D=$T/var/backups/andamio
check "$(L "dump de PostgreSQL restaurado" "PostgreSQL dump restored")" yes "$([ -s "$D/postgres.sql" ] && echo yes || echo no)"
check "$(L "snapshot de Redis restaurado" "Redis snapshot restored")" yes "$([ -s "$D/redis.rdb" ] && echo yes || echo no)"

L "==> PostgreSQL temporal con el dump (red interna, sin puertos)" "==> Temporary PostgreSQL with the dump (internal network, no ports)"
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
    "SELECT count(*) || ' $(L tablas tables)' FROM information_schema.tables
     WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')" < /dev/null
}
PROD_DBS=$(dbs postgres "$PG_USER")
check "$(L "bases de datos" databases)" "$(tr '\n' ' ' <<< "$PROD_DBS")" "$(dbs "$PG" postgres | tr '\n' ' ')"
for db in $PROD_DBS; do
  check "$db" "$(tables postgres "$PG_USER" "$db")" "$(tables "$PG" postgres "$db")"
done

# MariaDB de las apps: solo si corre en producción (alguna app la usa).
if docker ps --format '{{.Names}}' | grep -qx mariadb; then
  L "==> MariaDB temporal con el dump (red interna, sin puertos)" "==> Temporary MariaDB with the dump (internal network, no ports)"
  check "$(L "dump de MariaDB restaurado" "MariaDB dump restored")" yes "$([ -s "$D/mariadb.sql" ] && echo yes || echo no)"
  if [ -s "$D/mariadb.sql" ]; then
    MD_IMAGE=$(docker inspect mariadb --format '{{.Config.Image}}')
    # La misma clave de root que producción: el dump trae sus usuarios y la reemplaza al cargarlo.
    MARIADB_ROOT_PASSWORD=$(docker exec mariadb printenv MARIADB_ROOT_PASSWORD)
    # Por entorno, nunca en la línea de comandos (se vería en la lista de procesos).
    MYSQL_PWD=$MARIADB_ROOT_PASSWORD
    export MARIADB_ROOT_PASSWORD MYSQL_PWD
    docker run -d --name "$MD" --network "$NET" -e MARIADB_ROOT_PASSWORD "$MD_IMAGE" > /dev/null
    for _ in $(seq 1 90); do docker exec "$MD" healthcheck.sh --connect --innodb_initialized < /dev/null > /dev/null 2>&1 && break; sleep 1; done
    mq() {  # mq <contenedor> <consulta>
      docker exec -e MYSQL_PWD "$1" mariadb -uroot -N -B -e "$2" < /dev/null
    }
    loaded=yes
    docker exec -i -e MYSQL_PWD "$MD" mariadb -uroot < "$D/mariadb.sql" > /dev/null || loaded=no
    check "$(L "dump de MariaDB carga sin errores" "MariaDB dump loads without errors")" yes "$loaded"
    SYS="'mysql', 'sys', 'performance_schema', 'information_schema'"
    mdbs() { mq "$1" "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ($SYS) ORDER BY 1"; }
    mtables() { mq "$1" "SELECT CONCAT(COUNT(*), ' $(L tablas tables)') FROM information_schema.TABLES WHERE TABLE_SCHEMA = '$2'"; }
    PROD_MDBS=$(mdbs mariadb)
    check "$(L "bases de MariaDB" "MariaDB databases")" "$(tr '\n' ' ' <<< "$PROD_MDBS")" "$(mdbs "$MD" | tr '\n' ' ')"
    for db in $PROD_MDBS; do
      check "MariaDB $db" "$(mtables mariadb "$db")" "$(mtables "$MD" "$db")"
    done
  fi
fi

echo
L "Resultado: $ok correctos, $bad con diferencias" "Result: $ok correct, $bad with differences"
# Una app que creó tablas después del backup explica una diferencia: el backup de
# `andamio backups` corre justo antes de esta prueba para comparar contra lo mismo.
[ "$bad" = 0 ]
