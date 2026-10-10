#!/usr/bin/env bash
# Deploy sin caída de una app de andamio.
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

INFRA=/srv/andamio/infra
DIR=$INFRA/apps/$APP
# Idioma de los mensajes (los ve quien despliega, en la pestaña Actions): el del servidor.
LNG=$(sed -n 's/^ANDAMIO_LANG=//p' /etc/andamio/andamio.env 2> /dev/null)
# App cuya base junta los deploys de todas (andamio_dashboard_app; vacío = ninguna).
DASH=$(sed -n 's/^ANDAMIO_DASHBOARD_APP=//p' /etc/andamio/andamio.env 2> /dev/null)
L() { if [ "${LNG:-en}" = es ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
[ -f "$DIR/compose.yaml" ] || { echo "App desconocida: $APP"; exit 1; }
# andamio app stop: mientras esté detenida, un push no la vuelve a levantar.
if grep -qx 'stopped: true' "$DIR/app.yml" 2> /dev/null; then
  echo "⏸ $APP está detenida: no la despliego. Para volver: andamio app start $APP"; exit 1
fi

notify() {
  [ -e /etc/andamio/telegram.env ] || return 0   # Telegram no activado: nada que avisar
  [ -r /etc/andamio/telegram.env ] || { echo "⚠ $(L "Sin aviso: no puedo leer" "No notice: can't read") /etc/andamio/telegram.env" >&2; return 0; }
  ( set -a; . /etc/andamio/telegram.env; set +a; echo "$1" | "$INFRA/scripts/telegram-send.sh" ) || true
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
  [ -n "$DASH" ] && [ "$APP" != "$DASH" ] || return 0
  url=$(grep '^DATABASE_URL=' "$INFRA/apps/$DASH/.env" 2>/dev/null | cut -d= -f2- || true)
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
  echo "❌ $1. $(L "Sigue corriendo la versión anterior" "The previous version keeps running")."; exit 1
}

# Por qué no quedó sana una versión: los errores típicos de una app que no está lista para
# un servidor, con su arreglo. Escribe líneas "💡" (el pipeline las muestra arriba de la corrida).
explain() {  # explain <contenedor>
  local c=$1 logs port path state var
  logs=$(docker logs --tail 80 "$c" 2>&1 || true)
  port=$(docker inspect "$c" 2> /dev/null | grep -oE '"traefik\.http\.services\.[^"]+\.loadbalancer\.server\.port": "[0-9]+"' \
    | grep -oE '[0-9]+"$' | tr -d '"' | head -n 1)
  path=$(docker inspect -f '{{index .Config.Labels "andamio.health"}}' "$c" 2> /dev/null || true)
  state=$(docker inspect -f '{{.State.Status}} {{.RestartCount}}' "$c" 2> /dev/null || echo "gone 0")
  local found=0
  hint() { echo "💡 $*"; found=1; }
  if grep -qiE '(listen|running|serving|started|bound).*(127\.0\.0\.1|localhost)' <<< "$logs"; then
    hint "$(L "Tu app escucha en 127.0.0.1/localhost: dentro del contenedor nadie más la alcanza. Haz que escuche en 0.0.0.0 (puerto $port)." \
              "Your app listens on 127.0.0.1/localhost: inside the container nothing else can reach it. Make it listen on 0.0.0.0 (port $port).")"
  fi
  if grep -qiE 'EADDRINUSE|address already in use' <<< "$logs"; then
    hint "$(L "El puerto ya está en uso dentro del contenedor: ¿la app arranca dos servidores?" "The port is already in use inside the container: does the app start two servers?")"
  fi
  var=$(grep -oE "KeyError: '[A-Z][A-Z0-9_]+'|[A-Z][A-Z0-9_]{2,} (is not set|is required|is missing|must be set)|(Missing|missing|Undefined|undefined) (environment )?variable:? ?[A-Z][A-Z0-9_]{2,}" <<< "$logs" \
        | grep -oE '[A-Z][A-Z0-9_]{2,}' | grep -vE '^(KEY|ERROR|MISSING)$' | head -n 1 || true)
  if [ -n "$var" ]; then
    hint "$(L "Falta la variable $var. Agrégala: andamio app secret set $APP $var" "Variable $var is missing. Add it: andamio app secret set $APP $var")"
  fi
  if grep -qE "ModuleNotFoundError|No module named|Cannot find module|ERR_MODULE_NOT_FOUND|cannot find package" <<< "$logs"; then
    hint "$(L "Falta una dependencia: agrégala a requirements.txt / package.json / go.mod (en la imagen solo está lo que declaras)." \
              "A dependency is missing: add it to requirements.txt / package.json / go.mod (the image only has what you declare).")"
  fi
  if grep -qE "EACCES|Permission denied|Read-only file system" <<< "$logs"; then
    hint "$(L "La app intenta escribir donde no puede (corre sin root). Escribe en /tmp; lo que deba durar, en la base de datos." \
              "The app tries to write where it can't (it runs without root). Write to /tmp; whatever must last, to the database.")"
  fi
  if [ -z "$(tr -d '[:space:]' <<< "$logs")" ] && [[ $state != running* ]]; then
    hint "$(L "La app se cierra sin escribir nada: revisa el comando de arranque (CMD) de tu Dockerfile." \
              "The app exits without printing anything: check your Dockerfile's start command (CMD).")"
  fi
  if [ "$found" = 0 ] && [[ $state == "running 0" ]] && [ -n "$path" ]; then
    hint "$(L "La app corre pero no respondió en http://<contenedor>:$port$path en 90 s: ¿escucha en el puerto $port (port: en app.yml) y en 0.0.0.0? ¿esa ruta responde 200?" \
              "The app runs but didn't answer at http://<container>:$port$path within 90 s: does it listen on port $port (port: in app.yml) and on 0.0.0.0? Does that path return 200?")"
  fi
}

# Deploys de apps distintas pueden llegar a la vez (cada app tiene su propia cola en el
# CI): dos "git pull" simultáneos en el mismo repo fallan ("Cannot fast-forward to
# multiple branches", 2026-10-08). El candado los hace de a uno; el resto del deploy
# sigue en paralelo.
flock "$INFRA/.git/andamio-pull.lock" git -C "$INFRA" pull --ff-only --quiet origin main
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

# Carpetas persistentes (volumes: en app.yml): del usuario de la imagen nueva.
"$INFRA/scripts/app-volumes.sh" "$APP" || fail "$(L "no pude preparar sus carpetas persistentes" "couldn't prepare its persistent folders")"

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
  echo "--- $(L "últimos logs de la versión nueva" "last logs of the new version") ---"
  docker logs --tail 30 "$NEW" 2>&1 || true
  echo "---"
  explain "$NEW"
  docker rm -f "$NEW" > /dev/null
  fail "$(L "la versión nueva no quedó sana" "the new version didn't become healthy")"
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
