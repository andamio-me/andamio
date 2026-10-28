"""`andamio app` en una copia sin servidor: lo que se rechaza antes de tocar nada, y `app set`.

Los comandos corren sin terminal (como en CI): cada pregunta se responde "no", así que nada
llega a GitHub ni al servidor.
"""
from __future__ import annotations

import subprocess

import pytest
import yaml

from conftest import APP_YML, git


def app(copy, env, *args: str) -> subprocess.CompletedProcess:
    # start_new_session: sin terminal de control, como en CI (las preguntas no pueden esperar a nadie).
    return subprocess.run([str(copy / "bin" / "andamio-app"), "app", *args], cwd=copy, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, start_new_session=True,
                          timeout=60)


@pytest.mark.parametrize("args, error", [
    (["create", "A"], "Nombre inválido"),
    (["create", "x" * 31], "Nombre inválido"),
    (["create", "nueva", "--mem", "12x"], "Memoria inválida"),
    (["create", "nueva", "--port", "1"], "Puerto inválido"),
    (["create", "nueva", "--host", "Mal_Host"], "Host inválido"),
    (["create", "nueva", "--health", "sin-barra"], "Ruta de salud inválida"),
    (["create", "nueva", "--repo", "sin-dueño"], "Repo inválido"),
    (["create", "nueva", "--domain", "no es dominio"], "Dominio inválido"),
    (["create", "nueva", "--domain", "ejemplo.com"], "usa --host @"),
    (["create", "nueva", "--domain", "api.ejemplo.com"], "usa --host api"),
    (["create", "nueva", "--cors", "*"], "orígenes exactos"),
    (["create", "nueva", "--cors", "https://x.com/ruta"], "Origen inválido"),
    (["create", "nueva", "--volume", "/etc"], "carpeta del sistema"),
    (["create", "nueva", "--volume", "datos"], "Carpeta inválida"),
    (["create", "nueva", "--volume", "/a/../etc"], "Carpeta inválida"),
    (["create", "nueva", "--inventada"], "Opción desconocida"),
    (["create", "web"], "Ya existe"),
    (["create", "nueva", "--host", "web"], "ya lo usa otra app"),
    (["volume", "add", "web", "/proc"], "carpeta del sistema"),
    (["domain", "add", "web", "no_valido"], "Dominio inválido"),
    (["cors", "add", "web", "*"], "orígenes exactos"),
    (["secret", "set", "web", "minusculas"], "Nombre inválido"),
    (["secret", "set", "web", "DATABASE_URL"], "lo pone andamio"),
    (["secret", "set", "web", "MYSQL_URL"], "lo pone andamio"),
    (["secret", "import", "web", "/no/existe.env"], "No puedo leer"),
    (["logs", "noexiste"], "No existe la app noexiste"),
    (["set", "web", "--mem", "12x"], "Memoria inválida"),
    (["set", "web", "--cpus", "0"], "CPU inválida"),
    (["set", "web", "--port", "70000"], "Puerto inválido"),
    (["set", "web", "--health", "x"], "Ruta de salud inválida"),
    (["set", "web"], "Nada que cambiar"),
    (["set", "web", "--inventada"], "Opción desconocida"),
    (["set", "web", "--db-connections", "20"], "no tiene base"),
    (["set", "web", "--db-connections", "999"], "Conexiones inválidas"),
    (["set", "web", "--db-timeout", "30 s"], "Tiempo inválido"),
    (["rollback", "web", "no-es-commit"], "Commit inválido"),
    (["restore", "web", "x;y"], "Respaldo inválido"),
    (["restore", "noexiste", "latest"], "No existe la app noexiste"),
    (["restore", "web", "latest"], "Cancelado"),
    (["revert", "web", "zz"], "Commit inválido"),
    (["revert", "web", "abcdef1"], "No existe el commit"),
    (["sql", "web", "select 1"], "no tiene base"),
    (["logs", "web", "--otro"], "Opción desconocida"),
    (["cron", "edit", "web", "nada", "--schedule", "@daily"], "No hay una tarea nada"),
    (["cron", "edit", "web", "nada"], "Nada que cambiar"),
    (["sql", "noexiste"], "No existe esa app"),
    # Varias apps en un repo
    (["create", "nueva", "--dir", "../fuera"], "Carpeta inválida"),
    (["create", "nueva", "--dir", "/backend"], "Carpeta inválida"),
    (["create", "nueva", "--dir", "backend"], "--dir va con --repo"),
    (["create", "nueva", "--context", "."], "van con --dir"),
    (["create", "nueva", "--path", "api"], "Ruta inválida"),
    (["create", "nueva", "--path", "/API/"], "Ruta inválida"),
    (["create", "nueva", "--repo", "yo/x", "--dir", "b", "--watch", "a b"], "Ruta inválida"),
    (["source", "web", "--dir", "backend"], "es la única app de su repo"),
    (["source", "noexiste"], "No existe la app noexiste"),
])
def test_rejected_before_touching_anything(fake_copy, env, args, error):
    r = app(fake_copy, env, *args)
    assert r.returncode != 0
    assert error in r.stderr, r.stderr
    assert git(fake_copy, "status", "--porcelain") == "", "un rechazo no deja cambios"


def test_unknown_app_lists_the_real_ones(fake_copy, env):
    r = app(fake_copy, env, "set", "otra", "--mem", "1g")
    assert "No existe la app otra" in r.stderr and "Sus apps: web" in r.stderr


def test_set_with_the_same_values_does_nothing(fake_copy, env):
    r = app(fake_copy, env, "set", "web", "--mem", "256m", "--vpn")
    assert r.returncode == 0, r.stderr
    assert "nada que cambiar" in r.stdout
    assert git(fake_copy, "status", "--porcelain") == ""


def test_set_cancelled_leaves_app_yml_as_it_was(fake_copy, env):
    r = app(fake_copy, env, "set", "web", "--mem", "512m", "--public")
    assert r.returncode != 0 and "Cancelado" in r.stderr
    assert "resources.mem: 256m → 512m" in r.stdout and "access: vpn → public" in r.stdout
    assert "cualquiera en internet" in r.stdout, "pasar a pública avisa"
    assert (fake_copy / "apps/web/app.yml").read_text() == APP_YML
    assert git(fake_copy, "status", "--porcelain") == ""


# ---- yaml_set: la edición de app.yml que hace `app set` ----

def test_yaml_set_keeps_comments_and_order(andamio):
    text, changed = andamio.yaml_set(APP_YML, ["resources.mem=512m", "access=public", "port=8080"])
    assert changed == ["resources.mem: 256m → 512m", "access: vpn → public", "port: 3000 → 8080"]
    assert "access: public                # vpn | public" in text
    assert "host: web                  # web.<DOMAIN>" in text
    # Solo esas líneas cambian.
    diff = [(a, b) for a, b in zip(APP_YML.splitlines(), text.splitlines()) if a != b]
    assert len(diff) == 3 and len(text.splitlines()) == len(APP_YML.splitlines())


def test_yaml_set_changes_resources_not_the_worker(andamio):
    text, _ = andamio.yaml_set(APP_YML, ["resources.mem=1g"])
    assert "  mem: 192m" in text, "el mem del worker no se toca"
    assert "  mem: 1g" in text


def test_yaml_set_adds_a_missing_key_after_port(andamio):
    text, changed = andamio.yaml_set(APP_YML, ["health=/healthz"])
    lines = text.splitlines()
    assert lines[lines.index("port: 3000") + 1] == "health: /healthz"
    assert changed == ["health: (ninguna) → /healthz"]


def test_yaml_set_quoted_and_unchanged_values(andamio):
    text, changed = andamio.yaml_set('host: "@"\nport: 80\n', ["host=@", "port=80"])
    assert changed == [] and text == 'host: "@"\nport: 80\n'


def test_yaml_set_unknown_nested_key_fails(andamio):
    with pytest.raises(SystemExit):
        andamio.yaml_set(APP_YML, ["resources.gpu=1"])


def revert_env(env, tmp_path):
    """Un ansible-playbook de mentira (regenerar el compose no hace falta aquí)."""
    fake = tmp_path / "fakebin"
    fake.mkdir(exist_ok=True)
    (fake / "ansible-playbook").write_text("#!/bin/sh\necho ok=1\n")
    (fake / "ansible-playbook").chmod(0o755)
    return {**env, "PATH": f"{fake}:" + env["PATH"], "ANDAMIO_REVERT_OK": "1"}


def test_revert_undoes_a_config_change_with_a_new_commit(fake_copy, env, tmp_path):
    yml = fake_copy / "apps/web/app.yml"
    before = yml.read_text()
    yml.write_text(before.replace("mem: 256m", "mem: 512m"))
    git(fake_copy, "commit", "-qam", "feat(apps): web: resources.mem=512m")
    sha = git(fake_copy, "rev-parse", "HEAD").strip()
    app(fake_copy, revert_env(env, tmp_path), "revert", "web", sha)   # luego falla al subir: la copia no tiene remoto
    assert yml.read_text() == before
    assert git(fake_copy, "log", "-1", "--format=%s").startswith(f"revert(apps): web: deshacer {sha[:7]}")
    assert git(fake_copy, "rev-list", "--count", "HEAD").strip() != "0" and sha in git(fake_copy, "log", "--format=%H"), "el historial no se borra"


def test_revert_refuses_when_a_later_change_touched_the_same_lines(fake_copy, env, tmp_path):
    yml = fake_copy / "apps/web/app.yml"
    yml.write_text(yml.read_text().replace("mem: 256m", "mem: 512m"))
    git(fake_copy, "commit", "-qam", "mem 512m")
    first = git(fake_copy, "rev-parse", "HEAD").strip()
    yml.write_text(yml.read_text().replace("mem: 512m", "mem: 1g"))
    git(fake_copy, "commit", "-qam", "mem 1g")
    r = app(fake_copy, revert_env(env, tmp_path), "revert", "web", first)
    assert r.returncode != 0 and "Un cambio posterior" in r.stderr
    assert "mem: 1g" in yml.read_text() and git(fake_copy, "status", "--porcelain") == ""


def test_revert_only_config_changes(fake_copy, env, tmp_path):
    (fake_copy / "apps/web/secrets.sops.env").write_text("X=1\n")
    git(fake_copy, "add", "-A")
    git(fake_copy, "commit", "-qm", "secreto")
    r = app(fake_copy, revert_env(env, tmp_path), "revert", "web", git(fake_copy, "rev-parse", "HEAD").strip())
    assert r.returncode != 0 and "no es un cambio de configuración" in r.stderr


def test_ci_snippet_for_one_of_several_apps(fake_copy, env):
    """Una de varias apps del repo: su archivo, su carpeta, su llave, y solo corre si cambió lo suyo."""
    r = subprocess.run([str(fake_copy / "bin" / "forge"), "ci-snippet", "yo/infra", "a" * 40, "--app", "web-api",
                        "--dir", "backend", "--watch", "packages/"], cwd=fake_copy, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert out.startswith("# .github/workflows/andamio-web-api.yml")
    assert "image: web-api" in out and "dir: backend" in out and "deploy_key: DEPLOY_SSH_KEY_WEB_API" in out
    assert 'paths: ["backend/**", "packages/**", ".github/workflows/andamio-web-api.yml"]' in out
    plain = subprocess.run([str(fake_copy / "bin" / "forge"), "ci-snippet", "yo/infra", "a" * 40], cwd=fake_copy, env=env,
                           capture_output=True, text=True).stdout
    assert "andamio.yml" in plain and "paths:" not in plain and "deploy_key" not in plain


def test_ci_snippet_passes_secrets_across_owners(fake_copy, env):
    """inherit no cruza de dueño: los secretos van explícitos; --inherit, para versiones viejas del pipeline."""
    forge = str(fake_copy / "bin" / "forge")
    out = subprocess.run([forge, "ci-snippet", "andamio-me/andamio", "a" * 40], cwd=fake_copy, env=env,
                         capture_output=True, text=True).stdout
    assert "uses: andamio-me/andamio/.github/workflows/app-build.yml@" + "a" * 40 in out
    assert "ANDAMIO_SECRETS: ${{ toJSON(secrets) }}" in out and "secrets: inherit" not in out
    yaml.safe_load(out)
    old = subprocess.run([forge, "ci-snippet", "yo/infra", "a" * 40, "--inherit"], cwd=fake_copy, env=env,
                         capture_output=True, text=True).stdout
    assert "secrets: inherit" in old and "ANDAMIO_SECRETS" not in old


def test_ci_repin_moves_to_the_public_pipeline(fake_copy, env, tmp_path):
    """Un pipeline viejo (de tu copia, con inherit) pasa al público, con los secretos explícitos."""
    wf = tmp_path / ".github" / "workflows" / "andamio.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text(f"jobs:\n  build:\n    uses: yo/infra/.github/workflows/app-build.yml@{'a' * 40}\n"
                  "    with:\n      image: web\n    secrets: inherit   # la llave de deploy\n")
    forge = str(fake_copy / "bin" / "forge")
    r = subprocess.run([forge, "ci-repin", str(tmp_path), "andamio-me/andamio", "b" * 40], cwd=fake_copy, env=env,
                       capture_output=True, text=True)
    assert r.stdout.strip() == f"{'a' * 40} {'b' * 40}", r.stderr
    job = yaml.safe_load(wf.read_text())["jobs"]["build"]
    assert job["uses"] == f"andamio-me/andamio/.github/workflows/app-build.yml@{'b' * 40}"
    assert job["secrets"] == {"ANDAMIO_SECRETS": "${{ toJSON(secrets) }}"}
    again = subprocess.run([forge, "ci-repin", str(tmp_path), "andamio-me/andamio", "b" * 40], cwd=fake_copy, env=env,
                           capture_output=True, text=True)
    assert again.stdout.strip() == ""


def test_ci_runs_rejects_a_bad_workflow_name(fake_copy, env):
    r = subprocess.run([str(fake_copy / "bin" / "forge"), "ci-runs", "yo/app", "--workflow", "../x"], cwd=fake_copy,
                       env=env, capture_output=True, text=True)
    assert r.returncode == 2 and "workflow" in r.stderr


def test_source_shows_where_an_app_comes_from(fake_copy, env):
    r = app(fake_copy, env, "source", "web")
    assert r.returncode == 0 and "la raíz" in r.stdout


def test_watch_paths_become_patterns(fake_copy, env):
    """Una carpeta cubre lo de adentro, un archivo queda tal cual; construir desde la raíz suma sus manifiestos."""
    r = subprocess.run([str(fake_copy / "bin" / "forge"), "ci-snippet", "yo/infra", "a" * 40, "--app", "api", "--dir", "backend",
                        "--context", ".", "--watch", "packages", "--watch", "config/*.yml", "--watch", "tsconfig.base.json"],
                       cwd=fake_copy, env=env, capture_output=True, text=True)
    line = next(l for l in r.stdout.splitlines() if "push:" in l)
    for want in ('"backend/**"', '"packages/**"', '"config/*.yml"', '"tsconfig.base.json"', '"pnpm-lock.yaml"', '"package.json"'):
        assert want in line, want
    assert "context: ." in r.stdout


def test_ci_snippet_deploys_from_the_repo_branch(fake_copy, env):
    """Un repo cuya rama principal no es main (production): el pipeline escucha esa rama."""
    forge = str(fake_copy / "bin" / "forge")
    out = subprocess.run([forge, "ci-snippet", "yo/infra", "a" * 40, "--branch", "production"], cwd=fake_copy, env=env,
                         capture_output=True, text=True).stdout
    assert "push: { branches: [production] }" in out
    bad = subprocess.run([forge, "ci-runs", "yo/app", "--branch", "a..b"], cwd=fake_copy, env=env, capture_output=True, text=True)
    assert bad.returncode == 2 and "branch" in bad.stderr
