#!/usr/bin/env bash
# Deploy sin caída de una app del homelab.
# Uso: deploy-app.sh <app> [sha] [versión]
#   Desde CI (forced command), sha y versión llegan en SSH_ORIGINAL_COMMAND.
set -euo pipefail

APP=${1:?uso: deploy-app.sh <app> [sha] [versión]}
read -r SHA VERSION _ <<< "${SSH_ORIGINAL_COMMAND:-${2:-} ${3:-}}"

# Validar TODO lo que llega de afuera (se usa en rutas, comandos y SQL)
[[ $APP =~ ^[a-z0-9-]+$ ]]          || { echo "App inválida"; exit 1; }
[[ ${SHA:-} =~ ^[0-9a-f]{40}$ ]]     || { echo "SHA inválido (40 hex)"; exit 1; }
VERSION=${VERSION:-${SHA:0:7}}
[[ $VERSION =~ ^[A-Za-z0-9._-]{1,40}$ ]] || { echo "Versión inválida"; exit 1; }

INFRA=/srv/homelab/infra
DIR=$INFRA/apps/$APP
[ -f "$DIR/compose.yaml" ] || { echo "App desconocida: $APP"; exit 1; }
# andamio app stop: mientras esté detenida, un push no la vuelve a levantar.
if grep -qx 'stopped: true' "$DIR/app.yml" 2> /dev/null; then
  echo "⏸ $APP está detenida: no la despliego. Para volver: andamio app start $APP"; exit 1
fi

notify() {
  [ -r /etc/homelab/telegram.env ] || { echo "⚠ Sin aviso: no puedo leer /etc/homelab/telegram.env" >&2; return 0; }
  ( set -a; . /etc/homelab/telegram.env; set +a; echo "$1" | "$INFRA/scripts/telegram-send.sh" ) || true
}
record() {  # registra el deploy en la tabla deployments de la app y en el registro central
  # Apps sin base (sin DATABASE_URL) no registran: grep sin resultado no debe cortar el script (set -e).
  # Los valores ya están validados arriba (APP, SHA, VERSION); el estado es fijo.
  local url
  url=$(grep '^DATABASE_URL=' .env | cut -d= -f2- || true)
  [ -z "$url" ] || docker run --rm --network data postgres:18.6-alpine psql -q "$url" \
    -c "INSERT INTO deployments (version, commit_sha, status) VALUES ('$VERSION', '$SHA', '$1')" || true
  # Registro central: la base del dashboard junta los deploys de todas las apps.
  # El dashboard ya quedó registrado arriba (su tabla ES el registro central).
  [ "$APP" = homelab-dashboard ] && return 0
  url=$(grep '^DATABASE_URL=' "$INFRA/apps/homelab-dashboard/.env" 2>/dev/null | cut -d= -f2- || true)
  [ -n "$url" ] || return 0
  docker run --rm --network data postgres:18.6-alpine psql -q "$url" \
    -c "INSERT INTO deployments (app, version, commit_sha, status) VALUES ('$APP', '$VERSION', '$SHA', '$1')" || true
}
# Espera hasta 90 s a que el contenedor esté sano. Sirve para apps de cualquier
# lenguaje: no exige herramientas dentro de la imagen. En orden:
#  1. label andamio.health (de "health:" en app.yml): GET HTTP a esa ruta, desde el
#     host, a la IP del contenedor en la red proxy y al puerto de Traefik;
#  2. HEALTHCHECK propio de la imagen;
#  3. ninguno: sano si lleva 10 s corriendo sin reiniciarse.
wait_healthy() {  # wait_healthy <contenedor>
  local c=$1 path port ip health running restarts up_since=""
  path=$(docker inspect -f '{{index .Config.Labels "andamio.health"}}' "$c" 2>/dev/null || true)
  # El puerto es el mismo que usa Traefik (label ...loadbalancer.server.port).
  port=$(docker inspect "$c" 2>/dev/null | grep -oE '"traefik\.http\.services\.[^"]+\.loadbalancer\.server\.port": "[0-9]+"' \
    | grep -oE '[0-9]+"$' | tr -d '"' | head -n 1)
  for _ in $(seq 1 45); do
    read -r health running restarts <<< "$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.State.Running}} {{.RestartCount}}' "$c" 2>/dev/null || echo "gone false 0")"
    [ "$health" = gone ] && return 1
    [ "$health" = unhealthy ] && return 1
    if [ "$running" = true ] && [ "$restarts" = 0 ]; then
      if [ -n "$path" ] && [ -n "$port" ]; then
        ip=$(docker inspect -f '{{with index .NetworkSettings.Networks "proxy"}}{{.IPAddress}}{{end}}' "$c")
        curl -fsS -m 3 -o /dev/null "http://$ip:$port$path" 2> /dev/null && return 0
      elif [ "$health" = healthy ]; then
        return 0
      elif [ "$health" = none ]; then
        up_since=${up_since:-$SECONDS}
        [ $(( SECONDS - up_since )) -ge 10 ] && return 0
      fi
    else
      up_since=""
      # Se reinició o se cayó: con restart: unless-stopped vuelve, pero no está sano.
      [ "$restarts" != 0 ] && return 1
    fi
    sleep 2
  done
  return 1
}
fail() {  # deja la versión anterior en .env, registra y avisa
  sed -i "s/^TAG=.*/TAG=$PREV/" .env
  record failed
  notify "❌ Deploy de $APP $VERSION falló: $1. Sigue corriendo la versión anterior."
  echo "❌ $1"; exit 1
}

# Deploys de apps distintas pueden llegar a la vez (cada app tiene su propia cola en el
# CI): dos "git pull" simultáneos en el mismo repo fallan ("Cannot fast-forward to
# multiple branches", 2026-10-08). El candado los hace de a uno; el resto del deploy
# sigue en paralelo.
flock "$INFRA/.git/homelab-pull.lock" git -C "$INFRA" pull --ff-only --quiet origin main
cd "$DIR"
PREV=$(grep '^TAG=' .env | cut -d= -f2)
echo "==> $APP: ${PREV:0:7} -> ${SHA:0:7} ($VERSION)"
sed -i "s/^TAG=.*/TAG=$SHA/" .env

# Bajar TODAS las imágenes (también la de migraciones, que tiene perfil) antes de
# tocar nada. GHCR a veces corta la conexión a mitad de una capa: hasta 3 intentos.
for intento in 1 2 3; do
  docker compose --profile migrate pull --quiet && break
  [ "$intento" = 3 ] && fail "no se pudieron bajar las imágenes de GHCR (red), 3 intentos"
  echo "⚠ La descarga falló (intento $intento/3); reintento en $((intento * 10)) s"
  sleep $((intento * 10))
done

if docker compose config --profiles | grep -qx migrate; then
  echo "==> Migraciones"
  docker compose run --rm migrate || fail "las migraciones fallaron"
fi

echo "==> Arrancando la versión nueva junto a la actual"
OLD=$(docker compose ps -q app)
docker compose up -d --no-deps --no-recreate --scale app=$(( $(wc -w <<< "$OLD") + 1 )) app
NEW=$(docker compose ps -q app | grep -vxF -f <(printf '%s\n' $OLD) || true)
[ -n "$NEW" ] || fail "no se creó el contenedor nuevo"

echo "==> Esperando el healthcheck de ${NEW:0:12}"
if ! wait_healthy "$NEW"; then
  docker logs --tail 30 "$NEW" 2>&1 || true
  docker rm -f "$NEW" > /dev/null
  fail "la versión nueva no quedó sana"
fi

# Worker (si la app tiene uno): se reemplaza cuando la web nueva ya está sana y
# antes de apagar la vieja. Si el worker nuevo no queda sano, todo vuelve atrás.
if docker compose config --services | grep -qx worker; then
  echo "==> Reemplazando el worker"
  docker compose up -d --no-deps worker
  WORKER=$(docker compose ps -q worker)
  echo "==> Esperando el latido de ${WORKER:0:12}"
  if ! wait_healthy "$WORKER"; then
    docker logs --tail 30 "$WORKER" 2>&1 || true
    docker rm -f "$NEW" > /dev/null
    sed -i "s/^TAG=.*/TAG=$PREV/" .env
    if [ -n "$PREV" ]; then docker compose up -d --no-deps worker; else docker compose rm -sf worker; fi
    fail "el worker nuevo no quedó sano"
  fi
fi

if [ -n "$OLD" ]; then
  echo "==> Apagando la versión anterior"
  docker stop -t 15 $OLD > /dev/null && docker rm $OLD > /dev/null
fi

record success
notify "✅ $APP $VERSION desplegada (${SHA:0:7})"
echo "✅ $APP $VERSION en producción"
