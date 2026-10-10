"""Ayudas compartidas por los tests de andamio.

- `andamio`: bin/andamio cargado como módulo, para probar sus funciones directo.
- `make_repo`: un repo git temporal con los archivos que le pases.
- `env`: entorno aislado (HOME, caché y configuración en carpetas temporales) para correr
  bin/andamio y bin/andamio-app como procesos sin tocar tu máquina.
- `fake_copy`: una copia de andamio de mentira (config, inventario, una app), sin servidor.

Correr: tools/tests.sh (o pytest tests/ con pytest instalado).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.environ["ANDAMIO_LANG"] = "es"   # los mensajes que se revisan, en español


def load_andamio():
    loader = importlib.machinery.SourceFileLoader("andamio_cli", str(ROOT / "bin" / "andamio"))
    spec = importlib.util.spec_from_loader("andamio_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def andamio():
    return load_andamio()


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


def write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Entorno para los procesos: nada de tu HOME (ni lanzador global, ni caché, ni llaves)."""
    home = tmp_path / "home"
    home.mkdir()
    e = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "SOPS_", "ANDAMIO_"))}
    e.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_CACHE_HOME=str(home / ".cache"),
             ANDAMIO_LANG="es", GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
             GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com", GIT_CONFIG_NOSYSTEM="1")
    return e


@pytest.fixture
def make_repo(tmp_path: Path, env: dict[str, str]):
    """make_repo("nombre", {"ruta": "contenido"}) → carpeta con un repo git y un commit."""
    def make(name: str, files: dict[str, str]) -> Path:
        d = tmp_path / name
        d.mkdir(parents=True)
        write_files(d, files)
        subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True, env=env)
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(d), "commit", "-qm", "inicio"], check=True, env=env)
        return d
    return make


APP_YML = """\
# Cómo corre web en la plataforma.
name: web
host: web                  # web.<DOMAIN>
port: 3000
access: vpn                # vpn | public
networks: []
migrate: false
db: false
redis: false
worker:
  command: node worker.js
  mem: 192m
resources:
  mem: 256m
  cpus: 0.5
  pids: 200
"""


@pytest.fixture
def fake_copy(make_repo, env):
    """Una copia de andamio sin servidor: bin/ real, configuración y una app `web` inventadas."""
    files = {
        "ansible/group_vars/all.yml": (
            "andamio_domain: ejemplo.com\nandamio_github_owner: tu-usuario\n"
            "andamio_repo: git@github.com:tu-usuario/tu-andamio.git\nandamio_server_ip: 203.0.113.10\n"),
        "ansible/inventory.yml": "all:\n  children:\n    servers:\n      hosts:\n        mi-vps:\n",
        "apps/web/app.yml": APP_YML,
        "apps/web/secrets.sops.env": "# relleno: los tests no descifran nada\n",
    }
    files[".gitignore"] = (ROOT / ".gitignore").read_text()
    d = make_repo("copia", files)
    (d / "bin").mkdir()
    for name in ("andamio", "andamio-app", "forge"):
        shutil.copy2(ROOT / "bin" / name, d / "bin" / name)
    shutil.copytree(ROOT / "templates", d / "templates")
    shutil.copytree(ROOT / "ansible" / "filter_plugins", d / "ansible" / "filter_plugins",
                    ignore=shutil.ignore_patterns("__pycache__"))
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "bin"], check=True, env=env)
    return d
