#!/usr/bin/env bash
# Corre los tests de andamio (tests/). La primera vez crea un entorno con pytest en
# ~/.cache/andamio/tests-venv (no toca tu Python). El CI corre esto mismo.
#
#   tools/tests.sh              todos
#   tools/tests.sh -k update    solo los que coincidan (acepta cualquier opción de pytest)
#
# Construir y arrancar de verdad los Dockerfiles generados (con Docker): tests/build-fixtures.sh
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENV=${XDG_CACHE_HOME:-$HOME/.cache}/andamio/tests-venv
PYTEST=8.3.5
PYYAML=6.0.2
JINJA2=3.1.6   # la plantilla del compose (tests/test_compose.py), como la usa Ansible

if ! "$VENV/bin/python" -c "import pytest, yaml, jinja2; assert pytest.__version__ == '$PYTEST'" 2> /dev/null; then
  echo "==> Entorno de tests (una vez): pytest $PYTEST" >&2
  rm -rf "$VENV"
  python3 -m venv "$VENV" \
    || { echo "✗ No pude crear el entorno (en Ubuntu: sudo apt install python3-venv)" >&2; exit 1; }
  "$VENV/bin/pip" install -q --disable-pip-version-check "pytest==$PYTEST" "pyyaml==$PYYAML" "jinja2==$JINJA2"
fi
# bin/andamio corre con el python3 del PATH: el del entorno, que tiene PyYAML.
export PATH=$VENV/bin:$PATH
cd "$ROOT"
exec python -m pytest -p no:cacheprovider tests "$@"
