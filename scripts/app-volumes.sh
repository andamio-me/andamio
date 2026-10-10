#!/usr/bin/env bash
# Carpetas persistentes de una app (volumes: en app.yml): que existan y sean del usuario con
# el que corre su imagen. Una carpeta nueva es de quien la crea, y una app sin root no podría
# escribir en ella. Viven en /srv/andamio/data/apps/<app>/, dentro del backup diario.
#   app-volumes.sh <app> [TAG]   (TAG: la versión que va a correr; por defecto, la actual)
# Lo llaman deploy-app.sh (antes de arrancar una versión) y Ansible (al aplicar la app).
set -euo pipefail

APP=${1:?uso: app-volumes.sh <app> [TAG]}
[[ $APP =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || { echo "App inválida: $APP" >&2; exit 1; }
DIR=/srv/andamio/infra/apps/$APP
ROOT=/srv/andamio/data/apps/$APP
cd "$DIR"

TAG=${2:-$(sed -n 's/^TAG=//p' .env 2> /dev/null)}
[ -n "$TAG" ] || exit 0   # app nueva, todavía sin imagen: el primer deploy lo hace

# Las carpetas del host que montan sus servicios (solo las de andamio).
mapfile -t MOUNTS < <(TAG=$TAG docker compose config --format json | python3 -c '
import json, sys
for s in json.load(sys.stdin)["services"].values():
    for v in s.get("volumes", []):
        if v.get("type") == "bind" and v["source"].startswith(sys.argv[1] + "/"):
            print(v["source"])' "$ROOT" | sort -u)
[ ${#MOUNTS[@]} -gt 0 ] || exit 0

# El usuario de la imagen: USER del Dockerfile (número, nombre o vacío = root).
IMAGE=$(TAG=$TAG docker compose config --images | head -n 1)
user=$(docker image inspect -f '{{.Config.User}}' "$IMAGE")
user=${user%%:*}
if [ -z "$user" ] || [ "$user" = root ] || [ "$user" = 0 ]; then
  uid=0 gid=0
elif [[ $user =~ ^[0-9]+$ ]]; then
  uid=$user gid=$user
else
  # Un nombre: su uid sale del /etc/passwd de la imagen (sin ejecutarla).
  cid=$(docker create "$IMAGE")
  line=$(docker cp "$cid:/etc/passwd" - 2> /dev/null | tar -xO | grep "^$user:" || true)
  docker rm "$cid" > /dev/null
  [ -n "$line" ] || { echo "No encuentro el usuario $user en la imagen $IMAGE" >&2; exit 1; }
  uid=$(cut -d: -f3 <<< "$line") gid=$(cut -d: -f4 <<< "$line")
fi

for m in "${MOUNTS[@]}"; do
  mkdir -p "$m"
  [ "$(stat -c %u "$m")" = "$uid" ] && continue
  # Cambiar el dueño necesita root: un contenedor de un instante, con una imagen que el
  # servidor ya tiene (la de PostgreSQL, que también usa deploy-app.sh).
  docker run --rm -u 0 -v "$m:/v" --entrypoint chown postgres:18.6-alpine -R "$uid:$gid" /v
  echo "✓ $m es de uid $uid"
done
