"""El Dockerfile que andamio propone cuando el repo de una app no trae uno.

Aquí se revisa el texto generado; tests/build-fixtures.sh (en CI) los construye y arranca de verdad.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import ROOT, write_files


def render(andamio, kind: str, d: Path, port: str) -> str:
    values = {"PORT": port}
    if kind in ("node", "python"):
        extra, start = andamio.node_values(d) if kind == "node" else andamio.python_values(d)
        values.update(extra, START=start)
    elif kind == "go":
        values.update(andamio.go_values(d))
    return andamio.render_dockerfile(kind, values)


def final_stage(text: str) -> str:
    return text.rsplit("\nFROM ", 1)[-1]


@pytest.mark.parametrize("files, kind", [
    ({"package.json": "{}"}, "node"),
    ({"requirements.txt": "flask"}, "python"),
    ({"pyproject.toml": "[project]\nname='x'"}, "python"),
    ({"go.mod": "module x\n\ngo 1.23\n"}, "go"),
    ({"index.html": "<h1>hola</h1>"}, "static"),
    ({"README.md": "nada"}, None),
    ({"package.json": "{}", "requirements.txt": ""}, "node"),   # Node manda (frontend con scripts de Python)
])
def test_detect_kind(andamio, tmp_path, files, kind):
    write_files(tmp_path, files)
    assert andamio.detect_kind(tmp_path) == kind


@pytest.mark.parametrize("kind, files, port", [
    ("node", {"package.json": json.dumps({"scripts": {"start": "node server.js"}})}, "3000"),
    ("python", {"requirements.txt": "fastapi\nuvicorn\n", "main.py": ""}, "8000"),
    ("go", {"go.mod": "module x\n\ngo 1.23\n", "main.go": ""}, "8080"),
    ("static", {"index.html": ""}, "8080"),
])
def test_every_dockerfile_is_safe_and_complete(andamio, tmp_path, kind, files, port):
    write_files(tmp_path, files)
    text = render(andamio, kind, tmp_path, port)
    assert "{{" not in text, "quedó un valor de la plantilla sin reemplazar"
    final = final_stage(text)
    # Corre sin root: un USER que no sea root, o la imagen distroless :nonroot.
    users = re.findall(r"(?m)^USER (\S+)", final)
    assert (users and users[-1] not in ("root", "0")) or ":nonroot" in final.splitlines()[0]
    assert f"EXPOSE {port}" in final
    # Solo comentarios en el idioma elegido (#es:/#en: no quedan en el archivo).
    assert not re.search(r"(?m)^#(es|en): ", text)


def test_node_package_managers(andamio, tmp_path):
    pkg = {"scripts": {"build": "tsc", "test": "vitest run", "start": "node dist/index.js"},
           "packageManager": "pnpm@9.12.0"}
    write_files(tmp_path, {"package.json": json.dumps(pkg), "pnpm-lock.yaml": ""})
    values, start = andamio.node_values(tmp_path)
    assert values["PM"] == "pnpm" and "pnpm@9" in values["PM_SETUP"]
    assert values["INSTALL"] == "pnpm install --frozen-lockfile"
    assert values["BUILD"] == "RUN pnpm run build"
    assert "pnpm run test" in values["TEST"]
    assert start == "node dist/index.js"

    (tmp_path / "pnpm-lock.yaml").unlink()
    write_files(tmp_path, {"package-lock.json": "{}"})
    values, _ = andamio.node_values(tmp_path)
    assert values["INSTALL"] == "npm ci"


def test_node_without_start_or_tests(andamio, tmp_path):
    write_files(tmp_path, {"package.json": json.dumps(
        {"main": "app.js", "scripts": {"test": 'echo "Error: no test specified" && exit 1'}})})
    values, start = andamio.node_values(tmp_path)
    assert start == "node app.js"
    assert values["TEST"] == "", "el test de relleno de npm init no cuenta como tests"
    assert values["BUILD"] == ""


def test_next_starts_with_next(andamio, tmp_path):
    write_files(tmp_path, {"package.json": json.dumps({"dependencies": {"next": "15"}, "scripts": {"build": "next build"}})})
    _, start = andamio.node_values(tmp_path)
    assert start == "next start"


@pytest.mark.parametrize("files, start", [
    ({"requirements.txt": "fastapi\nuvicorn", "main.py": ""}, "uvicorn main:app --host 0.0.0.0 --port $PORT"),
    ({"requirements.txt": "flask\ngunicorn", "app.py": ""}, "gunicorn app:app --bind 0.0.0.0:$PORT"),
    ({"requirements.txt": "django\ngunicorn", "manage.py": "", "sitio/wsgi.py": ""},
     "gunicorn sitio.wsgi --bind 0.0.0.0:$PORT"),
    ({"requirements.txt": "requests", "main.py": ""}, "python main.py"),
])
def test_python_start_command(andamio, tmp_path, files, start):
    write_files(tmp_path, files)
    _, got = andamio.python_values(tmp_path)
    assert got == start
    # Siempre escucha en todas las interfaces y en $PORT (o lo decide la app, con python main.py).
    assert "127.0.0.1" not in got and "localhost" not in got


def test_python_tests_and_pyproject(andamio, tmp_path):
    write_files(tmp_path, {"pyproject.toml": "[project]\ndependencies=['fastapi','uvicorn']", "main.py": "",
                           "tests/test_x.py": ""})
    values, _ = andamio.python_values(tmp_path)
    assert "pip install ." in values["INSTALL"]
    assert "pytest" in values["TEST"]


def test_go_version_and_package(andamio, tmp_path):
    write_files(tmp_path, {"go.mod": "module x\n\ngo 1.24\n", "go.sum": "", "cmd/api/main.go": ""})
    values = andamio.go_values(tmp_path)
    assert values == {"GO": "1.24", "GOSUM": "go.sum ", "PKG": "./cmd/api"}


def test_start_command_is_escaped(andamio, tmp_path):
    """Un comando con comillas no rompe el CMD ["sh", "-c", "..."] de la imagen."""
    write_files(tmp_path, {"package.json": "{}"})
    values, _ = andamio.node_values(tmp_path)
    start = 'node -e "require(\'./s\')"'
    values.update(PORT="3000", START=start.replace("\\", "\\\\").replace('"', '\\"'))
    cmd = re.search(r"(?m)^CMD (.+)$", andamio.render_dockerfile("node", values)).group(1)
    assert json.loads(cmd) == ["sh", "-c", f"exec {start}"]


def test_scaffold_command(andamio, tmp_path, env):
    """_scaffold (lo que llama app create): escribe Dockerfile y .dockerignore, y el puerto."""
    import subprocess
    app = tmp_path / "app"
    write_files(app, {"package.json": json.dumps({"scripts": {"start": "node server.js"}})})
    out = tmp_path / "out"
    r = subprocess.run([str(ROOT / "bin" / "andamio"), "_scaffold", str(app), "", str(out)],
                       input="s\ns\n", text=True, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    assert out.read_text() == "status=generated\nport=3000\n"
    assert (app / "Dockerfile").exists() and "node_modules" in (app / ".dockerignore").read_text()

    # Con Dockerfile propio: no lo toca.
    (app / "Dockerfile").write_text("FROM scratch\n")
    r = subprocess.run([str(ROOT / "bin" / "andamio"), "_scaffold", str(app), "4000", str(out)],
                       text=True, capture_output=True, env=env)
    assert out.read_text() == "status=existing\nport=4000\n"
    assert (app / "Dockerfile").read_text() == "FROM scratch\n"
