#!/usr/bin/env bash
# Compila la interfaz del panel (ui-src/, Svelte + TypeScript) a ui/, que es lo que sirve
# `andamio ui`. Corre en un contenedor de Node: no hace falta Node en tu máquina. Solo lo
# necesita quien cambia la interfaz; ui/ ya compilado va en el repo. El CI comprueba que ui/
# corresponda exactamente a ui-src/.
#   tools/ui-build.sh           revisa tipos y compila
#   tools/ui-build.sh --check   además, falla si ui/ quedó distinto de lo que está en git
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=node:24-alpine
# La caché de pnpm vive en el contenedor (/tmp), no en tu repo.
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -e COREPACK_ENABLE_DOWNLOAD_PROMPT=0 -e npm_config_store_dir=/tmp/pnpm-store \
  -v "$ROOT:/w" -w /w/ui-src "$IMAGE" \
  sh -c 'corepack pnpm install --frozen-lockfile --reporter=silent && corepack pnpm run check && corepack pnpm run build'
if [ "${1:-}" = --check ] && [ -n "$(git -C "$ROOT" status --porcelain -- ui)" ]; then
  echo "✗ ui/ no corresponde a ui-src/: corre tools/ui-build.sh y sube ui/" >&2
  git -C "$ROOT" status --short -- ui >&2
  exit 1
fi
echo "✓ ui/ compilada"
