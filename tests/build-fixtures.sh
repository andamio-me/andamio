#!/usr/bin/env bash
# Construye y arranca el Dockerfile que andamio genera para cada app de tests/fixtures/apps:
# que la imagen se construya, corra sin root y responda en su puerto. Necesita Docker; lo
# corre el CI en cada push (tests/test_scaffold.py revisa el texto; esto, que funcione).
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
export ANDAMIO_LANG=es
work=$(mktemp -d)
trap 'docker rm -f andamio-fixture > /dev/null 2>&1 || true; rm -rf "$work"' EXIT
fail=0

for src in "$ROOT"/tests/fixtures/apps/*/; do
  kind=$(basename "$src")
  dir=$work/$kind
  cp -r "$src" "$dir"
  # Sin Dockerfile: andamio propone uno. Dos "sí": el comando de arranque y el Dockerfile.
  printf 's\ns\n' | "$ROOT/bin/andamio" _scaffold "$dir" "" "$work/$kind.out" > /dev/null
  port=$(sed -n 's/^port=//p' "$work/$kind.out")
  echo "==> $kind (puerto $port)"
  if ! docker build -q -t "andamio-fixture-$kind" "$dir" > "$work/build.log" 2>&1; then
    echo "✗ $kind: no construye"; tail -30 "$work/build.log"; fail=1; continue
  fi
  user=$(docker image inspect -f '{{.Config.User}}' "andamio-fixture-$kind")
  if [[ -z $user || $user == root || $user == 0 ]]; then
    echo "✗ $kind: la imagen corre como root"; fail=1
  fi
  docker run -d --name andamio-fixture -p "127.0.0.1:18080:$port" "andamio-fixture-$kind" > /dev/null
  ok=""
  for _ in $(seq 30); do
    if curl -fsS http://127.0.0.1:18080/ 2> /dev/null | grep -q andamio-ok; then ok=1; break; fi
    sleep 1
  done
  if [ -n "$ok" ]; then
    echo "✓ $kind: construye, corre como $user y responde"
  else
    echo "✗ $kind: no respondió en el puerto $port"; docker logs andamio-fixture 2>&1 | tail -20; fail=1
  fi
  docker rm -f andamio-fixture > /dev/null
done
exit "$fail"
