#!/usr/bin/env bash
# Consulta de SOLO LECTURA a la base MariaDB de una app (andamio app sql, y la consola del panel).
# Lo mismo que app-sql.sh hace con PostgreSQL:
#   app-sql-mysql.sh <app>            cliente interactivo (necesita una terminal: ssh -t)
#   app-sql-mysql.sh <app> --query    la consulta por stdin; el resultado en TSV (--batch) por stdout
#
# Tres capas para que nada cambie datos:
#  1. Un usuario aparte, <usuario>_ro@localhost, que solo tiene SELECT y SHOW VIEW en la base de
#     la app. Sin contraseña: «localhost» es el socket de dentro del contenedor de MariaDB (con
#     skip-name-resolve, por red nadie es localhost), así que solo entra con docker exec.
#  2. Cada consulta tiene 5 s como máximo y el usuario 3 conexiones (MAX_STATEMENT_TIME,
#     MAX_USER_CONNECTIONS).
#  3. El resultado sale cortado a 4 MB (el panel muestra 500 filas como máximo).
# Lo corre el usuario de andamio (grupo docker), por SSH. No necesita sudo.
set -euo pipefail

APP=${1:?uso: app-sql-mysql.sh <app> [--query]}
MODE=${2:-}
[[ $APP =~ ^[a-z][a-z0-9-]{1,28}[a-z0-9]$ ]] || { echo "App inválida: $APP" >&2; exit 2; }
ENV=/srv/andamio/infra/apps/$APP/.env
url=$(grep '^MYSQL_URL=' "$ENV" 2> /dev/null | cut -d= -f2- || true)
[ -n "$url" ] || { echo "$APP no tiene MariaDB (mysql: true en su app.yml)" >&2; exit 3; }
db=${url##*/}
user=$(sed -E 's#^mysql://([^:]+):.*#\1#' <<< "$url")
[[ $db =~ ^[a-z0-9_]+$ && $user =~ ^[a-z0-9_]+$ ]] || { echo "MYSQL_URL inesperada" >&2; exit 2; }
ro=${user}_ro

# El usuario de solo lectura y sus permisos (idempotente; como root, dentro del contenedor).
docker exec -i mariadb sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot' > /dev/null <<SQL
CREATE USER IF NOT EXISTS '$ro'@'localhost';
ALTER USER '$ro'@'localhost' WITH MAX_STATEMENT_TIME 5 MAX_USER_CONNECTIONS 3;
GRANT SELECT, SHOW VIEW ON \`$db\`.* TO '$ro'@'localhost';
SQL

client=(mariadb -u "$ro" --database "$db")
case $MODE in
  "")
    exec docker exec -it mariadb "${client[@]}" ;;
  --query)
    docker exec -i mariadb "${client[@]}" --batch | head -c 4000000 ;;
  *)
    echo "Modo desconocido: $MODE" >&2; exit 2 ;;
esac
