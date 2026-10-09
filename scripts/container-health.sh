#!/usr/bin/env bash
# Publica la salud (HEALTHCHECK) de cada contenedor para el textfile collector
# de node-exporter. Corre cada 30 s vía andamio-container-health.timer.
# Así el dashboard la lee de Prometheus sin tocar el socket de Docker.
set -euo pipefail

dir=/var/lib/node_exporter/textfile
tmp=$(mktemp "$dir/.containers.XXXXXX")
trap 'rm -f "$tmp"' EXIT

{
  echo "# HELP andamio_container_health Salud según HEALTHCHECK. status: healthy, unhealthy, starting, none."
  echo "# TYPE andamio_container_health gauge"
  mapfile -t ids < <(docker ps -q)
  if ((${#ids[@]})); then
    docker inspect --format '{{slice .Name 1}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${ids[@]}" |
      while read -r name status; do
        printf 'andamio_container_health{name="%s",status="%s"} 1\n' "$name" "$status"
      done
  fi
} > "$tmp"

chmod 644 "$tmp"
mv "$tmp" "$dir/containers.prom"   # atómico: node-exporter nunca lee un archivo a medias
trap - EXIT
