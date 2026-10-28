#!/usr/bin/env bash
# Runner propio de GitHub Actions en esta máquina (WSL), para repos PRIVADOS: sus corridas no
# gastan minutos de Actions. Nunca en el VPS de producción ni para repos públicos (cualquiera
# con un PR correría código aquí).
#
#   tools/runner.sh add <dueño/repo>...    instala (la primera vez) y registra un runner por repo
#   tools/runner.sh remove <dueño/repo>... lo quita (y el repo vuelve a los runners de GitHub)
#   tools/runner.sh status                 qué runners hay y si están en línea
#
# Cada repo usa este runner solo si tiene la variable de Actions RUNNER=self-hosted (la pone
# `add`, la quita `remove`): sus workflows dicen runs-on: ${{ vars.RUNNER || 'ubuntu-24.04' }}.
# Corre como un usuario aparte (ghrunner), sin acceso a tu carpeta personal (tus llaves SSH,
# age, gh). Pero está en el grupo docker, y Docker equivale a root: solo repos tuyos.
# Pide tu contraseña de sudo (crear el usuario, instalar el servicio).
set -euo pipefail

RUNNER_USER=ghrunner
BASE=/home/$RUNNER_USER

die() { echo "✗ $*" >&2; exit 1; }
ok() { echo "  ✓ $*"; }

repo_dir() { echo "$BASE/${1//\//-}"; }
# La carpeta de ghrunner es privada (750): se mira y se entra con sudo.
as_root() { sudo bash -c "$1" _ "${@:2}"; }

need_repo() {
  [[ $1 =~ ^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$ ]] || die "Repo inválido: $1 (formato dueño/repo)"
  [ "$(gh repo view "$1" --json visibility -q .visibility)" != PUBLIC ] \
    || die "$1 es público: un runner propio ahí dejaría a cualquiera correr código en tu máquina."
}

setup_user() {
  if ! id "$RUNNER_USER" > /dev/null 2>&1; then
    sudo useradd --create-home --shell /bin/bash "$RUNNER_USER"
    ok "usuario $RUNNER_USER creado"
  fi
  getent group docker > /dev/null || die "No hay grupo docker: activa la integración de WSL en Docker Desktop."
  id -nG "$RUNNER_USER" | grep -qw docker || { sudo usermod -aG docker "$RUNNER_USER"; ok "$RUNNER_USER en el grupo docker"; }
  # Lo que los workflows dan por hecho en los runners de GitHub (libatomic1: el binario de pnpm).
  local p missing=()
  for p in jq libatomic1; do dpkg -s "$p" > /dev/null 2>&1 || missing+=("$p"); done
  [ ${#missing[@]} -eq 0 ] || { sudo apt-get install -y -qq "${missing[@]}" > /dev/null; ok "instalado: ${missing[*]}"; }
  [ "$(stat -c %a "$HOME")" = 750 ] || [ "$(stat -c %a "$HOME")" = 700 ] \
    || echo "  ! Tu carpeta $HOME es legible por otros usuarios: chmod 750 $HOME"
}

# La versión más reciente del runner, verificada contra el SHA-256 que publica su release.
download() {
  local dest=$1 rel version file sha
  rel=$(gh api repos/actions/runner/releases/latest)
  version=$(jq -r .tag_name <<< "$rel"); version=${version#v}
  file="actions-runner-linux-x64-$version.tar.gz"
  sha=$(jq -r .body <<< "$rel" | sed -n 's/.*<!-- BEGIN SHA linux-x64 -->\([0-9a-f]\{64\}\)<!-- END SHA linux-x64 -->.*/\1/p')
  [ -n "$sha" ] || die "No encontré el SHA-256 de $file en la release."
  local tmp; tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/$file" "https://github.com/actions/runner/releases/download/v$version/$file"
  echo "$sha  $tmp/$file" | (cd "$tmp" && sha256sum -c - > /dev/null) || die "$file no coincide con su SHA-256."
  sudo -u "$RUNNER_USER" mkdir -p "$dest"
  sudo tar xzf "$tmp/$file" -C "$dest"
  sudo chown -R "$RUNNER_USER:$RUNNER_USER" "$dest"
  rm -rf "$tmp"
  ok "runner $version (SHA-256 verificado)"
}

add() {
  local repo=$1 dir token
  need_repo "$repo"
  dir=$(repo_dir "$repo")
  echo "==> $repo"
  setup_user
  if ! sudo test -f "$dir/.runner"; then
    sudo test -x "$dir/config.sh" || download "$dir"
    # Prueba varias versiones de libicu hasta dar con la de tu Ubuntu: sus "Unable to locate" no son errores.
    sudo test -f "$BASE/.deps-ok" || { sudo "$dir/bin/installdependencies.sh" > /dev/null 2>&1 && sudo touch "$BASE/.deps-ok"; } \
      || die "No pude instalar las dependencias del runner: sudo $dir/bin/installdependencies.sh"
    # El token de registro vale una hora y no se muestra: va de gh a config.sh.
    token=$(gh api -X POST "repos/$repo/actions/runners/registration-token" -q .token)
    sudo -u "$RUNNER_USER" bash -c 'cd "$1" && ./config.sh --unattended --replace --url "https://github.com/$2" \
      --token "$3" --name "$(hostname)-${2#*/}" --labels andamio-pc --work _work > /dev/null' _ "$dir" "$repo" "$token"
    ok "registrado en $repo"
  fi
  # El PATH de los jobs (el runner lo lee de .path): con ~/.local/bin, donde pipx deja lo que
  # instalan (shellcheck, ansible-lint), como en los runners de GitHub.
  local path="$BASE/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  if [ "$(sudo cat "$dir/.path" 2> /dev/null)" != "$path" ]; then
    echo "$path" | sudo -u "$RUNNER_USER" tee "$dir/.path" > /dev/null
    as_root 'cd "$1" && ./svc.sh stop > /dev/null 2>&1; ./svc.sh start > /dev/null 2>&1' "$dir" || true
    ok "PATH con ~/.local/bin"
  fi
  if ! systemctl list-unit-files 'actions.runner.*' --no-legend | grep -q "${repo//\//-}"; then
    as_root 'cd "$1" && ./svc.sh install "$2" > /dev/null && ./svc.sh start > /dev/null' "$dir" "$RUNNER_USER"
    ok "servicio activo (arranca con WSL)"
  fi
  gh variable set RUNNER -R "$repo" -b self-hosted > /dev/null
  ok "RUNNER=self-hosted: sus workflows corren aquí"
}

remove() {
  local repo=$1 dir token
  dir=$(repo_dir "$repo")
  echo "==> $repo"
  gh variable delete RUNNER -R "$repo" > /dev/null 2>&1 || true
  ok "sin RUNNER: sus workflows vuelven a los runners de GitHub"
  sudo test -d "$dir" || return 0
  as_root 'cd "$1" && ./svc.sh stop > /dev/null 2>&1; ./svc.sh uninstall > /dev/null 2>&1' "$dir" || true
  token=$(gh api -X POST "repos/$repo/actions/runners/remove-token" -q .token)
  sudo -u "$RUNNER_USER" bash -c 'cd "$1" && ./config.sh remove --token "$2" > /dev/null' _ "$dir" "$token" || true
  sudo rm -rf "$dir"
  ok "runner quitado"
}

status() {
  local d repo
  for d in $(sudo find "$BASE" -mindepth 2 -maxdepth 2 -name .runner); do
    repo=$(sudo jq -r .gitHubUrl "$d" | sed 's#https://github.com/##')
    gh api "repos/$repo/actions/runners" --jq '.runners[] | "  \(.name)  \(.status)  \(if .busy then "trabajando" else "libre" end)"'
    printf '  RUNNER=%s\n' "$(gh variable get RUNNER -R "$repo" 2> /dev/null || echo '(sin: usa GitHub)')"
  done
}

case "${1:-}" in
  add) shift; [ $# -gt 0 ] || die "Uso: tools/runner.sh add <dueño/repo>..."; for r in "$@"; do add "$r"; done ;;
  remove) shift; [ $# -gt 0 ] || die "Uso: tools/runner.sh remove <dueño/repo>..."; for r in "$@"; do remove "$r"; done ;;
  status) status ;;
  *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
