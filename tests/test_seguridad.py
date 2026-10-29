"""`andamio seguridad`: las piezas que deciden sin tocar un servidor.

- probe_port: distinguir "el servidor rechaza" (el puerto llega) de "nadie responde" (firewall).
- offers_password: leer del rechazo de ssh si el servidor todavía ofrece contraseña.
- ssh_host_name / free_alias: una copia nueva no hereda el alias SSH de otro servidor.
- la configuración mínima de seguridad: init la completa sin volver a preguntar, y los
  comandos de la plataforma explican qué falta.
"""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_probe_port_open_and_closed(andamio):
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen()
        assert andamio.probe_port("127.0.0.1", srv.getsockname()[1], timeout=2) == "open"
    with socket.socket() as tmp:   # un puerto que nadie escucha: el sistema lo rechaza al instante
        tmp.bind(("127.0.0.1", 0))
        free = tmp.getsockname()[1]
    assert andamio.probe_port("127.0.0.1", free, timeout=2) == "closed"


@pytest.mark.parametrize("stderr, expected", [
    ("root@203.0.113.10: Permission denied (publickey).", False),
    ("newtest@203.0.113.10: Permission denied (publickey,password).", True),
    ("x@203.0.113.10: Permission denied (publickey,keyboard-interactive).", True),
    ("ssh: connect to host 203.0.113.10 port 2222: Connection timed out", None),
    ("Host key verification failed.", None),
])
def test_offers_password(andamio, stderr, expected):
    assert andamio.offers_password(stderr) is expected


SSH_CONFIG = """\
Host otro-vps
    HostName 203.0.113.10
    User andamio
    Port 2222

Host andamio
    HostName 198.51.100.7
    User viejo
"""


def test_ssh_host_name(andamio):
    assert andamio.ssh_host_name(SSH_CONFIG, "otro-vps") == "203.0.113.10"
    assert andamio.ssh_host_name(SSH_CONFIG, "andamio") == "198.51.100.7"
    assert andamio.ssh_host_name(SSH_CONFIG, "andamio-2") is None
    assert andamio.ssh_host_name("Host sinhost\n    User x\n", "sinhost") == ""


def test_free_alias_skips_other_servers(andamio):
    assert andamio.free_alias("", "192.0.2.1") == "andamio"
    # "andamio" ya es otro servidor (una prueba vieja): la copia nueva usa otro alias
    assert andamio.free_alias(SSH_CONFIG, "192.0.2.1") == "andamio-2"
    # el mismo servidor de siempre: se reusa
    assert andamio.free_alias(SSH_CONFIG, "198.51.100.7") == "andamio"


PARTIAL = """\
# Configuración de este servidor (andamio seguridad: solo el blindaje).
andamio_user: geo
andamio_uid: 1001
andamio_ssh_port: 24567
andamio_ssh_host_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample"
andamio_server_ip: 192.0.2.1
"""


def test_init_completes_the_security_config(andamio, tmp_path, monkeypatch):
    cfg = tmp_path / "ansible" / "group_vars" / "all.yml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(PARTIAL)
    monkeypatch.setattr(andamio, "ROOT", tmp_path)
    monkeypatch.setattr(andamio, "CONFIG", cfg)
    monkeypatch.setattr(andamio, "SOPS_CONFIG", tmp_path / ".sops.yaml")
    monkeypatch.setattr(andamio, "forge_out", lambda what: {"name": "GitHub", "registry": "ghcr.io"}[what])
    assert andamio.is_partial_config()

    import yaml
    pre = yaml.safe_load(cfg.read_text())
    a = {"ip": "192.0.2.1", "user": "geo", "port": "24567", "domain": "ejemplo.com", "tls": "http",
         "email": "tu@ejemplo.com", "owner": "tu-usuario", "repo": "tu-usuario/tu-andamio", "monitoring": "auto"}
    andamio.write_config(a, "age1ejemplo", pre)
    full = yaml.safe_load(cfg.read_text())
    assert not andamio.is_partial_config()
    assert full["andamio_ssh_host_key"] == pre["andamio_ssh_host_key"], "la huella verificada no se pierde"
    assert (full["andamio_user"], full["andamio_ssh_port"], full["andamio_server_ip"]) == ("geo", 24567, "192.0.2.1")
    assert full["andamio_domain"] == "ejemplo.com" and full["andamio_repo"].endswith("tu-usuario/tu-andamio.git")


def test_platform_commands_explain_a_security_only_copy(fake_copy, env):
    (fake_copy / "ansible" / "group_vars" / "all.yml").write_text(PARTIAL)
    r = subprocess.run([str(fake_copy / "bin" / "andamio"), "estado"], cwd=fake_copy, env=env,
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "andamio init" in r.stdout + r.stderr and "andamio seguridad" in r.stdout + r.stderr


def test_security_check_skips_the_platform(andamio):
    """En modo seguridad, el chequeo del servidor no revisa backups, certificados ni la VPN."""
    script = (andamio.ROOT / "scripts" / "security-check.sh").read_text()
    guarded = script.split('if [ "${SOLO:-}" != seguridad ]; then', 1)[1].split("fi   # fin de lo de la plataforma", 1)[0]
    for section in ("# --- Backups ---", "# --- Certificados", "# --- Contenedores ---", "# --- VPN ---"):
        assert section in guarded
    assert "# --- SSH ---" not in guarded and "fail2ban" not in guarded


def test_rename_operator_updates_config_and_alias(andamio, tmp_path, monkeypatch):
    """Si eligió el mismo usuario que el del proveedor: otro nombre, en la configuración y en su alias."""
    cfg = tmp_path / "all.yml"
    cfg.write_text(PARTIAL.replace("andamio_user: geo", "andamio_user: newtest"))
    ssh = tmp_path / "ssh"
    ssh.mkdir()
    (ssh / "config").write_text(SSH_CONFIG + "\nHost andamio-2\n    HostName 192.0.2.1\n    User newtest\n    Port 24567\n")
    monkeypatch.setattr(andamio, "CONFIG", cfg)
    monkeypatch.setattr(andamio, "SSH_DIR", ssh)
    andamio.rename_operator("andamio-2", "newtest", "geo")
    import yaml
    assert yaml.safe_load(cfg.read_text())["andamio_user"] == "geo"
    text = (ssh / "config").read_text()
    assert "Host andamio-2\n    HostName 192.0.2.1\n    User geo\n" in text
    assert "User viejo" in text and "User andamio" in text, "los otros alias no se tocan"


def test_suggest_alias_says_which_server(andamio):
    cfg = {"andamio_server_ip": "192.0.2.1", "andamio_provider": "azure"}
    assert andamio.suggest_alias("", cfg) == "andamio"
    # "andamio" es otro servidor: por el proveedor, o por el dominio si lo hay
    assert andamio.suggest_alias(SSH_CONFIG, cfg) == "andamio-azure"
    assert andamio.suggest_alias(SSH_CONFIG, {**cfg, "andamio_domain": "blog.ejemplo.com"}) == "blog"
    assert andamio.suggest_alias(SSH_CONFIG, {"andamio_server_ip": "192.0.2.1"}) == "andamio-2"


@pytest.fixture
def git_identity(monkeypatch):
    for k, v in (("GIT_AUTHOR_NAME", "test"), ("GIT_AUTHOR_EMAIL", "test@example.com"),
                 ("GIT_COMMITTER_NAME", "test"), ("GIT_COMMITTER_EMAIL", "test@example.com")):
        monkeypatch.setenv(k, v)


def test_setup_security_only_makes_a_local_copy(andamio, make_repo, tmp_path, monkeypatch, git_identity):
    """Solo blindar: una copia local, sin origin (no es el template ni sube nada) y con su versión anotada."""
    public = make_repo("andamio", {"bin/andamio": "#!/bin/sh\n", "README.md": "andamio\n"})
    target = tmp_path / "mi-andamio"
    monkeypatch.setattr(andamio, "ROOT", public)
    monkeypatch.setattr(andamio, "ask", lambda *a, **k: str(target))
    monkeypatch.setattr(andamio, "ask_yes", lambda *a, **k: False)   # sin seguir a seguridad
    andamio.setup_local_copy([])
    assert (target / "README.md").exists()
    assert subprocess.run(["git", "-C", str(target), "remote"], capture_output=True, text=True).stdout.strip() == ""
    head = subprocess.run(["git", "-C", str(public), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert f"commit {head}" in (target / ".andamio" / "upstream").read_text()


def test_setup_connects_a_local_copy(andamio, make_repo, tmp_path, monkeypatch, git_identity):
    """La copia local de seguridad, con su configuración, sube entera a un repo privado nuevo."""
    copy = make_repo("mi-andamio", {"README.md": "andamio\n"})
    (copy / "ansible" / "group_vars").mkdir(parents=True)
    (copy / "ansible" / "group_vars" / "all.yml").write_text(PARTIAL)
    bare = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    created = []

    def forge(*a):
        created.append(a)
        return subprocess.CompletedProcess(a, 1 if a[0] == "repo-exists" else 0, "", "")
    monkeypatch.setattr(andamio, "ROOT", copy)
    monkeypatch.setattr(andamio, "forge", forge)
    monkeypatch.setattr(andamio, "forge_out", lambda what, *a: str(bare) if what == "clone-url" else
                        {"name": "GitHub", "whoami": "yo"}[what])
    monkeypatch.setattr(andamio, "ask", lambda q, default=None, check=None, **k: default)
    monkeypatch.setattr(andamio, "interactive", lambda cmd, **k: subprocess.run(cmd).returncode)
    andamio.connect_local_copy()
    assert ("repo-create-empty", "yo/mi-andamio") in created
    files = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "main"],
                           capture_output=True, text=True).stdout.split()
    assert "ansible/group_vars/all.yml" in files, "la configuración de seguridad sube con la copia"
    assert subprocess.run(["git", "-C", str(copy), "remote"],
                          capture_output=True, text=True).stdout.strip() == "origin"


def test_setup_again_reuses_the_local_copy(andamio, make_repo, tmp_path, monkeypatch, git_identity):
    """Volver a correr setup con la carpeta que ya creó: la reusa (no se queda diciendo "ya existe")."""
    existing = make_repo("mi-andamio", {"bin/andamio": "#!/bin/sh\n", "ansible/site.yml": "[]\n"})
    (existing / "ansible" / "group_vars").mkdir()
    (existing / "ansible" / "group_vars" / "all.yml").write_text(PARTIAL)
    monkeypatch.setattr(andamio, "ROOT", make_repo("andamio", {"README.md": "x\n"}))
    monkeypatch.setattr(andamio, "ask", lambda q, default=None, check=None, **k: (check(str(existing)), str(existing))[1])
    monkeypatch.setattr(andamio, "ask_yes", lambda *a, **k: False)
    andamio.setup_local_copy([])
    assert (existing / "ansible" / "group_vars" / "all.yml").read_text() == PARTIAL, "lo que ya tenía se queda"


def test_harden_fingerprint(andamio, tmp_path, monkeypatch):
    """El blindaje se salta solo si no cambió nada de lo que lo decide; agregar un stack no cuenta."""
    (tmp_path / "ansible/roles/ssh/tasks").mkdir(parents=True)
    (tmp_path / "ansible/site.yml").write_text("- hosts: servers\n")
    role = tmp_path / "ansible/roles/ssh/tasks/main.yml"
    role.write_text("- copy: {src: \"{{ playbook_dir }}/../host/ssh/x.conf\", dest: /etc/x}\n"
                    "- debug: {msg: \"{{ andamio_ssh_port }}\"}\n")
    for d in ("ssh", "systemd"):
        (tmp_path / "host" / d).mkdir(parents=True)
    (tmp_path / "host/ssh/x.conf").write_text("Port {{ andamio_ssh_port }}\n")
    (tmp_path / "host/systemd/y.service").write_text("[Unit]\n")
    monkeypatch.setattr(andamio, "ROOT", tmp_path)
    cfg = {"andamio_ssh_port": 5022, "andamio_stacks": ["stacks/proxy"]}
    base = andamio.harden_fingerprint(cfg)
    assert andamio.harden_fingerprint(dict(cfg, andamio_stacks=["stacks/proxy", "stacks/mi-stack"])) == base
    (tmp_path / "host/systemd/y.service").write_text("[Unit]\nDescription=otra\n")   # host/ que el blindaje no usa
    assert andamio.harden_fingerprint(cfg) == base
    assert andamio.harden_fingerprint(dict(cfg, andamio_ssh_port=6022)) != base
    (tmp_path / "host/ssh/x.conf").write_text("Port {{ andamio_ssh_port }}\nMaxAuthTries 3\n")
    assert andamio.harden_fingerprint(cfg) != base


@pytest.mark.parametrize("check, level, says", [
    (("ok", "2027-10-29 05:00:00 UTC"), "OK", "en 365 días"),
    (("ok", "2026-11-08 05:00:00 UTC"), "WARN", "en 10 días"),
    (("ok", ""), "OK", "sin vencimiento"),
    (("invalid", "401"), "FAIL", "ya no sirve"),
    (("nologin", ""), "FAIL", "no tiene login"),
    (("error", "timeout"), "WARN", "No pude revisar"),
])
def test_registry_rows_warn_before_the_token_expires(andamio, monkeypatch, check, level, says):
    """andamio estado avisa 30 días antes de que venza el token con el que bajan las imágenes."""
    monkeypatch.setattr(andamio, "registry_check", lambda alias: check)
    monkeypatch.setattr(andamio, "registry", lambda cfg: ("ghcr.io", "GHCR"))
    [row] = andamio.registry_rows({}, "srv", today=andamio.datetime.date(2026, 10, 29))
    assert row[0] == level and says in row[2], row
    renew = level == "FAIL" or (level == "WARN" and check[0] == "ok")
    assert row[3] == ("andamio registro renovar" if renew else "")


def test_registry_check_script_never_needs_the_network_without_login(tmp_path):
    """El script que revisa el token en el servidor: sin login (o con las claves en otro almacén)
    lo dice sin ir a GitHub."""
    script = subprocess.run([str(ROOT_DIR / "bin" / "forge"), "registry-check-script"],
                            capture_output=True, text=True, check=True).stdout
    home = tmp_path / "home"
    (home / ".docker").mkdir(parents=True)
    run = lambda: subprocess.run(["python3", "-"], input=script, capture_output=True, text=True,
                                 env={"HOME": str(home), "PATH": "/usr/bin:/bin"}).stdout.strip()
    assert run() == "nologin"   # sin config.json
    (home / ".docker/config.json").write_text('{"auths": {"docker.io": {"auth": "eDp5"}}}')
    assert run() == "nologin"   # login en otro registro, no en ghcr.io
    (home / ".docker/config.json").write_text('{"credsStore": "desktop"}')
    assert run() == "unknown"
