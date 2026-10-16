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
from pathlib import Path

import pytest

LIVE = {"apps": {"web": {"created": "2026-10-10T20:00:00Z", "id": "abc123def456", "state": "running",
                         "health": "healthy", "started": "2026-10-10T20:00:00Z", "restarts": 0,
                         "version": "1a2b3c4", "mem": "40MiB", "cpu": "0.5%"}},
        "server": {"uptime": 3600.0, "load": 0.1, "cpus": 2, "mem_total": 2 * 1024**3, "mem_used": 1024**3,
                   "disk_total": 50 * 1024**3, "disk_used": 10 * 1024**3},
        "platform": {"backups": {"configured": True, "result": "success", "last": 1, "next": 2, "running": False},
                     "alerts": {"ntfy": True, "telegram": False}}}

METRICS = {"series": {"cpu": [[1000, 1.5], [1120, 2.0]], "mem": [[1000, 4e7]], "rx": [], "tx": []},
           "error": "", "start": 0, "end": 21600, "step": 120}
BACKUPS = {"configured": True, "result": "success", "last": 1, "next": 2, "running": False, "listed": True, "listed_at": 5,
           "snapshots": [{"id": "ab" * 32, "short": "abababab", "time": 4, "secs": 130, "size": 2e9, "added": 4e6, "files": 9}]}

FAKE_SSH = """#!/bin/sh
# ssh de mentira: el estado del servidor (python3 por stdin), las métricas, los respaldos y
# unas líneas de logs. El último script recibido queda en $FAKE_LIVE.sent.
case "$*" in
  *" python3 -")
    cat > "$FAKE_LIVE.sent"
    if grep -q '"sparks": {}' "$FAKE_LIVE.sent"; then echo '{"sparks": {"web": [[0, 1.5], [1800, 2.0]]}, "start": 0, "end": 1800, "step": 1800, "error": ""}'
    elif grep -q services_of "$FAKE_LIVE.sent"; then echo '{"services_of": "web", "error": "", "services": [{"name": "web-app-3", "kind": "app", "status": "healthy", "mem": 41943040, "cpu": 0.5}, {"name": "postgres", "kind": "postgres", "status": "healthy", "mem": 83886080, "cpu": 1.2}]}'
    elif grep -q '"outages"' "$FAKE_LIVE.sent"; then echo '{"start": 0, "end": 7200, "error": "", "hours": [[3600, 1.0], [7200, null]], "outages": [{"start": 100, "end": 700, "mins": 10, "ongoing": false}]}'
    elif grep -q quantile_over_time "$FAKE_LIVE.sent"; then echo '{"mem_peak": 251658240, "cpu_p95": 1.0, "cpu_max": 3.0, "samples": 2016, "error": ""}'
    elif grep -q query_range "$FAKE_LIVE.sent"; then cat "$FAKE_METRICS"
    elif grep -q snapshots.json "$FAKE_LIVE.sent"; then cat "$FAKE_BACKUPS"
    elif grep -qF 'print(json.dumps({"ntfy"' "$FAKE_LIVE.sent"; then echo '{"ntfy": false, "telegram": true}'
    elif grep -q avg_over_time "$FAKE_LIVE.sent"; then echo '{"apps": {"web": {"24h": 99.5, "7d": 97.25}}, "error": ""}'
    else cat "$FAKE_LIVE"; fi ;;
  *"app-sql"*)
    echo "$*" > "$FAKE_LIVE.sql"
    case "$*" in
      *--tables) printf "schema,name,rows,columns\npublic,users,3,\\"id integer, email text\\"\n" ;;
      *--query) q=$(cat); case "$q" in
        *boom*) echo "ERROR:  syntax error at or near \\"boom\\"" >&2; exit 3 ;;
        *query_to_xml*) printf 'schema,name,rows,exact,columns\npublic,users,3,t,"[[""id"", ""integer""], [""email"", ""text""]]"\n' ;;
        *) printf "n,email\n42,\n" ;; esac ;;
    esac ;;
  *"andamio-cron/"*) printf '\\0360 1700000000 3\\nhola\\nlisto\\n\\0362 1699990000 1\\nboom\\n' ;;
  *"docker logs"*) echo "$*" > "$FAKE_LIVE.logs"; echo "linea uno"; echo "linea <dos> & tres" ;;
  *"sudo -S -p"*) read -r pw; [ "$pw" = "la-correcta" ] ;;
esac
"""


@pytest.fixture
def panel(fake_copy, env, tmp_path):
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    (fake_bin / "ssh").write_text(FAKE_SSH)
    (fake_bin / "ssh").chmod(0o755)
    (tmp_path / "live.json").write_text(json.dumps(LIVE))
    (tmp_path / "metrics.json").write_text(json.dumps(METRICS))
    (tmp_path / "backups.json").write_text(json.dumps(BACKUPS))
    run = tmp_path / "run"   # como $XDG_RUNTIME_DIR: ahí se recuerda la contraseña de sudo
    run.mkdir(mode=0o700)
    e = {**env, "PATH": f"{fake_bin}:{env['PATH']}", "FAKE_LIVE": str(tmp_path / "live.json"), "XDG_RUNTIME_DIR": str(run),
         "FAKE_METRICS": str(tmp_path / "metrics.json"), "FAKE_BACKUPS": str(tmp_path / "backups.json")}
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


def get(port, path, headers=None, method="GET", body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    c.request(method, path, body=body, headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
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
    assert get(port, "/api/apps", auth, method="PUT")[0] == 405
    status, headers, body = get(port, "/", auth)
    assert status == 200 and b"/assets/" in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY" and headers["Cache-Control"] == "no-store"
    for path in re.findall(rb'(?:src|href)="(/assets/[^"]+)"', body):
        assert get(port, path.decode(), auth)[0] == 200
    for path in ("/../bin/andamio", "/api/app/..%2F..%2Fetc", "/api/app/nada", "/ui/index.html",
                 "/assets/../index.html", "/assets/%2e%2e%2fbin"):
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
    assert "deploys" not in one and one["cron"] == []   # los deploys van aparte (/api/deploys?app=)

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


# ---- Fase 2: acciones ----

def session(port, token):
    auth = login(port, token)
    csrf = json.loads(get(port, "/api/meta", auth)[2])["csrf"]
    return {**auth, "Origin": f"http://127.0.0.1:{port}", "X-Andamio-CSRF": csrf, "Content-Type": "application/json"}


def post(port, path, headers, data):
    status, _, body = get(port, path, headers, method="POST", body=json.dumps(data))
    return status, (json.loads(body) if body.startswith(b"{") else body)


def events(port, headers, jid, until="done", timeout=60):
    """Los eventos de una acción hasta `until` (prompt o done)."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    c.request("GET", f"/api/jobs/{jid}/events", headers={"Host": f"127.0.0.1:{port}", "Cookie": headers["Cookie"]})
    r = c.getresponse()
    out, kind = [], None
    while True:
        line = r.fp.readline().decode()
        if not line:
            break
        line = line.rstrip("\n")
        if line.startswith("event: "):
            kind = line[7:]
        elif line.startswith("data: ") and kind:
            out.append((kind, json.loads(line[6:])))
            if kind == until:
                break
    c.close()
    return out


def test_actions_need_the_session_key_and_origin(panel):
    port, token = panel
    h = session(port, token)
    body = {"action": "stop", "app": "web"}
    assert post(port, "/api/jobs", {k: v for k, v in h.items() if k != "X-Andamio-CSRF"}, body)[0] == 403
    assert post(port, "/api/jobs", {**h, "X-Andamio-CSRF": "otra"}, body)[0] == 403
    assert post(port, "/api/jobs", {k: v for k, v in h.items() if k != "Origin"}, body)[0] == 403
    assert post(port, "/api/jobs", {**h, "Origin": "https://malo.example"}, body)[0] == 403
    assert post(port, "/api/jobs", {**h, "Content-Type": "text/plain"}, body)[0] == 403
    assert post(port, "/api/jobs", {k: v for k, v in h.items() if k != "Cookie"}, body)[0] == 403


@pytest.mark.parametrize("body, error", [
    ({"action": "stop", "app": "nada"}, "No existe"),
    ({"action": "stop", "app": "../web"}, "No existe"),
    ({"action": "set", "app": "web", "set": {"mem": "12x"}}, "inválido"),
    ({"action": "set", "app": "web", "set": {"mem": "512m; rm -rf /"}}, "inválido"),
    ({"action": "set", "app": "web", "set": {"port": "--public"}}, "inválido"),
    ({"action": "set", "app": "web", "set": {}}, "Nada que cambiar"),
    ({"action": "cron-run", "app": "web", "task": "nada"}, "no tiene una tarea"),
    ({"action": "rollback", "app": "web"}, "Commit inválido"),
    ({"action": "rollback", "app": "web", "sha": "1a2b3c4"}, "Commit inválido"),
    ({"action": "rollback", "app": "web", "sha": "a" * 40 + "; rm"}, "Commit inválido"),
    ({"action": "restore", "app": "web", "snapshot": "x;y", "understood": True, "confirm": "web"}, "Respaldo inválido"),
    ({"action": "inventada", "app": "web"}, "desconocida"),
])
def test_only_valid_actions(panel, body, error):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), body)
    assert status == 400 and error in data["error"]


def test_sudo_inside_the_terminal(panel, fake_copy):
    """La contraseña se pide en la terminal; una mala se vuelve a pedir; nunca aparece en la salida."""
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, {"action": "stop", "app": "web"})
    assert status == 201 and job["command"] == "andamio app stop web"
    first = events(port, h, job["id"], until="prompt")
    assert first[0] == ("line", "$ andamio app stop web") and first[-1][0] == "prompt"

    # Mientras espera, es la única acción: otra no puede empezar.
    status, busy = post(port, "/api/jobs", h, {"action": "start", "app": "web"})
    assert status == 409 and busy["running"] == "andamio app stop web"

    assert post(port, f"/api/jobs/{job['id']}/password", h, {"password": "la-mala"})[0] == 200
    time.sleep(1)
    assert post(port, f"/api/jobs/{job['id']}/password", h, {"password": "la-correcta"})[0] == 200
    allev = events(port, h, job["id"])
    texts = [t for _, t in allev]
    assert any("No es la contraseña" in t for t in texts) and any("Contraseña correcta" in t for t in texts)
    assert allev[-1][0] == "done"
    # Corrió el comando de la CLI (aquí falla al subir: la copia de prueba no tiene remoto).
    assert "stopped: true" in (fake_copy / "apps/web/app.yml").read_text()
    assert not any("la-correcta" in t or "la-mala" in t for t in texts)


def test_cancel_while_asking_for_the_password(panel, fake_copy):
    port, token = panel
    h = session(port, token)
    _, job = post(port, "/api/jobs", h, {"action": "set", "app": "web", "set": {"mem": "512m"}})
    assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt"
    assert post(port, f"/api/jobs/{job['id']}/cancel", h, {})[0] == 200
    allev = events(port, h, job["id"])
    assert allev[-1] == ("done", "130") and any("Cancelado" in t for _, t in allev)
    assert "mem: 256m" in (fake_copy / "apps/web/app.yml").read_text(), "cancelada: nada cambió"
    # Ya terminó: se puede correr otra.
    assert post(port, "/api/jobs", h, {"action": "start", "app": "web"})[0] == 201


def test_cli_questions_take_their_default_from_the_panel(fake_copy, env):
    """Desde el panel, cada pregunta de la CLI toma su respuesta por defecto: los "¿seguro?" frenan."""
    andamio = str(fake_copy / "bin" / "andamio")
    e = {**env, "ANDAMIO_ASSUME": "default"}
    assert subprocess.run([andamio, "_ask", "¿Aplicar?", "s"], env=e, capture_output=True).returncode == 0
    assert subprocess.run([andamio, "_ask", "¿Borrar?", "n"], env=e, capture_output=True).returncode == 1


# ---- Fase 2b: secretos, tareas, listas, reintentar ----

@pytest.mark.parametrize("body, error", [
    ({"action": "secret-set", "app": "web", "key": "minusculas", "value": "x"}, "inválido"),
    ({"action": "secret-set", "app": "web", "key": "DATABASE_URL", "value": "x"}, "inválido"),
    ({"action": "secret-set", "app": "web", "key": "API_KEY", "value": ""}, "una sola línea"),
    ({"action": "secret-set", "app": "web", "key": "API_KEY", "value": "a\nb"}, "una sola línea"),
    ({"action": "secret-set", "app": "web", "key": "API_KEY", "value": "x" * 5000}, "una sola línea"),
    ({"action": "cron-add", "app": "web", "schedule": "0 25 * * *", "command": "x"}, "hora"),
    ({"action": "cron-add", "app": "web", "schedule": "@daily", "command": ""}, "una sola línea"),
    ({"action": "cron-add", "app": "web", "schedule": "@daily", "command": "x", "task": "Mala"}, "inválido"),
    ({"action": "cron-rm", "app": "web", "task": "nada"}, "no tiene una tarea"),
    ({"action": "domain-add", "app": "web", "value": "no es dominio"}, "inválido"),
    ({"action": "cors-add", "app": "web", "value": "*"}, "inválido"),
    ({"action": "cors-add", "app": "web", "value": "https://x.com/ruta"}, "inválido"),
    ({"action": "volume-add", "app": "web", "value": "/a/../etc"}, "inválido"),
    ({"action": "volume-add", "app": "web", "value": "datos"}, "inválido"),
])
def test_2b_rejects_bad_input(panel, body, error):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), body)
    assert status == 400 and error in data["error"], data


def run_with_password(port, h, body):
    """Corre una acción hasta el final, con la contraseña de sudo correcta si la pide."""
    status, job = post(port, "/api/jobs", h, body)
    assert status == 201, job
    first = events(port, h, job["id"], until="prompt", timeout=60)
    if first and first[-1][0] == "prompt":
        post(port, f"/api/jobs/{job['id']}/password", h, {"password": "la-correcta"})
    return job, events(port, h, job["id"])


def test_secret_value_never_leaks(panel, fake_copy, tmp_path):
    """El valor de un secreto entra por stdin: no aparece en el comando, ni en la salida."""
    port, token = panel
    h = session(port, token)
    secret = "valor-supersecreto-12345"
    job, allev = run_with_password(port, h, {"action": "secret-set", "app": "web", "key": "API_KEY", "value": secret})
    assert job["command"] == "andamio app secret set web API_KEY"
    texts = " ".join(t for _, t in allev)
    assert secret not in texts and secret not in job["command"]
    assert "API_KEY" in texts


@pytest.mark.parametrize("pairs, error", [
    ([], "Entre 1 y 100"),
    ([{"key": "minusculas", "value": "x"}], "inválido"),
    ([{"key": "TAG", "value": "x"}], "inválido"),
    ([{"key": "A", "value": "1"}, {"key": "A", "value": "2"}], "repetido"),
    ([{"key": "A", "value": "a\nb"}], "una sola línea"),
    ([{"key": "A", "value": ""}], "una sola línea"),
])
def test_secret_import_checks_every_pair(panel, pairs, error):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), {"action": "secret-import", "app": "web", "pairs": pairs})
    assert status == 400 and error in data["error"], data


def test_secret_import_values_never_leak(panel):
    port, token = panel
    h = session(port, token)
    secret = "otro-valor-supersecreto-678"
    job, allev = run_with_password(port, h, {"action": "secret-import", "app": "web",
                                             "pairs": [{"key": "API_KEY", "value": secret}, {"key": "OTRA", "value": "x"}]})
    assert job["command"] == "andamio app secret import web -"
    assert secret not in " ".join(t for _, t in allev)


def test_cron_add_uses_the_panel_timezone(panel, fake_copy):
    port, token = panel
    h = session(port, token)
    job, allev = run_with_password(port, h, {"action": "cron-add", "app": "web", "schedule": "0 3 * * *",
                                             "command": "python limpiar.py", "task": "", "timezone": "America/Lima"})
    assert job["command"] == "andamio app cron add web '0 3 * * *' 'python limpiar.py'"
    assert 'andamio_timezone: "America/Lima"' in (fake_copy / "ansible/group_vars/all.yml").read_text()
    assert "name: limpiar" in (fake_copy / "apps/web/app.yml").read_text()


def test_domain_needs_explicit_ok_when_dns_is_wrong(panel, fake_copy):
    """Sin el "agregarlo igual" de la página, un dominio que no apunta al servidor no se agrega."""
    port, token = panel
    h = session(port, token)
    _, allev = run_with_password(port, h, {"action": "domain-add", "app": "web", "value": "api.no-existe-andamio.invalid"})
    assert allev[-1][0] == "done" and allev[-1][1] != "0"
    assert "no-existe-andamio" not in (fake_copy / "apps/web/app.yml").read_text()
    _, allev = run_with_password(port, h, {"action": "domain-add", "app": "web", "value": "api.no-existe-andamio.invalid",
                                           "dns_ok": True})
    assert any("Agregado igual" in t for _, t in allev)
    assert "api.no-existe-andamio.invalid" in (fake_copy / "apps/web/app.yml").read_text()


def test_dns_and_cron_preview_endpoints(panel):
    port, token = panel
    auth = login(port, token)
    d = json.loads(get(port, "/api/dns?domain=api.no-existe-andamio.invalid", auth)[2])
    assert d["ok"] is False and d["ip"] == "203.0.113.10"
    assert "error" in json.loads(get(port, "/api/dns?domain=no%20valido", auth)[2])
    ok = json.loads(get(port, "/api/cron-preview?schedule=30%208%20*%20*%201-5&tz=UTC", auth)[2])
    assert ok["calendar"] == "Mon..Fri *-*-* 08:30:00" and ok["timezone"] == "UTC"
    bad = json.loads(get(port, "/api/cron-preview?schedule=0%2025%20*%20*%20*&tz=UTC", auth)[2])
    assert "hora" in bad["error"]


def test_retry_needs_no_password(panel):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, {"action": "retry", "app": "web"})
    assert status == 201 and job["command"] == "andamio app retry web"
    allev = events(port, h, job["id"])
    assert not any(k == "prompt" for k, _ in allev) and allev[-1][0] == "done"


# ---- El inicio: plataforma, seguridad y deploys recientes ----

def test_home_brings_platform_and_last_security_check(panel, fake_copy, tmp_path):
    import hashlib
    port, token = panel
    auth = login(port, token)
    cache = tmp_path / "home" / ".cache" / "andamio"
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(fake_copy.resolve()).encode()).hexdigest()[:12]
    check = {"at": 1, "ok": 14, "warn": 1, "fail": 0,
             "items": [{"status": "WARN", "area": "Backups", "what": "viejo", "fix": "andamio backups"}]}
    (cache / f"estado-{key}.json").write_text(json.dumps(check))
    data = json.loads(get(port, "/api/apps", auth)[2])
    assert data["security"] == check
    assert data["platform"] == LIVE["platform"]
    assert data["backups_enabled"] is False


def test_recent_deploys_endpoint(panel):
    port, token = panel
    data = json.loads(get(port, "/api/deploys", login(port, token))[2])
    assert data == {"deploys": []}, "sin GitHub (como aquí), una lista vacía: la página lo dice"


def test_security_check_runs_andamio_estado(panel):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, {"action": "estado"})
    assert status == 201 and job["command"] == "andamio estado"
    assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt", "estado usa sudo: pide la contraseña"
    post(port, f"/api/jobs/{job['id']}/cancel", h, {})
    assert events(port, h, job["id"])[-1] == ("done", "130")


def test_estado_saves_its_summary(andamio, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    andamio.estado_save([["OK", "SSH", "solo llave", ""], ["WARN", "Disco", "al 82%", "libera"],
                         ["FAIL", "Internet", "el 22 responde", "ciérralo"]])
    saved = json.loads(andamio.estado_cache().read_text())
    assert (saved["ok"], saved["warn"], saved["fail"]) == (1, 1, 1)
    assert [i["area"] for i in saved["items"]] == ["Disco", "Internet"], "solo lo que no está bien"

from conftest import ROOT  # noqa: E402


# ---- Fase 3: crear una app ----

BASE = {"name": "nueva", "repo": "tu-usuario/nueva", "host": "", "port": "3000", "mem": "256m", "health": "",
        "access": "vpn", "db": False, "redis": False, "volume": "", "start": "", "precheck_ok": False}


@pytest.mark.parametrize("change, error", [
    ({"name": "A"}, "Nombre inválido"),
    ({"name": "web"}, "Ya hay una app web"),
    ({"repo": "sin-dueno"}, "Repo inválido"),
    ({"repo": ""}, "plantilla"),
    ({"host": "web"}, "ya la usa otra app"),
    ({"host": "Mal_Host"}, "Dirección inválida"),
    ({"port": "1"}, "Puerto inválido"),
    ({"mem": "12x"}, "Memoria inválida"),
    ({"health": "sin-barra"}, "Ruta de salud inválida"),
    ({"volume": "/etc"}, "Carpeta inválida"),
    ({"start": "a\nb"}, "una sola línea"),
])
def test_create_rejects_bad_input(panel, change, error):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), {"action": "create", "create": {**BASE, **change}})
    assert status == 400 and error in data["error"], data


def test_create_runs_the_same_cli_command(andamio, fake_copy, monkeypatch):
    """El formulario arma el mismo `andamio app create`, con lo decidido en la página."""
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_create_argv({**BASE, "host": "api", "access": "public", "db": True, "volume": "/data/",
                                   "health": "/healthz", "start": "uvicorn main:app --port $PORT", "precheck_ok": True})
    assert plan["argv"] == ["app", "create", "nueva", "--repo", "tu-usuario/nueva", "--host", "api", "--port", "3000",
                            "--mem", "256m", "--health", "/healthz", "--public", "--db", "--volume", "/data"]
    assert plan["env"] == {"ANDAMIO_CREATE_OK": "1", "ANDAMIO_PRECHECK_OK": "1", "ANDAMIO_START_CMD": "uvicorn main:app --port $PORT"}
    assert plan["sudo"] is True
    # Sin marcar "crear igual", la revisión previa grave frena (la CLI pregunta y dice que no).
    assert "ANDAMIO_PRECHECK_OK" not in andamio.ui_create_argv(BASE)["env"]


def test_cli_honors_the_panel_answers(fake_copy, env):
    """confirm con su variable: sigue solo si el panel lo confirmó; sin ella, frena."""
    script = fake_copy / "probar.sh"
    script.write_text('source <(sed -n "/^ask() {/,/^}/p;/^confirm() {/,/^}/p" bin/andamio-app)\n'
                      'L() { printf "%s" "$1"; }; die() { echo "$*"; exit 1; }; INFRA=$PWD\n'
                      'confirm "¿Crear?" ANDAMIO_CREATE_OK && echo SIGUE\n')
    run = lambda e: subprocess.run(["bash", str(script)], cwd=fake_copy, env={**env, **e}, capture_output=True,
                                   text=True, start_new_session=True, stdin=subprocess.DEVNULL)
    assert "SIGUE" in run({"ANDAMIO_CREATE_OK": "1"}).stdout
    r = run({"ANDAMIO_ASSUME": "default"})
    assert "SIGUE" not in r.stdout and "Cancelado" in r.stdout


def test_scaffold_takes_the_start_command_from_the_panel(tmp_path, env):
    app = tmp_path / "app"
    app.mkdir()
    (app / "package.json").write_text('{"scripts": {"start": "node server.js"}}')
    out = tmp_path / "out"
    r = subprocess.run([str(ROOT / "bin" / "andamio"), "_scaffold", str(app), "", str(out)], capture_output=True, text=True,
                       env={**env, "ANDAMIO_ASSUME": "default", "ANDAMIO_START_CMD": "node dist/main.js"},
                       stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "exec node dist/main.js" in (app / "Dockerfile").read_text()

from conftest import git  # noqa: E402


# ---- Variables de entorno al crear ----

def test_detects_env_vars_the_code_uses(andamio, make_repo):
    repo = make_repo("conenv", {
        "main.py": 'import os\nkey = os.environ["ANTHROPIC_API_KEY"]\nmodo = os.getenv("MODO", "x")\nport = os.environ["PORT"]\n',
        "web/app.js": "const u = process.env.STRIPE_KEY;\nconst d = process.env['DATABASE_URL'];\n",
        "cmd/main.go": 'v := os.Getenv("SALUDO")\n',
        ".env.example": "export SENTRY_DSN=\nANTHROPIC_API_KEY=\n",
        "node_modules/x/i.js": "process.env.NO_CUENTA\n",
    })
    found = {e["key"]: e["where"] for e in andamio.detect_env_names(repo)}
    assert found == {"ANTHROPIC_API_KEY": ".env.example:2",
                     "MODO": "main.py:3", "STRIPE_KEY": "web/app.js:1", "SALUDO": "cmd/main.go:1",
                     "SENTRY_DSN": ".env.example:1"}
    assert "PORT" not in found and "DATABASE_URL" not in found and "NO_CUENTA" not in found


def test_env_names_required_and_examples(andamio, make_repo):
    """Requerida solo con señal clara (getOrThrow, os.environ[...], process.env.X!); el ejemplo del
    .env.example, salvo secretos, marcadores y direcciones de tu máquina."""
    repo = make_repo("envreq", {
        "a.ts": "config.getOrThrow<string>('JWT_SECRET');\nconst t = process.env.TTL ?? '15m';\n"
                "const k = process.env.STRIPE_KEY!;\nif (process.env.FLAG !== 'x') {}\n",
        "b.py": "import os\nos.environ['MODO']\nos.getenv('NIVEL', 'info')\n",
        ".env.example": "TTL=15m\nJWT_SECRET=supersecreto\nAPI_URL=http://localhost:3000\nSITE=<tu-sitio>\nPAGE=\"20\"  # filas\n",
    })
    env = {e["key"]: e for e in andamio.detect_env_names(repo)}
    assert {k for k, e in env.items() if e["required"]} == {"JWT_SECRET", "STRIPE_KEY", "MODO"}
    assert {k: e["example"] for k, e in env.items() if e["example"]} == {"TTL": "15m", "PAGE": "20"}


def test_create_one_of_several_apps_in_a_repo(andamio, fake_copy, monkeypatch):
    """Una carpeta del repo (el back), construida desde la raíz y bajo la dirección de otra app."""
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_create_argv({**BASE, "host": "web", "dir": "backend", "context": ".", "path": "/api"})
    assert plan["argv"][plan["argv"].index("--dir"):plan["argv"].index("--dir") + 6] == \
        ["--dir", "backend", "--context", ".", "--path", "/api"]
    # web ya usa web (sin ruta): sin ruta, choca.
    assert "ya la usa" in andamio.ui_create_argv({**BASE, "host": "web", "dir": "backend"})
    assert andamio.ui_create_argv({**BASE, "branch": "production"})["argv"][-2:] == ["--branch", "production"] or         "--branch" in andamio.ui_create_argv({**BASE, "branch": "production"})["argv"]
    for bad in ({"dir": "../x"}, {"dir": "/abs"}, {"context": "."}, {"dir": "b", "context": "otra"}, {"path": "api"},
                {"dir": "b", "repo": ""}, {"branch": "a..b"}, {"branch": "x y"}):
        assert isinstance(andamio.ui_create_argv({**BASE, **bad}), str), bad


def test_create_with_its_own_domain(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_create_argv({**BASE, "domain": "Api.Ejemplo.com", "dns_ok": True})
    assert plan["argv"][plan["argv"].index("--domain") + 1] == "api.ejemplo.com"
    assert plan["env"]["ANDAMIO_DNS_OK"] == "1"
    assert "ANDAMIO_DNS_OK" not in andamio.ui_create_argv({**BASE, "domain": "api.ejemplo.com"})["env"]
    assert isinstance(andamio.ui_create_argv({**BASE, "domain": "no es dominio"}), str)


def test_create_preview_rejects_a_bad_folder(andamio):
    assert "error" in andamio.ui_create_preview("yo/app", "../etc")


def put(root, rel: str, text: str = "") -> None:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


def test_repo_folders_finds_the_apps_in_a_repo(andamio, tmp_path):
    put(tmp_path, "frontend/package.json", json.dumps({"scripts": {"start": "react-scripts start"}, "dependencies": {"react-scripts": "5"}}))
    put(tmp_path, "frontend/public/index.html")              # parte del front, no otra app
    put(tmp_path, "backend/Dockerfile", "FROM scratch\n")
    put(tmp_path, "node_modules/x/package.json", "{}")
    found = andamio.repo_folders(tmp_path)
    assert [f["dir"] for f in found] == ["backend", "frontend"]
    assert found[0]["dockerfile"] is True
    assert found[1]["framework"] == "React" and found[1]["role"] == "web"


def test_repo_folders_reads_workspaces_and_hides_libraries(andamio, tmp_path):
    """Un Turborepo: las apps que declara el repo primero, con su papel; sus paquetes, como librerías."""
    put(tmp_path, "package.json", json.dumps({"private": True, "workspaces": ["apps/*", "packages/*"]}))
    put(tmp_path, "apps/web/package.json", json.dumps({"scripts": {"start": "next start"}, "dependencies": {"next": "15"}}))
    put(tmp_path, "apps/api/package.json", json.dumps({"dependencies": {"@nestjs/core": "10"}}))
    put(tmp_path, "packages/ui/package.json", json.dumps({"main": "index.ts"}))
    put(tmp_path, "services/billing/go.mod", "module billing")
    put(tmp_path, "services/billing/main.go", "package main\nfunc main() {}\n")
    put(tmp_path, "libs/money/go.mod", "module money")
    put(tmp_path, "libs/money/money.go", "package money\n")
    put(tmp_path, "services/jobs/worker/requirements.txt", "celery==5\n")
    found = {f["dir"]: f for f in andamio.repo_folders(tmp_path)}
    assert found["apps/api"]["role"] == "api" and found["apps/api"]["framework"] == "NestJS" and found["apps/api"]["declared"]
    assert found["apps/web"]["role"] == "web" and not found["apps/web"]["lib"]
    assert found["packages/ui"]["lib"] and found["libs/money"]["lib"]
    assert not found["services/billing"]["lib"] and found["services/jobs/worker"]["role"] == "worker"
    order = [f["dir"] for f in andamio.repo_folders(tmp_path)]
    assert order.index("apps/web") < order.index("services/billing") < order.index("packages/ui")


def test_source_action_runs_the_cli(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_action_argv({"action": "source", "app": "web", "dir": "backend/", "context": ".", "watch_add": "/packages/"})
    assert plan["argv"] == ["app", "source", "web", "--dir", "backend", "--context", ".", "--watch-add", "packages/"]
    assert plan["sudo"] is False and plan["env"] == {"ANDAMIO_SOURCE_OK": "1"}
    for bad in ({"dir": "../x"}, {"context": "raiz"}, {"watch_add": "a b"}, {"watch_rm": "../.."}, {}):
        assert isinstance(andamio.ui_action_argv({"action": "source", "app": "web", **bad}), str), bad


def test_create_sends_variables_through_stdin(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_create_argv({**BASE, "secrets": [{"key": "API_KEY", "value": "sk-supersecreto"},
                                                        {"key": "MODO", "value": "prod"}]})
    assert plan["argv"][-2:] == ["--env-file", "-"]
    assert plan["stdin"] == "API_KEY=sk-supersecreto\nMODO=prod\n"
    assert "sk-supersecreto" not in " ".join(plan["argv"])
    for bad in ([{"key": "minus", "value": "x"}], [{"key": "TAG", "value": "x"}],
                [{"key": "A", "value": "x"}, {"key": "A", "value": "y"}], [{"key": "A", "value": "a\nb"}]):
        assert isinstance(andamio.ui_create_argv({**BASE, "secrets": bad}), str)


def test_create_job_never_shows_the_values(panel):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, {"action": "create", "create": {
        **BASE, "secrets": [{"key": "API_KEY", "value": "sk-nunca-se-ve-123"}]}})
    assert status == 201 and job["command"].endswith("--env-file -")
    first = events(port, h, job["id"], until="prompt")
    if first[-1][0] == "prompt":
        post(port, f"/api/jobs/{job['id']}/password", h, {"password": "la-correcta"})
    allev = events(port, h, job["id"])
    assert not any("sk-nunca-se-ve-123" in t for _, t in allev)


@pytest.mark.parametrize("content, error", [
    ("API_KEY=x\nminusculas=y\n", "Línea 2"),
    ("DATABASE_URL=postgres://x\n", "lo pone andamio"),
    ("SOLO_NOMBRE\n", "Línea 1"),
])
def test_env_file_is_checked_before_anything(fake_copy, env, tmp_path, content, error):
    f = tmp_path / "vars.env"
    f.write_text(content)
    r = subprocess.run([str(fake_copy / "bin" / "andamio-app"), "app", "create", "nueva", "--repo", "x/y", "--env-file", str(f)],
                       cwd=fake_copy, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    assert r.returncode != 0 and error in (r.stdout + r.stderr)
    assert "postgres://x" not in r.stdout + r.stderr, "nunca muestra un valor"
    assert git(fake_copy, "status", "--porcelain") == ""


# ---- Borrar una app: doble confirmación ----

@pytest.mark.parametrize("body", [
    {"action": "destroy", "app": "web"},
    {"action": "destroy", "app": "web", "understood": True},
    {"action": "destroy", "app": "web", "understood": True, "confirm": "Web"},
    {"action": "destroy", "app": "web", "understood": False, "confirm": "web"},
    {"action": "destroy", "app": "web", "understood": "true", "confirm": "web"},
])
def test_destroy_needs_both_confirmations(panel, fake_copy, body):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), body)
    assert status == 400 and "escribe el nombre exacto" in data["error"]
    assert (fake_copy / "apps/web/app.yml").exists()


def test_destroy_runs_the_cli_with_the_name_typed(panel):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, {"action": "destroy", "app": "web", "understood": True, "confirm": "web"})
    assert status == 201 and job["command"] == "andamio app destroy web"
    assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt", "pide la contraseña de sudo antes de tocar nada"
    post(port, f"/api/jobs/{job['id']}/cancel", h, {})
    assert events(port, h, job["id"])[-1] == ("done", "130")


def test_dashboard_cannot_be_deleted_from_the_panel(panel, fake_copy):
    with (fake_copy / "ansible/group_vars/all.yml").open("a") as f:
        f.write("andamio_dashboard_app: web\n")
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), {"action": "destroy", "app": "web", "understood": True, "confirm": "web"})
    assert status == 400 and "dashboard" in data["error"]


# ---- Historial de uso, volver a un deploy, respaldos ----

def test_metrics_of_an_app_and_of_the_server(panel, tmp_path):
    port, token = panel
    auth = login(port, token)
    data = json.loads(get(port, "/api/metrics?app=web&range=6h", auth)[2])
    assert data["series"]["cpu"] == METRICS["series"]["cpu"] and data["range"] == "6h"
    sent = (tmp_path / "live.json.sent").read_text()
    assert "web-(app|worker)-[0-9]+" in sent and '"step": 120' in sent, "solo los contenedores de esa app"
    get(port, "/api/metrics?range=24h", auth)
    assert "node_cpu_seconds_total" in (tmp_path / "live.json.sent").read_text(), "sin app: el servidor entero"
    assert "error" in json.loads(get(port, "/api/metrics?app=web&range=1y", auth)[2])
    assert json.loads(get(port, "/api/metrics?app=..%2Fweb&range=1h", auth)[2])["error"]


def test_backups_list_comes_without_sudo(panel):
    port, token = panel
    data = json.loads(get(port, "/api/backups", login(port, token))[2])
    assert data["snapshots"] == BACKUPS["snapshots"] and data["enabled"] is False


def test_rollback_runs_the_cli_without_asking_again(panel):
    port, token = panel
    h = session(port, token)
    sha = "a" * 40
    status, job = post(port, "/api/jobs", h, {"action": "rollback", "app": "web", "sha": sha})
    assert status == 201 and job["command"] == f"andamio app rollback web {sha}"
    allev = events(port, h, job["id"])
    assert not any(k == "prompt" for k, _ in allev), "un rollback es un deploy: no usa sudo"


@pytest.mark.parametrize("body", [
    {"action": "restore", "app": "web", "snapshot": "latest"},
    {"action": "restore", "app": "web", "snapshot": "latest", "understood": True},
    {"action": "restore", "app": "web", "snapshot": "latest", "understood": True, "confirm": "Web"},
    {"action": "restore", "app": "web", "snapshot": "latest", "understood": "true", "confirm": "web"},
])
def test_restore_needs_both_confirmations(panel, body):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), body)
    assert status == 400 and "escribe el nombre exacto" in data["error"]


def test_restore_and_backup_now_ask_for_sudo(panel):
    port, token = panel
    h = session(port, token)
    for body, command in [({"action": "restore", "app": "web", "snapshot": "abababab", "understood": True, "confirm": "web"},
                           "andamio app restore web abababab"),
                          ({"action": "backup-now"}, "andamio backups now"),
                          ({"action": "backup-list"}, "andamio backups list")]:
        status, job = post(port, "/api/jobs", h, body)
        assert status == 201 and job["command"] == command
        assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt", "usa sudo: pide la contraseña"
        post(port, f"/api/jobs/{job['id']}/cancel", h, {})
        assert events(port, h, job["id"])[-1] == ("done", "130")


# ---- Logs con búsqueda, Ctrl+K, historial, ajustes y varios servidores ----

def test_logs_bring_the_lines_you_ask_for(panel, tmp_path):
    port, token = panel
    auth = login(port, token)
    for asked, sent in [("1000", "--tail 1000"), ("5000", "--tail 5000"), ("99999", "--tail 200"), ("1;rm", "--tail 200")]:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", f"/api/logs/web?tail={asked}", headers={"Host": f"127.0.0.1:{port}", "Cookie": auth["Cookie"]})
        c.getresponse().read()
        c.close()
        assert sent in (tmp_path / "live.json.logs").read_text(), asked


def test_names_come_from_your_files_only(panel):
    port, token = panel
    data = json.loads(get(port, "/api/names", login(port, token))[2])
    assert [a["name"] for a in data["apps"]] == ["web"] and data["apps"][0]["stopped"] is False


def test_history_marks_what_can_be_undone(panel, fake_copy):
    yml = fake_copy / "apps/web/app.yml"
    yml.write_text(yml.read_text().replace("mem: 256m", "mem: 512m"))
    git(fake_copy, "commit", "-qam", "feat(apps): web: resources.mem=512m")
    (fake_copy / "apps/web/secrets.sops.env").write_text("X=1\n")
    git(fake_copy, "add", "-A")
    git(fake_copy, "commit", "-qm", "feat(apps): web: secreto X")
    port, token = panel
    changes = json.loads(get(port, "/api/history?app=web", login(port, token))[2])["changes"]
    secret, config = changes[0], changes[1]
    assert secret["kind"] == "secrets" and not secret["revertible"] and not secret["lines"], "un secreto nunca se deshace"
    assert config["kind"] == "config" and config["revertible"] and config["apps"] == ["web"]
    assert "-  mem: 256m" in config["lines"] and "+  mem: 512m" in config["lines"]
    assert get(port, "/api/history?app=..%2Fx", login(port, token))[0] == 400


def test_revert_asks_for_sudo_and_skips_the_cli_question(panel):
    port, token = panel
    h = session(port, token)
    sha = "b" * 40
    assert post(port, "/api/jobs", h, {"action": "revert", "app": "web", "commit": "abc"})[0] == 400
    status, job = post(port, "/api/jobs", h, {"action": "revert", "app": "web", "commit": sha})
    assert status == 201 and job["command"] == f"andamio app revert web {sha}"
    assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt"
    post(port, f"/api/jobs/{job['id']}/cancel", h, {})
    assert events(port, h, job["id"])[-1] == ("done", "130")


def test_settings_never_show_alert_addresses(panel):
    port, token = panel
    data = json.loads(get(port, "/api/settings", login(port, token))[2])
    assert data["alerts"] == {"ntfy": False, "telegram": True}
    assert data["ntfy_url"] == "" and "token" not in json.dumps(data).lower()
    assert "America/Bogota" in data["timezones"] and "UTC" in data["timezones"]
    assert data["tasks"] == 0 and data["domain"] == "ejemplo.com"


@pytest.mark.parametrize("body, command, sudo", [
    ({"action": "timezone", "timezone": "Europe/Madrid"}, "andamio zona Europe/Madrid", True),
    ({"action": "alert-test"}, "andamio alertas prueba", False),
    ({"action": "update-check"}, "andamio update --check", False),
    ({"action": "ntfy", "ntfy": "nuevo"}, "andamio alertas --ntfy nuevo", True),
    ({"action": "ntfy", "ntfy": "quitar"}, "andamio alertas --ntfy quitar", True),
    ({"action": "ntfy", "ntfy": "https://ntfy.ejemplo.com/alertas"},
     "andamio alertas --ntfy https://ntfy.ejemplo.com/alertas", True),
])
def test_settings_actions_run_the_cli(panel, body, command, sudo):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, body)
    assert status == 201 and job["command"] == command
    if sudo:
        assert events(port, h, job["id"], until="prompt")[-1][0] == "prompt"
        post(port, f"/api/jobs/{job['id']}/cancel", h, {})


@pytest.mark.parametrize("tz", ["Marte/Olimpo", "../etc", "America/Bogota; rm -rf /", ""])
def test_timezone_is_checked(panel, tz):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), {"action": "timezone", "timezone": tz})
    assert status == 400 and "Zona horaria inválida" in data["error"]


def test_switch_opens_the_panel_of_another_copy(panel, fake_copy, tmp_path):
    port, token = panel
    h = session(port, token)
    assert post(port, "/api/switch", h, {"path": "/etc"})[0] == 400, "solo tus copias"
    assert post(port, "/api/switch", h, {"path": str(fake_copy)})[0] == 400, "esta misma no"
    other = tmp_path / "otra"
    (other / "ansible/group_vars").mkdir(parents=True)
    (other / "ansible/group_vars/all.yml").write_text("andamio_domain: otro.example\n")
    (other / "bin").mkdir()
    (other / "bin/andamio").write_text("#!/bin/sh\necho '  http://127.0.0.1:5555/?t=abc-123'\nexec sleep 60\n")
    (other / "bin/andamio").chmod(0o755)
    copies = tmp_path / "home/.config/andamio/copias"
    copies.parent.mkdir(parents=True, exist_ok=True)
    copies.write_text(f"{fake_copy}\n{other}\n")
    data = json.loads(get(port, "/api/copies", h)[2])["copies"]
    assert [(c["domain"], c["current"]) for c in data] == [("ejemplo.com", True), ("otro.example", False)]
    status, data = post(port, "/api/switch", h, {"path": str(other)})
    assert status == 200 and data["url"] == "http://127.0.0.1:5555/?t=abc-123"
    assert post(port, "/api/switch", h, {"path": str(other)})[1]["url"] == data["url"], "ya abierto: el mismo"


@pytest.mark.parametrize("value", ["http://ntfy.ejemplo.com/a", "https://ntfy.ejemplo.com/", "https://x.com/a; rm -rf /",
                                   "https://x.com/a/b", "", "--help"])
def test_ntfy_only_takes_new_off_or_a_topic_url(panel, value):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), {"action": "ntfy", "ntfy": value})
    assert status == 400 and "ntfy" in data["error"]


# ---- Telegram guiado y consola SQL ----

@pytest.mark.parametrize("body", [
    {"action": "telegram", "token": "corto", "chat": "123"},
    {"action": "telegram", "token": "123456789:" + "A" * 35, "chat": "abc"},
    {"action": "telegram", "token": "123456789:" + "A" * 35 + "; rm", "chat": "123"},
])
def test_telegram_needs_a_token_and_a_chat(panel, body):
    port, token = panel
    status, data = post(port, "/api/jobs", session(port, token), body)
    assert status == 400 and "token" in data["error"]


def test_telegram_token_never_leaks(panel):
    port, token = panel
    h = session(port, token)
    bot = "987654321:" + "Z" * 35
    job, allev = run_with_password(port, h, {"action": "telegram", "token": bot, "chat": "12345"})
    assert job["command"] == "andamio telegram --chat 12345 --token-stdin"
    assert bot not in " ".join(t for _, t in allev) and bot not in job["command"]


def test_telegram_check_rejects_a_bad_token_without_calling_telegram(panel):
    port, token = panel
    h = session(port, token)
    assert "no parece un token" in post(port, "/api/telegram/check", h, {"token": "hola"})[1]["error"]
    assert post(port, "/api/telegram/chats", h, {"token": "hola"})[0] == 400


def test_sql_console_is_read_only_and_query_goes_by_stdin(panel, fake_copy, tmp_path):
    port, token = panel
    h = session(port, token)
    assert "no tiene base" in post(port, "/api/sql", h, {"app": "web", "query": "select 1"})[1]["error"]
    yml = fake_copy / "apps/web/app.yml"
    yml.write_text(yml.read_text().replace("db: false", "db: true"))
    tables = json.loads(get(port, "/api/sql/tables?app=web", h)[2])
    assert tables["tables"] == [{"schema": "public", "name": "users", "rows": 3, "exact": True,
                                 "columns": [{"name": "id", "type": "integer"}, {"name": "email", "type": "text"}]}]
    data = post(port, "/api/sql", h, {"app": "web", "query": "SELECT count(*) AS n, secreto-en-la-consulta AS email"})[1]
    assert data["columns"] == ["n", "email"] and data["rows"] == [["42", ""]] and not data["error"]
    sent = (tmp_path / "live.json.sql").read_text()
    assert "secreto-en-la-consulta" not in sent and "--query" in sent, "la consulta va por stdin"
    assert "default_transaction_read_only = on" in sent and "_ro" in sent, "corre como el rol de solo lectura"
    assert post(port, "/api/sql", h, {"app": "web", "query": "boom"})[1]["error"].startswith("syntax error")
    assert "consulta" in post(port, "/api/sql", h, {"app": "web", "query": "  "})[1]["error"]


# ---- Auditoría de UX: volver a conectarse a una acción en curso ----

def test_current_job_lets_a_reloaded_page_reconnect(panel):
    port, token = panel
    h = session(port, token)
    assert json.loads(get(port, "/api/jobs/current", h)[2]) == {}
    status, job = post(port, "/api/jobs", h, {"action": "stop", "app": "web"})
    assert status == 201
    events(port, h, job["id"], until="prompt")
    cur = json.loads(get(port, "/api/jobs/current", h)[2])
    assert cur == {"id": job["id"], "command": "andamio app stop web", "action": "stop", "state": "password"}
    # La página recargada vuelve a leer todo lo que salió, desde el principio.
    assert events(port, h, job["id"], until="prompt")[0] == ("line", "$ andamio app stop web")
    post(port, f"/api/jobs/{job['id']}/cancel", h, {})
    events(port, h, job["id"])
    assert json.loads(get(port, "/api/jobs/current", h)[2]) == {}


def test_settings_say_when_the_copy_cannot_update(panel, fake_copy):
    port, token = panel
    auth = login(port, token)
    cfg = fake_copy / "ansible/group_vars/all.yml"
    base = cfg.read_text()
    cfg.write_text(base + 'andamio_upstream: "@fuente"\n')
    assert json.loads(get(port, "/api/settings", auth)[2])["updatable"] is False, "la fuente de andamio no se actualiza con update"
    cfg.write_text(base + 'andamio_upstream: "https://github.com/ejemplo/andamio.git"\n')
    assert json.loads(get(port, "/api/settings", auth)[2])["updatable"] is True



# ---- Reiniciar, desplegar ahora, editar tareas, corridas, worker, disponibilidad y certificados ----

@pytest.mark.parametrize("body, command, sudo", [
    ({"action": "restart", "app": "web"}, "andamio app restart web", False),
    ({"action": "deploy", "app": "web"}, "andamio app deploy web", False),
])
def test_restart_and_deploy_need_no_password(panel, body, command, sudo):
    port, token = panel
    h = session(port, token)
    status, job = post(port, "/api/jobs", h, body)
    assert status == 201 and job["command"] == command
    assert not any(k == "prompt" for k, _ in events(port, h, job["id"]))


def test_cron_edit_is_checked_and_runs_the_cli(panel, fake_copy):
    yml = fake_copy / "apps/web/app.yml"
    yml.write_text(yml.read_text() + "cron:\n  - name: limpiar\n    schedule: \"@daily\"\n    command: \"python l.py\"\n")
    port, token = panel
    h = session(port, token)
    assert "no tiene una tarea" in post(port, "/api/jobs", h, {"action": "cron-edit", "app": "web", "task": "otra", "schedule": "@daily"})[1]["error"]
    assert "Nada que cambiar" in post(port, "/api/jobs", h, {"action": "cron-edit", "app": "web", "task": "limpiar"})[1]["error"]
    assert "minuto" in post(port, "/api/jobs", h, {"action": "cron-edit", "app": "web", "task": "limpiar", "schedule": "61 * * * *"})[1]["error"]
    status, job = post(port, "/api/jobs", h, {"action": "cron-edit", "app": "web", "task": "limpiar", "schedule": "0 4 * * *"})
    assert status == 201 and job["command"] == "andamio app cron edit web limpiar --schedule '0 4 * * *'"
    post(port, f"/api/jobs/{job['id']}/cancel", h, {}) if events(port, h, job["id"], until="prompt")[-1][0] == "prompt" else None


def test_cron_runs_come_with_their_output(panel):
    port, token = panel
    auth = login(port, token)
    runs = json.loads(get(port, "/api/cron-runs?app=web&task=limpiar", auth)[2])["runs"]
    assert runs[0] == {"rc": 0, "start": 1700000000, "secs": 3, "output": "hola\nlisto"}
    assert runs[1]["rc"] == 2 and runs[1]["output"] == "boom"
    assert get(port, "/api/cron-runs?app=web&task=..%2Fx", auth)[0] == 400


def test_worker_logs(panel, tmp_path):
    port, token = panel
    auth = login(port, token)
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", "/api/logs/web?service=worker", headers={"Host": f"127.0.0.1:{port}", "Cookie": auth["Cookie"]})
    c.getresponse().read()
    c.close()
    assert "com.docker.compose.service=worker" in (tmp_path / "live.json.logs").read_text()


def test_availability_per_app(panel):
    port, token = panel
    data = json.loads(get(port, "/api/availability", login(port, token))[2])
    assert data["apps"]["web"] == {"24h": 99.5, "7d": 97.25}


def test_cert_check_reports_why_it_fails(andamio):
    c = andamio.cert_check("no-existe.invalid", tries=1)
    assert c["ok"] is False and c["host"] == "no-existe.invalid" and c["error"]



# ---- Velocidad y "entender qué pasó" ----

def test_app_page_does_not_wait_for_github(panel):
    port, token = panel
    auth = login(port, token)
    data = json.loads(get(port, "/api/app/web", auth)[2])
    assert "deploys" not in data["app"], "los deploys van aparte: la página no espera a GitHub"
    assert json.loads(get(port, "/api/deploys?app=web", auth)[2]) == {"deploys": []}
    assert get(port, "/api/deploys?app=..%2Fx", auth)[0] == 400


def test_ci_failure_is_checked(panel):
    port, token = panel
    auth = login(port, token)
    assert get(port, "/api/ci-failure?app=web&run=abc", auth)[0] == 400
    assert get(port, "/api/ci-failure?app=nada&run=1", auth)[0] == 400
    assert "error" in json.loads(get(port, "/api/ci-failure?app=web&run=1", auth)[2]), "sin GitHub: un error, no una caída"


def test_timeline_of_an_app(panel):
    port, token = panel
    data = json.loads(get(port, "/api/timeline?app=web", login(port, token))[2])
    assert data["hours"] == [[3600, 1.0], [7200, None]] and data["outages"][0]["mins"] == 10
    assert "error" in json.loads(get(port, "/api/timeline?app=..%2Fx", login(port, token))[2])


def test_services_of_an_app(panel):
    port, token = panel
    auth = login(port, token)
    data = json.loads(get(port, "/api/services?app=web", auth)[2])
    assert [s["kind"] for s in data["services"]] == ["app", "postgres"] and "services_of" not in data
    assert "error" in json.loads(get(port, "/api/services?app=..%2Fx", auth)[2])


def test_sparks_of_every_app_in_one_query(panel):
    port, token = panel
    data = json.loads(get(port, "/api/sparks", login(port, token))[2])
    assert data["sparks"] == {"web": [[0, 1.5], [1800, 2.0]]} and data["step"] == 1800


def test_sudo_minutes_is_a_setting_of_this_machine(panel, env):
    """Cuánto se recuerda la contraseña de sudo: solo las opciones del panel, en ~/.config/andamio."""
    port, token = panel
    h = session(port, token)
    data = json.loads(get(port, "/api/settings", login(port, token))[2])
    assert data["sudo_minutes"] == 15 and data["sudo_choices"] == [15, 60, 240, 480] and data["sudo_remembered"] is False
    assert post(port, "/api/sudo", h, {"minutes": 240})[0] == 200
    saved = Path(env["XDG_CONFIG_HOME"]) / "andamio" / "ajustes.json"
    assert json.loads(saved.read_text())["sudo_minutes"] == 240
    assert json.loads(get(port, "/api/settings", login(port, token))[2])["sudo_minutes"] == 240
    assert post(port, "/api/sudo", h, {"minutes": 99999})[0] == 400
    assert post(port, "/api/sudo", h, {"forget": True})[1] == {"ok": True}


def test_suggestions_from_seven_days(panel):
    """web tiene 256m y llegó a 240 MiB (más del 85 %): sugiere subirla. Su CPU (0.5) casi no se usa: bajarla."""
    port, token = panel
    data = json.loads(get(port, "/api/suggest?app=web", login(port, token))[2])
    assert data["days"] == 7.0
    assert data["mem"]["why"] == "up" and data["mem"]["suggest"] == "384m"
    assert data["cpu"]["why"] == "down" and data["cpu"]["suggest"] == "0.25"


def test_env_check_without_github_says_why(panel):
    port, token = panel
    auth = login(port, token)
    assert "No pude clonar" in json.loads(get(port, "/api/env-check?app=web", auth)[2])["error"]
    assert "error" in json.loads(get(port, "/api/env-check?app=nada", auth)[2])
