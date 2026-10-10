"""`andamio update`: trae lo nuevo de andamio sin pisar lo tuyo.

Un "andamio oficial" falso (repo git con una v1 y una v2) y una copia que viene de la v1, con
cambios propios. La copia nunca comparte historial con el oficial, como una creada desde el
template: la versión de la que viene se deduce de sus archivos.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import ROOT, git, write_files

DOC_V1 = "".join(f"línea {i}\n" for i in range(1, 11))

V1 = {
    "scripts/solo-andamio.sh": "echo v1\n",
    "docs/ambos.md": DOC_V1,
    "scripts/choque.sh": "valor=1\n",
    "scripts/viejo.sh": "echo viejo\n",
    "ansible/group_vars/all.yml": "andamio_domain: oficial.example\n",
    "apps/demo/app.yml": "name: demo\n",
}
V2 = {
    "scripts/solo-andamio.sh": "echo v2\n",
    "docs/ambos.md": DOC_V1.replace("línea 10\n", "línea 10 (andamio)\n"),
    "scripts/choque.sh": "valor=2\n",
    "scripts/nuevo.sh": "echo nuevo\n",
    "ansible/group_vars/all.yml": "andamio_domain: otro.example\n",
    "apps/demo/app.yml": "name: demo\nport: 9999\n",
    "apps/otra/app.yml": "name: otra\n",
}


def commit_all(d: Path, env, msg: str) -> str:
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", msg], check=True, env=env)
    return git(d, "rev-parse", "HEAD").strip()


@pytest.fixture
def setup(make_repo, env, tmp_path):
    """Devuelve (oficial, copia, sha_v1, sha_v2, crear_copia). crear_copia(conflicto=bool)."""
    official = make_repo("oficial", V1)
    v1 = git(official, "rev-parse", "HEAD").strip()
    (official / "scripts" / "viejo.sh").unlink()
    write_files(official, V2)
    v2 = commit_all(official, env, "v2: mejoras")

    def make_copy(conflict: bool = True) -> Path:
        files = {k: v for k, v in V1.items() if not k.startswith("apps/")}
        files["docs/ambos.md"] = DOC_V1.replace("línea 1\n", "línea 1 (mía)\n")
        if conflict:
            files["scripts/choque.sh"] = "valor=mio\n"
        files["ansible/group_vars/all.yml"] = f"andamio_domain: ejemplo.com\nandamio_upstream: file://{official}\n"
        copy = make_repo("copia", files)
        (copy / "bin").mkdir()
        shutil.copy2(ROOT / "bin" / "andamio", copy / "bin" / "andamio")
        commit_all(copy, env, "bin")
        return copy
    return official, v1, v2, make_copy


def update(copy: Path, env, *args: str, answers: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([str(copy / "bin" / "andamio"), "update", *args], cwd=copy, env=env,
                          input=answers, text=True, capture_output=True)


def test_check_changes_nothing_and_infers_the_base(setup, env):
    _, v1, _, make_copy = setup
    copy = make_copy()
    r = update(copy, env, "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"{v1[:8]} (deducida" in r.stdout
    assert "No cambié nada" in r.stdout
    assert git(copy, "status", "--porcelain") == ""


def test_update_merges_and_never_touches_yours(setup, env):
    _, _, v2, make_copy = setup
    copy = make_copy(conflict=True)
    own_config = (copy / "ansible/group_vars/all.yml").read_text()
    r = update(copy, env, answers="s\n")   # ¿Aplicar? sí (con conflicto no pregunta si subirlo)
    assert r.returncode == 0, r.stdout + r.stderr

    read = lambda p: (copy / p).read_text()
    assert read("scripts/solo-andamio.sh") == "echo v2\n", "lo que no tocaste se actualiza"
    doc = read("docs/ambos.md")
    assert "línea 1 (mía)" in doc and "línea 10 (andamio)" in doc and "<<<<<<<" not in doc, \
        "cambios de los dos en partes distintas: se combinan"
    clash = read("scripts/choque.sh")
    assert "<<<<<<<" in clash and "valor=mio" in clash and "valor=2" in clash, \
        "si chocan, quedan los dos con marcas, nada se pierde"
    assert "Con conflicto" in r.stdout and "<<<<<<<" in r.stdout
    assert not (copy / "scripts/viejo.sh").exists(), "lo que andamio quitó (y no tocaste) se quita"
    assert read("scripts/nuevo.sh") == "echo nuevo\n"
    # Lo tuyo: configuración y apps, nunca.
    assert read("ansible/group_vars/all.yml") == own_config
    assert not (copy / "apps").exists()
    assert read(".andamio/upstream").splitlines()[1] == f"commit {v2}"


def test_second_update_is_up_to_date(setup, env):
    _, _, _, make_copy = setup
    copy = make_copy(conflict=False)
    assert update(copy, env, answers="s\nno\n").returncode == 0
    commit_all(copy, env, "andamio: actualización")
    r = update(copy, env, "--check")
    assert "Ya estás al día" in r.stdout


def test_commit_and_push(setup, env, tmp_path):
    """Sin conflictos, "si" deja un commit con el mensaje de siempre y lo sube."""
    _, _, v2, make_copy = setup
    copy = make_copy(conflict=False)
    remote = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(copy, "remote", "add", "origin", str(remote))
    git(copy, "push", "-q", "-u", "origin", "main")
    r = update(copy, env, answers="s\nsi\n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(copy, "status", "--porcelain") == ""
    assert git(remote, "log", "-1", "--format=%s", "main").strip() == f"andamio: actualización a {v2[:8]}"
    assert "andamio servidor" in r.stdout, "cambió scripts/: avisa que hay que aplicarlo en el servidor"


def test_refuses_with_uncommitted_changes(setup, env):
    _, _, _, make_copy = setup
    copy = make_copy()
    (copy / "scripts/solo-andamio.sh").write_text("echo a medias\n")
    r = update(copy, env, "--check")
    assert r.returncode == 1 and "sin commit" in r.stderr
