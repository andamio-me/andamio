#!/usr/bin/env bash
# Crea las redes compartidas de andamio. Idempotente.
set -euo pipefail

create() {
  local name=$1; shift
  if docker network inspect "$name" > /dev/null 2>&1; then
    echo "= $name ya existe"
  else
    docker network create "$@" "$name" > /dev/null
    echo "+ $name creada"
  fi
}

create proxy
create data --internal
create monitoring --internal
