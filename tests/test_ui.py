"""andamio ui: el panel local. Que solo te responda a ti y que sus datos salgan bien.

Corre de verdad (bin/andamio ui) en una copia de mentira, con un `ssh` falso que devuelve el
estado de un servidor inventado: nada sale de la máquina.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import subprocess
import time

import pytest

LIVE = {"apps": {"web": {"created": "2026-10-10T20:00:00Z", "id": "abc123def456", "state": "running",
                         "health": "healthy", "started": "2026-10-10T20:00:00Z", "restarts": 0,
                         "version": "1a2b3c4", "mem": "40MiB", "cpu": "0.5%"}},
        "server": {"uptime": 3600.0, "load": 0.1, "cpus": 2, "mem_total": 2 * 1024**3, "mem_used": 1024**3,
                   "disk_total": 50 * 1024**3, "disk_used": 10 * 1024**3}}

FAKE_SSH = """#!/bin/sh
# ssh de mentira: el estado del servidor (python3 por stdin) y unas líneas de logs.
case "$*" in
  *" python3 -") cat > /dev/null; cat "$FAKE_LIVE" ;;
  *"docker logs"*) echo "linea uno"; echo "linea <dos> & tres" ;;
esac
"""


@pytest.fixture
def panel(fake_copy, env, tmp_path):
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    (fake_bin / "ssh").write_text(FAKE_SSH)
    (fake_bin / "ssh").chmod(0o755)
    (tmp_path / "live.json").write_text(json.dumps(LIVE))
    e = {**env, "PATH": f"{fake_bin}:{env['PATH']}", "FAKE_LIVE": str(tmp_path / "live.json")}
    proc = subprocess.Popen([str(fake_copy / "bin" / "andamio"), "ui", "--no-browser"], cwd=fake_copy, env=e,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url, deadline = None, time.time() + 20
    while time.time() < deadline and not url:
        line = proc.stdout.readline()
        m = re.search(r"http://127\.0\.0\.1:(\d+)/\?t=([\w-]+)", line)
        if m:
            url = m
    assert url, "andamio ui no mostró su link"
    port, token = int(url.group(1)), url.group(2)
    yield port, token
    proc.terminate()
    proc.wait(timeout=10)


def get(port, path, headers=None, method="GET"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    c.request(method, path, headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


def login(port, token) -> dict:
    status, headers, _ = get(port, f"/?t={token}")
    assert status == 303 and headers["Location"] == "/"
    cookie = headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    return {"Cookie": cookie.split(";")[0]}


def test_only_with_the_key(panel):
    port, token = panel
    assert get(port, "/api/apps")[0] == 403
    assert get(port, "/?t=otra-clave")[0] == 403
    auth = login(port, token)
    assert get(port, "/api/apps", auth)[0] == 200


def test_other_sites_cannot_use_it(panel):
    port, token = panel
    auth = login(port, token)
    # DNS rebinding: un dominio ajeno que apunta a 127.0.0.1.
    assert get(port, "/api/apps", {**auth, "Host": f"malo.example:{port}"})[0] == 403
    assert get(port, "/api/apps", {**auth, "Origin": "https://malo.example"})[0] == 403
    assert get(port, "/api/apps", {**auth, "Origin": f"http://127.0.0.1:{port}"})[0] == 200


def test_view_only_and_safe_headers(panel):
    port, token = panel
    auth = login(port, token)
    assert get(port, "/api/apps", auth, method="POST")[0] == 405
    status, headers, body = get(port, "/", auth)
    assert status == 200 and b"/app.js" in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY" and headers["Cache-Control"] == "no-store"
    for path in ("/app.css", "/app.js"):
        assert get(port, path, auth)[0] == 200
    for path in ("/../bin/andamio", "/api/app/..%2F..%2Fetc", "/api/app/nada", "/ui/index.html"):
        assert get(port, path, auth)[0] == 404, path


def test_apps_and_one_app(panel):
    port, token = panel
    auth = login(port, token)
    data = json.loads(get(port, "/api/apps", auth)[2])
    assert data["error"] == "" and data["domain"] == "ejemplo.com"
    assert data["server"]["cpus"] == 2
    web = data["apps"][0]
    assert web["name"] == "web" and web["url"] == "https://web.ejemplo.com" and web["access"] == "vpn"
    assert web["live"]["version"] == "1a2b3c4" and web["mem"] == "256m"

    one = json.loads(get(port, "/api/app/web", auth)[2])["app"]
    assert one["live"]["mem"] == "40MiB" and one["worker"] == "node worker.js"
    assert one["deploys"] == [] and one["cron"] == []

    meta = json.loads(get(port, "/api/meta", auth)[2])
    assert meta["lang"] == "es" and meta["server"] == "mi-vps"


def test_live_logs(panel):
    port, token = panel
    auth = login(port, token)
    status, headers, body = get(port, "/api/logs/web", auth)
    assert status == 200 and headers["Content-Type"].startswith("text/event-stream")
    events = [json.loads(l[6:]) for l in body.decode().splitlines() if l.startswith("data: ") and l != "data: {}"]
    assert events == ["linea uno", "linea <dos> & tres"]
    assert b"event: end" in body


def test_without_server(panel, tmp_path):
    """Si el servidor no responde, las apps se ven igual (de tus archivos) y se dice por qué."""
    port, token = panel
    auth = login(port, token)
    (tmp_path / "live.json").write_text("no es json")
    data = json.loads(get(port, "/api/apps", auth)[2])
    assert data["error"] and data["apps"][0]["name"] == "web" and data["apps"][0]["live"] is None
