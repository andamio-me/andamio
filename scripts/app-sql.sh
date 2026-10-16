#!/usr/bin/env bash
# Consulta de SOLO LECTURA a la base de una app (andamio app sql, y la consola del panel).
#   app-sql.sh <app>            psql interactivo (necesita una terminal: ssh -t)
#   app-sql.sh <app> --query    la consulta por stdin; el resultado en CSV por stdout
#   app-sql.sh <app> --tables   sus tablas: esquema, nombre, filas (aprox.) y columnas, en CSV
#
# Tres capas para que nada cambie datos:
#  1. Un usuario aparte, <rol>_ro, que solo tiene SELECT en la base de la app: no es su dueño ni
#     superusuario, y no puede pasarse a otro rol. Sin contraseña: solo entra desde dentro del
#     contenedor de PostgreSQL (por red, pg_hba pide contraseña). Sus permisos se ponen al día en
#     cada uso (las tablas nuevas de una migración también se leen).
#  2. Toda transacción suya es de solo lectura (default_transaction_read_only), y cada consulta
#     tiene 5 s como máximo (statement_timeout).
#  3. El resultado sale cortado a 4 MB (el panel muestra 500 filas como máximo).
# Lo corre el usuario de andamio (grupo docker), por SSH. No necesita sudo.
set -euo pipefail

APP=${1:?uso: app-sql.sh <app> [--query|--tables]}
MODE=${2:-}
[[ $APP =~ ^[a-z][a-z0-9-]{1,28}[a-z0-9]$ ]] || { echo "App inválida: $APP" >&2; exit 2; }
ENV=/srv/andamio/infra/apps/$APP/.env
url=$(grep '^DATABASE_URL=' "$ENV" 2> /dev/null | cut -d= -f2- || true)
[ -n "$url" ] || { echo "$APP no tiene base de datos (db: true en su app.yml)" >&2; exit 3; }
db=${url##*/}
role=$(sed -E 's#^postgres(ql)?://([^:]+):.*#\2#' <<< "$url")
[[ $db =~ ^[a-z0-9_]+$ && $role =~ ^[a-z0-9_]+$ ]] || { echo "DATABASE_URL inesperada" >&2; exit 2; }
ro=${role}_ro

# El rol de solo lectura y sus permisos (idempotente; como superusuario, dentro del contenedor).
docker exec -i postgres sh -c 'psql -v ON_ERROR_STOP=1 -X -q -U "$POSTGRES_USER" -d postgres' > /dev/null <<SQL
DO \$\$BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$ro') THEN
    CREATE ROLE "$ro" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
  END IF;
END\$\$;
ALTER ROLE "$ro" SET default_transaction_read_only = on;
ALTER ROLE "$ro" SET statement_timeout = '5s';
ALTER ROLE "$ro" SET idle_in_transaction_session_timeout = '60s';
GRANT CONNECT ON DATABASE "$db" TO "$ro";
\\c "$db"
DO \$\$DECLARE s text;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace
           WHERE nspname NOT LIKE 'pg\_%' AND nspname <> 'information_schema' LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', s, '$ro');
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', s, '$ro');
  END LOOP;
END\$\$;
SQL

psql_ro=(psql -X -U "$ro" -d "$db" -v ON_ERROR_STOP=1)
case $MODE in
  "")
    exec docker exec -it postgres "${psql_ro[@]}" ;;
  --query)
    docker exec -i postgres "${psql_ro[@]}" -q --csv | head -c 4000000 ;;
  --tables)
    docker exec -i postgres "${psql_ro[@]}" -q --csv -c "
      SELECT n.nspname AS schema, c.relname AS name, c.reltuples::bigint AS rows,
             string_agg(a.attname || ' ' || format_type(a.atttypid, a.atttypmod), ', ' ORDER BY a.attnum) AS columns
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
      WHERE c.relkind IN ('r', 'p', 'v', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND n.nspname NOT LIKE 'pg_toast%' AND has_table_privilege(c.oid, 'SELECT')
      GROUP BY 1, 2, 3 ORDER BY 1, 2" < /dev/null ;;
  *)
    echo "Modo desconocido: $MODE" >&2; exit 2 ;;
esac
