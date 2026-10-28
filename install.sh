#!/bin/sh
# andamio: installer for YOUR computer (not for the server). Read it before running it:
# it clones andamio into ~/andamio and starts `bin/andamio setup`, which asks before
# installing anything. It never runs as root (it asks for sudo only to install packages).
#
#   curl -fsSL https://raw.githubusercontent.com/andamio-me/andamio/main/install.sh | sh
#
# Instalador para TU computador (no para el servidor). Léelo antes de correrlo: clona
# andamio en ~/andamio y abre `bin/andamio setup`, que pregunta antes de instalar nada.
set -eu

REPO="${ANDAMIO_REPO:-https://github.com/andamio-me/andamio.git}"
DIR="${ANDAMIO_DIR:-$HOME/andamio}"

es() { case "${ANDAMIO_LANG:-${LANG:-}}" in es*) return 0 ;; *) return 1 ;; esac; }
say() { if es; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
die() { say "✗ $1" "✗ $2" >&2; exit 1; }

# Las preguntas de setup se leen de la terminal: con `curl | sh`, stdin es este script.
[ -r /dev/tty ] || die "Hace falta una terminal (corre esto en una terminal, no en un script)." \
                       "A terminal is needed (run this in a terminal, not from a script)."

if [ "$(id -u)" = 0 ]; then
  die "No lo corras como root: andamio va en TU computador, con tu usuario (pide sudo solo para instalar paquetes). Si estás en el VPS: esto no va ahí, va en tu máquina." \
      "Don't run it as root: andamio goes on YOUR computer, as your user (it asks for sudo only to install packages). If you're on the VPS: this doesn't go there, it goes on your machine."
fi

case "$(uname -s)" in
  Linux | Darwin) ;;
  *) die "Necesitas Linux, macOS o WSL. En Windows: https://learn.microsoft.com/windows/wsl/install" \
         "You need Linux, macOS or WSL. On Windows: https://learn.microsoft.com/windows/wsl/install" ;;
esac

# Lo mínimo para bajar andamio y correrlo: git y python3. Todo lo demás lo instala setup.
if ! command -v git > /dev/null 2>&1 || ! command -v python3 > /dev/null 2>&1; then
  if command -v apt-get > /dev/null 2>&1; then
    say "Instalo git y python3 (te pide la contraseña de sudo de este computador)..." \
        "Installing git and python3 (asks for this computer's sudo password)..."
    # noninteractive: paquetes como tzdata no deben quedarse preguntando.
    sudo apt-get update -qq < /dev/tty \
      && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git python3 < /dev/tty
  elif [ "$(uname -s)" = Darwin ]; then
    die "Instala primero las herramientas de desarrollo de Apple: xcode-select --install (y vuelve a correr esto)." \
        "First install Apple's developer tools: xcode-select --install (then run this again)."
  else
    die "Instala git y python3 y vuelve a correr esto." "Install git and python3 and run this again."
  fi
fi

if [ -d "$DIR/.git" ]; then
  say "Actualizo andamio en $DIR" "Updating andamio in $DIR"
  git -C "$DIR" pull -q --ff-only
else
  say "Bajo andamio en $DIR" "Getting andamio into $DIR"
  git clone -q "$REPO" "$DIR"
fi

cd "$DIR"
exec bin/andamio setup < /dev/tty
