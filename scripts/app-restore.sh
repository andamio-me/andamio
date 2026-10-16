#!/usr/bin/env bash
# Restaura UNA app desde un respaldo (restic): su base de PostgreSQL, su base de MariaDB y sus
# carpetas persistentes, tal como estaban ese día. Lo corre `andamio app restore` (con sudo).
#   app-restore.sh <app> <respaldo: id de restic o latest>
#
# En orden, y sin tocar nada hasta saber que el respaldo sirve:
#  1. Saca del respaldo los dumps (PostgreSQL, MariaDB) y las carpetas de la app (a una carpeta temporal).
#  2. Carga cada dump en un servidor temporal (red interna, sin puertos) y extrae SOLO la base de
#     esta app. Si el respaldo no la tiene, para aquí. De MariaDB entra solo su base
#     (--one-database): ni los usuarios ni las bases de las demás apps.
#  3. Guarda el estado actual en /srv/andamio/archive/ (entra al backup), como app destroy.
#  4. Detiene la app, reemplaza su base y sus carpetas y la vuelve a encender. Si cargar la base
#     falla, vuelve a poner la de antes.
# No toca: Redis (es caché y colas), el código ni la versión desplegada, ni los secretos.
set -euo pipefail
# Con sudo el entorno se pierde: entonces vale el idioma de /etc/andamio/andamio.env.
LNG=en; lang=${ANDAMIO_LANG:-$(sed -n 's/^ANDAMIO_LANG=//p' /etc/andamio/andamio.env 2> /dev/null || true)}
[[ ${lang:-${LANG:-}} == es* ]] && LNG=es
L() { if [ "$LNG" = es ]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
[ "$(id -u)" = 0 ] || { L "Correr con sudo" "Run with sudo"; exit 1; }

APP=${1:?uso: app-restore.sh <app> <respaldo>}
SNAP=${2:?uso: app-restore.sh <app> <respaldo>}
[[ $APP =~ ^[a-z][a-z0-9-]{1,28}[a-z0-9]$ ]] || { L "App inválida: $APP" "Invalid app: $APP"; exit 1; }
[[ $SNAP == latest || $SNAP =~ ^[0-9a-f]{8,64}$ ]] || { L "Respaldo inválido: $SNAP" "Invalid backup: $SNAP"; exit 1; }
DIR=/srv/andamio/infra/apps/$APP
[ -f "$DIR/compose.yaml" ] || { L "App desconocida: $APP" "Unknown app: $APP"; exit 1; }
DATA=/srv/andamio/data/apps/$APP
ARCHIVE=/srv/andamio/archive
STAMP=$(date +%Y%m%d-%H%M%S)

T=$(mktemp -d /var/tmp/andamio-restore.XXXXXX)
NET=andamio-restore-net-$$
PG=andamio-restore-pg-$$
MD=andamio-restore-mariadb-$$
cleanup() {
  docker rm -f "$PG" "$MD" > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$T"
}
trap cleanup EXIT

url=$(grep '^DATABASE_URL=' "$DIR/.env" 2> /dev/null | cut -d= -f2- || true)
db="" role=""
if [ -n "$url" ]; then
  db=${url##*/}; role=$(sed -E 's#^postgres(ql)?://([^:]+):.*#\2#' <<< "$url")
  [[ $db =~ ^[a-z0-9_]+$ && $role =~ ^[a-z0-9_]+$ ]] || { L "DATABASE_URL inesperada; no sigo" "Unexpected DATABASE_URL; stopping"; exit 1; }
fi
# MariaDB (mysql: true): su base y su usuario, de MYSQL_URL.
murl=$(grep '^MYSQL_URL=' "$DIR/.env" 2> /dev/null | cut -d= -f2- || true)
mdb="" muser=""
if [ -n "$murl" ]; then
  mdb=${murl##*/}; muser=$(sed -E 's#^mysql://([^:]+):.*#\1#' <<< "$murl")
  [[ $mdb =~ ^[a-z0-9_]+$ && $muser =~ ^[a-z0-9_]+$ ]] || { L "MYSQL_URL inesperada; no sigo" "Unexpected MYSQL_URL; stopping"; exit 1; }
fi
[ -n "$db" ] || [ -n "$mdb" ] || [ -d "$DATA" ] || { L "✗ $APP no tiene base ni carpetas persistentes: no hay nada que restaurar." \
                                       "✗ $APP has no database or persistent folders: there's nothing to restore."; exit 1; }

set -a; . /etc/restic/env; set +a

echo "==> $(L "Sacando del respaldo $SNAP lo de $APP" "Taking $APP's data out of backup $SNAP")"
restic snapshots --tag andamio --compact "$SNAP" | grep -E '^[0-9a-f]{8} ' \
  || { L "✗ No existe el respaldo $SNAP" "✗ Backup $SNAP doesn't exist"; exit 1; }
args=(--target "$T")
[ -n "$db" ] && args+=(--include /var/backups/andamio/postgres.sql)
[ -n "$mdb" ] && args+=(--include /var/backups/andamio/mariadb.sql)
args+=(--include "$DATA")
restic restore "$SNAP" --tag andamio "${args[@]}" -q
SAVED_DATA=$T$DATA

if [ -n "$db" ]; then
  [ -s "$T/var/backups/andamio/postgres.sql" ] || { L "✗ El respaldo no trae el dump de PostgreSQL" "✗ The backup has no PostgreSQL dump"; exit 1; }
  echo "==> $(L "Comprobando la base en un PostgreSQL temporal (red interna, sin puertos)" "Checking the database in a temporary PostgreSQL (internal network, no ports)")"
  PG_IMAGE=$(docker inspect postgres --format '{{.Config.Image}}')
  docker network create --internal "$NET" > /dev/null
  docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=restore "$PG_IMAGE" > /dev/null
  for _ in $(seq 1 90); do docker exec "$PG" pg_isready -q -h 127.0.0.1 -U postgres < /dev/null && break; sleep 1; done
  # --clean del dump intenta borrar roles que aquí no existen: esos avisos no importan.
  docker exec -i "$PG" psql -q -U postgres -d postgres < "$T/var/backups/andamio/postgres.sql" > /dev/null 2>&1 || true
  [ "$(docker exec "$PG" psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$db'" < /dev/null)" = 1 ] \
    || { L "✗ Ese respaldo no tiene la base de $APP (¿la app es más nueva que el respaldo?). No toqué nada." \
           "✗ That backup doesn't have $APP's database (is the app newer than the backup?). Nothing was touched."; exit 1; }
  # Sin dueños ni permisos: al cargarla, todo queda del usuario de la app (como al crearla).
  docker exec "$PG" pg_dump -U postgres --no-owner --no-privileges -d "$db" < /dev/null > "$T/app.sql"
  [ -s "$T/app.sql" ] || { L "✗ La base del respaldo salió vacía. No toqué nada." "✗ The backup's database came out empty. Nothing was touched."; exit 1; }
  tables=$(docker exec "$PG" psql -U postgres -d "$db" -tAc "SELECT count(*) FROM information_schema.tables
    WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')" < /dev/null)
  echo "  ✓ $(L "base $db del respaldo: $tables tablas" "database $db from the backup: $tables tables")"
  docker rm -f "$PG" > /dev/null
fi
if [ -n "$mdb" ]; then
  [ -s "$T/var/backups/andamio/mariadb.sql" ] || { L "✗ El respaldo no trae el dump de MariaDB" "✗ The backup has no MariaDB dump"; exit 1; }
  echo "==> $(L "Comprobando la base en un MariaDB temporal (red interna, sin puertos)" "Checking the database in a temporary MariaDB (internal network, no ports)")"
  MD_IMAGE=$(docker inspect mariadb --format '{{.Config.Image}}')
  docker network inspect "$NET" > /dev/null 2>&1 || docker network create --internal "$NET" > /dev/null
  docker run -d --name "$MD" --network "$NET" -e MARIADB_ROOT_PASSWORD=restore "$MD_IMAGE" > /dev/null
  for _ in $(seq 1 90); do docker exec "$MD" healthcheck.sh --connect --innodb_initialized < /dev/null > /dev/null 2>&1 && break; sleep 1; done
  mtmp() { docker exec -i -e MYSQL_PWD=restore "$MD" mariadb -uroot "$@"; }
  # Solo la base de esta app: --one-database salta todo lo que no sea de ella (usuarios incluidos).
  mtmp -e "CREATE DATABASE \`$mdb\`" < /dev/null
  mtmp --one-database "$mdb" < "$T/var/backups/andamio/mariadb.sql" > /dev/null
  mtables=$(mtmp -N -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '$mdb'" < /dev/null)
  # Un dump sin la base de la app no crea nada en ella: entonces el respaldo no la tiene.
  grep -q "^USE \`$mdb\`;" "$T/var/backups/andamio/mariadb.sql" \
    || { L "✗ Ese respaldo no tiene la base de MariaDB de $APP (¿la app es más nueva que el respaldo?). No toqué nada." \
           "✗ That backup doesn't have $APP's MariaDB database (is the app newer than the backup?). Nothing was touched."; exit 1; }
  docker exec -e MYSQL_PWD=restore "$MD" mariadb-dump -uroot --single-transaction --routines --events "$mdb" < /dev/null > "$T/app-mariadb.sql"
  [ -s "$T/app-mariadb.sql" ] || { L "✗ La base de MariaDB del respaldo salió vacía. No toqué nada." "✗ The backup's MariaDB database came out empty. Nothing was touched."; exit 1; }
  echo "  ✓ $(L "base $mdb (MariaDB) del respaldo: $mtables tablas" "database $mdb (MariaDB) from the backup: $mtables tables")"
  docker rm -f "$MD" > /dev/null
fi
if [ -d "$SAVED_DATA" ]; then
  echo "  ✓ $(L "carpetas del respaldo: $(du -sh "$SAVED_DATA" | cut -f1)" "folders from the backup: $(du -sh "$SAVED_DATA" | cut -f1)")"
elif [ -d "$DATA" ]; then
  L "  ! El respaldo no tiene carpetas de $APP: las de ahora se quedan como están." \
    "  ! The backup has no folders for $APP: the current ones stay as they are."
fi

echo "==> $(L "Guardando el estado actual en $ARCHIVE" "Saving the current state in $ARCHIVE")"
install -d -m 700 "$ARCHIVE"
before=""
if [ -n "$db" ]; then
  before=$ARCHIVE/$APP-$(L antes-de-restaurar before-restore)-$STAMP.sql.gz
  docker run --rm --network data "$PG_IMAGE" pg_dump --no-owner --no-privileges "$url" | gzip > "$before"
  [ "$(gunzip -c "$before" | wc -c)" -gt 0 ] || { L "✗ La copia de la base actual quedó vacía; no sigo" "✗ The copy of the current database came out empty; stopping"; exit 1; }
  echo "  ✓ $before ($(du -h "$before" | cut -f1))"
fi
mbefore=""
if [ -n "$mdb" ]; then
  mbefore=$ARCHIVE/$APP-mariadb-$(L antes-de-restaurar before-restore)-$STAMP.sql.gz
  docker exec mariadb sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --routines --events "$1"' _ "$mdb" \
    | gzip > "$mbefore"
  [ "$(gunzip -c "$mbefore" | wc -c)" -gt 0 ] || { L "✗ La copia de la base de MariaDB actual quedó vacía; no sigo" "✗ The copy of the current MariaDB database came out empty; stopping"; exit 1; }
  echo "  ✓ $mbefore ($(du -h "$mbefore" | cut -f1))"
fi
if [ -d "$DATA" ] && [ -d "$SAVED_DATA" ]; then
  out=$ARCHIVE/$APP-$(L archivos-antes-de-restaurar files-before-restore)-$STAMP.tar.gz
  tar czf "$out" -C "$DATA" .
  echo "  ✓ $out ($(du -h "$out" | cut -f1))"
fi

cd "$DIR"
running=$(docker compose ps -q 2> /dev/null || true)
echo "==> $(L "Deteniendo $APP" "Stopping $APP")"
[ -z "$running" ] || docker compose stop -t 15 > /dev/null

load() {  # load <archivo .sql (o .sql.gz)>: reemplaza la base de la app con ese contenido
  docker exec -i postgres sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d postgres' <<SQL
DROP DATABASE IF EXISTS "$db" WITH (FORCE);
CREATE DATABASE "$db" OWNER "$role";
REVOKE ALL ON DATABASE "$db" FROM PUBLIC;
SQL
  # Como el usuario de la app: las tablas quedan suyas.
  { echo "SET ROLE \"$role\";"; if [[ $1 == *.gz ]]; then gunzip -c "$1"; else cat "$1"; fi; } \
    | docker exec -i postgres sh -c "psql -v ON_ERROR_STOP=1 -q -U \"\$POSTGRES_USER\" -d \"$db\"" > /dev/null
}
mload() {  # mload <archivo .sql (o .sql.gz)>: reemplaza la base MariaDB de la app con ese contenido
  # Sus permisos quedan: en MariaDB son del usuario sobre la base, no de la base.
  docker exec -i mariadb sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot' <<SQL
DROP DATABASE IF EXISTS \`$mdb\`;
CREATE DATABASE \`$mdb\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \`$mdb\`.* TO '$muser'@'%';
SQL
  { if [[ $1 == *.gz ]]; then gunzip -c "$1"; else cat "$1"; fi; } \
    | docker exec -i mariadb sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot "$1"' _ "$mdb"
}
start_again() {
  [ -z "$running" ] || docker compose start > /dev/null
}

if [ -n "$db" ]; then
  echo "==> $(L "Reemplazando la base $db" "Replacing database $db")"
  if ! load "$T/app.sql"; then
    L "✗ No se pudo cargar la base del respaldo. Vuelvo a poner la de antes." \
      "✗ Couldn't load the backup's database. Putting the previous one back."
    load "$before" && L "  ✓ Base anterior repuesta" "  ✓ Previous database restored" \
      || L "  ✗ Tampoco pude reponerla: está en $before" "  ✗ Couldn't put it back either: it's in $before"
    start_again
    exit 1
  fi
  echo "  ✓ $(L "base $db restaurada" "database $db restored")"
fi

if [ -n "$mdb" ]; then
  echo "==> $(L "Reemplazando la base $mdb (MariaDB)" "Replacing database $mdb (MariaDB)")"
  if ! mload "$T/app-mariadb.sql"; then
    L "✗ No se pudo cargar la base de MariaDB del respaldo. Vuelvo a poner la de antes." \
      "✗ Couldn't load the backup's MariaDB database. Putting the previous one back."
    mload "$mbefore" && L "  ✓ Base anterior repuesta" "  ✓ Previous database restored" \
      || L "  ✗ Tampoco pude reponerla: está en $mbefore" "  ✗ Couldn't put it back either: it's in $mbefore"
    start_again
    exit 1
  fi
  echo "  ✓ $(L "base $mdb (MariaDB) restaurada" "database $mdb (MariaDB) restored")"
fi

if [ -d "$SAVED_DATA" ]; then
  echo "==> $(L "Reemplazando sus carpetas persistentes" "Replacing its persistent folders")"
  rm -rf "$DATA.restore-new" "$DATA.restore-old"
  cp -a "$SAVED_DATA" "$DATA.restore-new"   # con sus dueños: los del usuario de la imagen
  [ ! -d "$DATA" ] || mv "$DATA" "$DATA.restore-old"
  mv "$DATA.restore-new" "$DATA"
  rm -rf "$DATA.restore-old"
  echo "  ✓ $(L "carpetas restauradas" "folders restored")"
fi

if [ -n "$running" ]; then
  echo "==> $(L "Encendiendo $APP" "Starting $APP")"
  start_again
fi
echo "✓ $(L "$APP quedó como en el respaldo $SNAP. Lo de antes está en $ARCHIVE." \
             "$APP is back to backup $SNAP. What it had before is in $ARCHIVE.")"
