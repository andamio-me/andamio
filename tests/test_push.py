"""Subir la copia cuando GitHub tiene commits que ella no (un PR mergeado allá, Dependabot): andamio
los trae, pone los suyos encima y sube. Si chocan, no adivina: deshace el intento y lo dice."""
from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import ROOT

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin"}


def git(d: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(d), *args], check=True, capture_output=True, text=True, env=GIT_ENV).stdout.strip()


def setup(tmp_path: Path) -> tuple[Path, Path]:
    """Un "GitHub" (repo bare), tu copia y otra copia (la web de GitHub, Dependabot) con un commit nuevo."""
    origin, mine, other = tmp_path / "origin.git", tmp_path / "mine", tmp_path / "other"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=GIT_ENV)
    subprocess.run(["git", "clone", "-q", str(origin), str(mine)], check=True, env=GIT_ENV, capture_output=True)
    (mine / "app.yml").write_text("mem: 512m\n")
    (mine / "ci.yml").write_text("checkout@v4\n")
    git(mine, "add", "-A"); git(mine, "commit", "-qm", "inicio"); git(mine, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", str(origin), str(other)], check=True, env=GIT_ENV, capture_output=True)
    return mine, other


def push_infra(copy: Path) -> subprocess.CompletedProcess:
    """La función push_infra de bin/andamio-app, sola."""
    script = (ROOT / "bin/andamio-app").read_text()
    fn = script[script.index("push_infra() {"):script.index("\n}\n", script.index("push_infra() {")) + 3]
    prelude = 'L() { printf "%s" "$1"; }\ndie() { echo "$*" >&2; exit 1; }\n'
    return subprocess.run(["bash", "-c", prelude + fn + f'INFRA="{copy}"\npush_infra'], capture_output=True, text=True,
                          env=GIT_ENV)


def test_brings_github_changes_and_pushes_on_top(tmp_path):
    mine, other = setup(tmp_path)
    (other / "ci.yml").write_text("checkout@v5\n"); git(other, "commit", "-qam", "dependabot"); git(other, "push", "-q")
    (mine / "app.yml").write_text("mem: 640m\n"); git(mine, "commit", "-qam", "mem=640m")
    r = push_infra(mine)
    assert r.returncode == 0, r.stderr
    assert "GitHub tiene cambios" in r.stdout
    log = git(mine, "log", "--format=%s", "origin/main")
    assert log.splitlines() == ["mem=640m", "dependabot", "inicio"], "el tuyo encima, sin merge"


def test_conflict_is_undone_and_explained(tmp_path):
    mine, other = setup(tmp_path)
    (other / "app.yml").write_text("mem: 1g\n"); git(other, "commit", "-qam", "otro cambio"); git(other, "push", "-q")
    (mine / "app.yml").write_text("mem: 640m\n"); git(mine, "commit", "-qam", "mem=640m")
    r = push_infra(mine)
    assert r.returncode != 0 and "cambiaron lo mismo" in r.stderr
    assert git(mine, "status", "--porcelain") == "", "sin rebase a medias"
    assert git(mine, "log", "-1", "--format=%s") == "mem=640m", "tu commit sigue ahí"


def test_nothing_new_on_github_just_pushes(tmp_path):
    mine, _ = setup(tmp_path)
    (mine / "app.yml").write_text("mem: 640m\n"); git(mine, "commit", "-qam", "mem=640m")
    r = push_infra(mine)
    assert r.returncode == 0 and "GitHub tiene cambios" not in r.stdout
