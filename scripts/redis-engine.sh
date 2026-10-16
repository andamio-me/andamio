#!/bin/bash
# Cambia el motor de Redis de andamio (redis, valkey o dragonfly) sin perder datos. Lo corre
# Ansible (tasks/redis-engine.yml) antes de levantar stacks/data, cuando andamio_redis_engine
# no es el motor que está corriendo.
#
#   redis-engine.sh <motor>
#
#   1. Levanta el motor nuevo aparte (redis-migrar), con su propio volumen vacío.
#   2. Pausa las escrituras en el actual (las lecturas siguen) y copia todo (kv-copy.py): los
#      archivos de un motor no los lee otro.
#   3. Apaga los dos y deja el nuevo como "redis": las apps se reconectan solas.
# Si algo falla antes del paso 3, el actual sigue como estaba. El volumen del anterior queda,
# por si quieres volver (volver es otro cambio de motor, que vuelve a copiar).
set -euo pipefail
new=${1:-}
case $new in
  redis | valkey | dragonfly) ;;
  *) echo "Uso: redis-engine.sh redis|valkey|dragonfly" >&2; exit 2 ;;
esac
infra=$(cd "$(dirname "$0")/.." && pwd)
cd "$infra/stacks/data"

image=$(docker inspect -f '{{.Config.Image}}' redis 2>/dev/null || true)
case $image in
  "") echo "Redis no está corriendo: nada que copiar"; exit 0 ;;
  *dragonfly*) old=dragonfly ;;
  *valkey*) old=valkey ;;
  *) old=redis ;;
esac
[ "$old" != "$new" ] || exit 0
echo "==> Motor de Redis: $old → $new (copia los datos; las escrituras esperan unos segundos)"

# La clave del admin, para leer y escribir todo (nunca se muestra).
REDIS_PASSWORD=$(sed -n 's/^REDIS_PASSWORD=//p' .env)
export REDIS_PASSWORD
ip() { docker inspect -f '{{(index .NetworkSettings.Networks "data").IPAddress}}' "$1"; }
undo() {
  docker exec redis redis-cli CLIENT UNPAUSE > /dev/null 2>&1 || true
  docker rm -f redis-migrar > /dev/null 2>&1 || true
  echo "✗ No se cambió el motor: $old sigue como estaba" >&2
}
trap undo ERR

# Lo que un cambio anterior dejó en el volumen del motor nuevo ya es viejo: se empieza vacío.
docker rm -f redis-migrar > /dev/null 2>&1 || true
if docker volume inspect "data_${new}data" > /dev/null 2>&1; then
  docker volume rm "data_${new}data" > /dev/null
  echo "  (borré data_${new}data, de un cambio de motor anterior: sus datos eran viejos)"
fi

# 1. El nuevo, aparte, con la definición del compose (su imagen, sus opciones, su volumen).
COMPOSE_PROFILES=$new docker compose run -d --name redis-migrar --no-deps "$new" > /dev/null
for _ in $(seq 1 30); do
  docker exec redis-migrar redis-cli ping 2> /dev/null | grep -q PONG && break
  sleep 1
done
docker exec redis-migrar redis-cli ping | grep -q PONG
# Que pida clave: sin su archivo de usuarios, un motor podría quedar abierto. Si no la pide, no sigue.
docker exec redis-migrar sh -c 'unset REDISCLI_AUTH; redis-cli ping' 2>&1 | grep -q NOAUTH \
  || { echo "✗ $new respondió sin pedir clave: no cargó sus usuarios" >&2; false; }

# 2. Sin escrituras nuevas en el actual mientras se copia (hasta 5 minutos), y copiar.
docker exec redis redis-cli CLIENT PAUSE 300000 WRITE > /dev/null
# Desde el servidor, a sus IPs en la red data; si no llega (Docker Desktop, rootless), desde un
# contenedor en esa misma red.
rc=0
python3 "$infra/scripts/kv-copy.py" "$(ip redis):6379" "$(ip redis-migrar):6379" || rc=$?
if [ "$rc" = 3 ]; then
  docker run --rm --network data -e REDIS_PASSWORD -v "$infra/scripts/kv-copy.py:/kv-copy.py:ro" \
    python:3.12-alpine python3 /kv-copy.py redis:6379 redis-migrar:6379
elif [ "$rc" != 0 ]; then
  false   # (dispara undo)
fi

# 3. El nuevo guarda en disco al apagarse; el actual se apaga y su volumen queda.
docker stop -t 30 redis-migrar > /dev/null
docker rm redis-migrar > /dev/null
trap - ERR
docker stop -t 30 redis > /dev/null
docker rm redis > /dev/null
COMPOSE_PROFILES=$new docker compose up -d --wait "$new"
docker exec redis sh -c 'unset REDISCLI_AUTH; redis-cli ping' 2>&1 | grep -q NOAUTH \
  || { echo "✗ $new respondió sin pedir clave: revisa redis-acl/users.acl" >&2; exit 1; }
echo "✓ Motor de Redis cambiado: $new, con los datos de $old (su volumen, data_${old}data, queda)"
