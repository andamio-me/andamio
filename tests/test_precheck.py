"""La revisión previa de `app create`: lo que haría fallar el primer deploy o perder datos."""
from __future__ import annotations

import itertools
import subprocess

import pytest

from conftest import ROOT

_n = itertools.count()


def findings(andamio, make_repo, files, port="3000", volume=False):
    repo = make_repo(f"app{next(_n)}", files)
    return andamio.precheck_findings(repo, port, volume)


def has(found, word: str, serious: bool | None = None) -> bool:
    return any(word in msg and (serious is None or s == serious) for s, msg in found)


CLEAN_NODE = """\
const http = require("http");
const port = process.env.PORT || 3000;
http.createServer((req, res) => res.end("ok")).listen(port, "0.0.0.0");
"""


def test_clean_app_has_no_findings(andamio, make_repo):
    assert findings(andamio, make_repo, {"server.js": CLEAN_NODE, "package.json": "{}"}) == []


@pytest.mark.parametrize("code", [
    'app.listen(3000, "localhost")',
    'uvicorn.run(app, host="127.0.0.1")',
    "app.run()",
    'http.ListenAndServe("localhost:8080", nil)',
])
def test_localhost_is_serious(andamio, make_repo, code):
    ext = ".go" if "ListenAndServe" in code else ".js" if "listen(" in code else ".py"
    found = findings(andamio, make_repo, {f"server{ext}": code + "\n"})
    assert has(found, "localhost", serious=True)


def test_fixed_port_other_than_the_app_port(andamio, make_repo):
    found = findings(andamio, make_repo, {"server.js": "app.listen(5000)\n"}, port="3000")
    assert has(found, "5000", serious=False)
    # El mismo puerto que usará andamio: nada que decir.
    assert findings(andamio, make_repo, {"server.js": "app.listen(5000)\n"}, port="5000") == []


@pytest.mark.parametrize("code", [
    "db = sqlite3.connect('datos.db')",
    "Path('subidas/x.txt').write_text(data)",
    "with open('log.txt', 'a') as f: f.write(x)",
    "fs.writeFileSync('out.json', data)",
])
def test_disk_writes_without_volume(andamio, make_repo, code):
    ext = ".js" if "fs." in code else ".py"
    found = findings(andamio, make_repo, {f"app{ext}": code + "\n"})
    assert has(found, "--volume", serious=False)
    # Con --volume ya está resuelto.
    assert not has(findings(andamio, make_repo, {f"app{ext}": code + "\n"}, volume=True), "--volume")


def test_committed_env_file_is_serious(andamio, make_repo):
    found = findings(andamio, make_repo, {".env": "API_KEY=x\n", "server.js": CLEAN_NODE})
    assert has(found, ".env", serious=True)


def test_python_main_block_only_counts_if_the_container_runs_the_file(andamio, make_repo):
    code = ('from fastapi import FastAPI\napp = FastAPI()\n\nif __name__ == "__main__":\n'
            '    import uvicorn\n    uvicorn.run(app, host="127.0.0.1", port=8000)\n')
    uvicorn = 'CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port $PORT"]\n'
    assert findings(andamio, make_repo, {"main.py": code, "Dockerfile": uvicorn}, port="8000") == []
    plain = 'CMD ["python", "main.py"]\n'
    assert has(findings(andamio, make_repo, {"main.py": code, "Dockerfile": plain}, port="8000"), "localhost")


def test_tests_and_dependencies_are_ignored(andamio, make_repo):
    files = {"tests/test_app.py": "app.run()\n", "node_modules/x/index.js": 'listen(1, "localhost")\n',
             "server.js": CLEAN_NODE}
    assert findings(andamio, make_repo, files) == []


def test_precheck_exit_codes(make_repo, env):
    """_precheck sale con 2 si hay algo grave (app create pregunta si seguir) y con 0 si no."""
    andamio = str(ROOT / "bin" / "andamio")
    bad = make_repo("mala", {"server.js": 'app.listen(3000, "localhost")\n'})
    good = make_repo("buena", {"server.js": CLEAN_NODE})
    assert subprocess.run([andamio, "_precheck", str(bad), "3000", "0"], env=env, capture_output=True).returncode == 2
    assert subprocess.run([andamio, "_precheck", str(good), "3000", "0"], env=env, capture_output=True).returncode == 0
