"""`andamio app` en una copia sin servidor: lo que se rechaza antes de tocar nada, y `app set`.

Los comandos corren sin terminal (como en CI): cada pregunta se responde "no", así que nada
llega a GitHub ni al servidor.
"""
from __future__ import annotations

import subprocess

import pytest

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
    (["logs", "noexiste"], "No existe la app noexiste"),
    (["set", "web", "--mem", "12x"], "Memoria inválida"),
    (["set", "web", "--cpus", "0"], "CPU inválida"),
    (["set", "web", "--port", "70000"], "Puerto inválido"),
    (["set", "web", "--health", "x"], "Ruta de salud inválida"),
    (["set", "web"], "Nada que cambiar"),
    (["set", "web", "--inventada"], "Opción desconocida"),
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
