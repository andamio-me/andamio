#!/usr/bin/env bash
# Crea un usuario y una base de datos para una app. Uso: pg-create-app.sh <app>
set -euo pipefail

APP=${1:?uso: pg-create-app.sh <app>}
[[ $APP =~ ^[a-z][a-z0-9_]{1,30}$ ]] || { echo "Nombre inválido: minúsculas, números y _"; exit 1; }
PASS=$(openssl rand -hex 24)

docker exec -i postgres sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d postgres' << SQL
CREATE ROLE "$APP" LOGIN PASSWORD '$PASS';
CREATE DATABASE "$APP" OWNER "$APP";
REVOKE ALL ON DATABASE "$APP" FROM PUBLIC;
SQL

echo "App '$APP' creada. Guarda esta línea en el .env de la app:"
echo "DATABASE_URL=postgres://$APP:$PASS@postgres:5432/$APP"
