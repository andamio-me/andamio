#!/usr/bin/env bash
# Corre una tarea programada de una app (cron: en su app.yml). La lanza su timer de systemd
# (andamio-cron-<app>.<tarea>), o `andamio app cron run` a mano. Usa lo mismo que la app
# (imagen, secretos, redes, carpetas y límites) en un contenedor de una sola vez que se borra
# al terminar, sin tráfico de Traefik. Si falla, avisa con el final de su salida.
#   app-cron.sh <app> <tarea> [--manual]   (--manual: sin aviso ni registro del resultado)
#
# El comando corre tal cual dentro de la imagen (sin su ENTRYPOINT). Con &&, |, ;, > o $,
# pasa por sh -c (la imagen necesita sh: las distroless no lo traen).
set -uo pipefail

app=${1:-} name=${2:-} manual=${3:-}
[[ $app =~ ^[a-z][a-z0-9-]+$ && $name =~ ^[a-z][a-z0-9-]*$ ]] || { echo "uso: app-cron.sh <app> <tarea> [--manual]" >&2; exit 2; }
ENV=/etc/andamio/andamio.env
# shellcheck source=/dev/null   # lo genera Ansible (andamio.env.j2)
[ -r "$ENV" ] && set -a && . "$ENV" && set +a
LNG=${ANDAMIO_LANG:-en}
L() { if [ "$LNG" = es ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
dir=/srv/andamio/infra/apps/$app
cmdfile=/etc/andamio/cron/$app.$name.cmd
LIMIT=${ANDAMIO_CRON_TIMEOUT:-3600}   # segundos

if [ ! -r "$cmdfile" ]; then
  L "La tarea $name de $app no está en el servidor (¿falta andamio app apply $app?)" \
    "Task $name of $app isn't on the server (missing andamio app apply $app?)" >&2; echo >&2; exit 1
fi
if grep -qx 'stopped: true' "$dir/app.yml" 2> /dev/null; then
  L "$app está detenida: $name no corre" "$app is stopped: $name doesn't run"; echo; exit 0
fi
if ! grep -qE '^TAG=.{5,}' "$dir/.env" 2> /dev/null; then
  L "$app todavía no tiene deploy: $name no corre" "$app hasn't been deployed yet: $name doesn't run"; echo; exit 0
fi

cmd=$(cat "$cmdfile")
if [[ $cmd =~ [\&\|\;\<\>\$\`] ]]; then
  argv=(sh -c "$cmd")
else
  mapfile -d '' argv < <(python3 -c 'import shlex, sys; sys.stdout.write("\0".join(shlex.split(sys.argv[1])))' "$cmd")
fi
cname=$app-cron-$name-$(date +%s)
out=$(mktemp)
trap 'docker rm -f "$cname" > /dev/null 2>&1; rm -f "$out"; exit 130' INT TERM   # Ctrl+C: sin restos
start=$(date +%s)
cd "$dir" || exit 1
# El programa va como entrypoint (reemplaza el de la imagen) y el resto como argumentos.
# Sin entrada (< /dev/null): una tarea no lee nada, y compose leyendo la terminal desde
# fuera de primer plano quedaba en pausa para siempre. A mano (--foreground), Ctrl+C la corta.
fg=(); [ "$manual" = --manual ] && fg=(--foreground)
timeout "${fg[@]}" --kill-after=30 "$LIMIT" docker compose run --rm --no-deps -T --name "$cname" --entrypoint "${argv[0]}" \
  --label traefik.enable=false app "${argv[@]:1}" < /dev/null 2>&1 | tee "$out"
rc=${PIPESTATUS[0]}
docker rm -f "$cname" > /dev/null 2>&1 || true   # si el límite de tiempo lo cortó
secs=$(( $(date +%s) - start ))

if [ "$manual" != --manual ]; then
  # Avisa cuando empieza a fallar y cuando vuelve a andar; una tarea cada 2 min que sigue
  # fallando no manda un aviso cada 2 min.
  prev=""
  if [ -n "${STATE_DIRECTORY:-}" ]; then
    read -r prev _ < "$STATE_DIRECTORY/$app.$name" 2> /dev/null || prev=""
    printf '%s %s %s\n' "$rc" "$start" "$secs" > "$STATE_DIRECTORY/$app.$name"
  fi
  if [ "$rc" = 0 ] && [ -n "$prev" ] && [ "$prev" != 0 ]; then
    "$(dirname "$0")/notify.sh" "✓ $(L "Tarea de nuevo bien: $app/$name" "Task working again: $app/$name")" \
      "$(L "Terminó bien en ${secs} s." "Finished fine in ${secs} s.")"
  fi
  if [ "$rc" != 0 ] && { [ -z "$prev" ] || [ "$prev" = 0 ]; }; then
    if [ "$rc" = 124 ]; then
      why=$(L "superó el límite de $((LIMIT / 60)) min y se cortó" "exceeded the $((LIMIT / 60)) min limit and was stopped")
    else
      why=$(L "terminó con código $rc" "exited with code $rc")
    fi
    tail_out=$(sed 's/\x1b\[[0-9;]*m//g' "$out" | tail -n 15 | cut -c1-200)
    "$(dirname "$0")/notify.sh" "❌ $(L "Tarea fallida: $app/$name" "Task failed: $app/$name")" \
      "$why. $(L "Probarla a mano: andamio app cron run $app $name
Si sigue fallando, no vuelvo a avisar hasta que ande." "Try it by hand: andamio app cron run $app $name
If it keeps failing, I won't notify again until it works.")" "$tail_out"
  fi
fi
rm -f "$out"
exit "$rc"
