"""PostgreSQL y Redis compartidos (andamio servicios): sus valores por defecto, lo que se rechaza,
el .env que escribe Ansible para stacks/data y la acción del panel."""
from __future__ import annotations

import re
from pathlib import Path

import jinja2
import pytest
import yaml

from conftest import ROOT

DEFAULTS = yaml.safe_load((ROOT / "ansible/roles/andamio/defaults/main.yml").read_text())
COMPOSE = (ROOT / "stacks/data/compose.yaml").read_text()


def data_env(**over) -> dict[str, str]:
    """El .env de stacks/data como lo arma Ansible (andamio_data_env), en un servidor de 4 CPU."""
    env = jinja2.Environment()
    env.filters["bool"] = lambda v: str(v).strip().lower() in ("true", "1", "yes")   # el de Ansible
    # andamio_mariadb_needed lee apps/*/app.yml con lookups de Ansible: aquí, un valor fijo.
    vals = {**DEFAULTS, "andamio_mariadb_needed": False, **over, "ansible_facts": {"processor_vcpus": 4}}
    for k in ("andamio_postgres_mem_mb", "andamio_redis_mem_mb", "andamio_mariadb_mem_mb", "andamio_dragonfly_threads"):
        vals[k] = env.from_string(str(vals[k])).render(**vals).strip()
    text = env.from_string(DEFAULTS["andamio_data_env"]).render(**vals)
    return dict(line.split("=", 1) for line in text.splitlines() if line)


def test_cli_defaults_match_ansible_defaults(andamio):
    for svc, values in andamio.SERVICE_DEFAULTS.items():
        for k, v in values.items():
            assert str(DEFAULTS[f"andamio_{svc}_{k}"]) == v, f"{svc}.{k}"


def test_default_env_keeps_todays_values():
    """Sin cambiar nada, PostgreSQL y Redis quedan como estaban (y no se recrean)."""
    env = data_env()
    assert env == {"POSTGRES_CPUS": "1.5", "POSTGRES_MEM": "1024m", "POSTGRES_SHARED_BUFFERS": "256MB",
                   "POSTGRES_MAX_CONNECTIONS": "100", "POSTGRES_WORK_MEM": "4MB", "REDIS_CPUS": "0.5",
                   "REDIS_MAXMEMORY": "256mb", "REDIS_MEM": "384m", "REDIS_POLICY": "noeviction",
                   "COMPOSE_PROFILES": "redis", "DRAGONFLY_THREADS": "1", "DRAGONFLY_CACHE_MODE": "false",
                   "MARIADB_MEM": "512m", "MARIADB_BUFFER_POOL": "204M", "MARIADB_MAX_CONNECTIONS": "100",
                   "MARIADB_CPUS": "1.0"}


def test_env_follows_the_config_and_caps_cpus():
    env = data_env(andamio_postgres_mem="2g", andamio_postgres_cpus="8", andamio_redis_mem="512m")
    assert env["POSTGRES_MEM"] == "2048m" and env["POSTGRES_SHARED_BUFFERS"] == "512MB"
    assert env["POSTGRES_CPUS"] == "4", "nunca más CPU que las del servidor"
    assert env["REDIS_MAXMEMORY"] == "512mb" and env["REDIS_MEM"] == "768m"


def test_compose_reads_every_variable_with_a_fallback():
    used = set(re.findall(r"\$\{([A-Z_]+):-[^}]+\}", COMPOSE))
    assert set(data_env()) - {"POSTGRES_CPUS", "COMPOSE_PROFILES"} <= used
    assert "POSTGRES_CPUS" in COMPOSE


def test_mariadb_runs_only_if_an_app_uses_it():
    assert data_env()["COMPOSE_PROFILES"] == "redis"
    assert data_env(andamio_mariadb_needed=True)["COMPOSE_PROFILES"] == "redis,mariadb"
    assert data_env(andamio_mariadb_needed=True, andamio_redis_engine="valkey")["COMPOSE_PROFILES"] == "valkey,mariadb"
    env = data_env(andamio_mariadb_mem="1g", andamio_mariadb_cpus="8")
    assert env["MARIADB_MEM"] == "1024m" and env["MARIADB_BUFFER_POOL"] == "409M" and env["MARIADB_CPUS"] == "4"


def test_mariadb_service_is_closed_and_off_by_default():
    c = yaml.safe_load(COMPOSE)
    m = c["services"]["mariadb"]
    assert m["profiles"] == ["mariadb"] and m["container_name"] == "mariadb"
    assert "ports" not in m and m["networks"] == ["data"]
    assert "--local-infile=0" in m["command"] and "--skip-name-resolve" in m["command"]
    assert m["environment"]["MARIADB_ROOT_PASSWORD"] == "${MARIADB_ROOT_PASSWORD}"
    assert "mariadbdata" in c["volumes"]


@pytest.mark.parametrize("apps, expected", [
    ({"web": "name: web\nmysql: true\n"}, True),
    ({"web": "name: web\nmysql:   true\n", "api": "name: api\ndb: true\n"}, True),
    ({"web": "name: web\nmysql: false\n"}, False),
    ({"web": "name: web\n# mysql: true (comentado)\n"}, False),
    ({}, False),
])
def test_mariadb_needed_reads_the_apps(tmp_path, apps, expected):
    """La expresión real de Ansible, con su comando real: ¿alguna app usa MariaDB? (Con fileglob
    daba siempre vacío: no acepta comodines en carpetas, y MariaDB se habría apagado sola.)"""
    import subprocess
    (tmp_path / "ansible").mkdir()
    for name, text in apps.items():
        (tmp_path / "apps" / name).mkdir(parents=True)
        (tmp_path / "apps" / name / "app.yml").write_text(text)
    env = jinja2.Environment()
    env.globals["lookup"] = lambda kind, cmd: subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    out = env.from_string(DEFAULTS["andamio_mariadb_needed"]).render(playbook_dir=str(tmp_path / "ansible"))
    assert out.strip() == str(expected)


def test_dragonfly_threads_follow_memory_and_cpu():
    assert data_env(andamio_redis_engine="dragonfly")["COMPOSE_PROFILES"] == "dragonfly"
    assert data_env(andamio_redis_mem="1g", andamio_redis_cpus="2")["DRAGONFLY_THREADS"] == "2", "no más hilos que CPU"
    assert data_env(andamio_redis_mem="1g", andamio_redis_cpus="4")["DRAGONFLY_THREADS"] == "4", "256 MB por hilo"
    assert data_env(andamio_redis_mem="512m", andamio_redis_cpus="4")["DRAGONFLY_THREADS"] == "2"
    assert data_env(andamio_redis_policy="allkeys-lru")["DRAGONFLY_CACHE_MODE"] == "true"


def test_the_three_engines_are_redis_for_the_apps():
    """Uno a la vez (profiles), siempre llamado redis (REDIS_URL no cambia), cada uno con su volumen."""
    c = yaml.safe_load(COMPOSE)
    for name in ("redis", "valkey", "dragonfly"):
        svc = c["services"][name]
        assert svc["profiles"] == [name] and svc["container_name"] == "redis"
        assert any(v.startswith(f"{name}data:") for v in svc["volumes"])
        assert "--aclfile" in svc["command"]
        assert f"{name}data" in c["volumes"]
    df = c["services"]["dragonfly"]
    # Su imagen tiene /etc/redis cerrado a su usuario; y sin archivo de usuarios, que igual pida clave.
    assert "./redis-acl:/acl:ro" in df["volumes"] and "--aclfile /acl/users.acl" in df["command"]
    assert df["environment"]["DFLY_requirepass"] == "${REDIS_PASSWORD}"
    assert "allow-undeclared-keys" in df["command"], "BullMQ"


SERVER = {"cpus": 4, "mem_total": 8 * 1024 ** 3}


def new_config(andamio, svc, **values):
    cfg = {k: dict(v) for k, v in andamio.SERVICE_DEFAULTS.items()}
    cfg[svc].update(values)
    return cfg


@pytest.mark.parametrize("svc, values, error", [
    ("postgres", {"mem": "128m"}, "desde 256m"),
    ("postgres", {"mem": "2x"}, "Memoria de PostgreSQL inválida"),
    ("redis", {"mem": "16m"}, "desde 32m"),
    ("postgres", {"cpus": "0"}, "CPU de PostgreSQL inválida"),
    ("redis", {"cpus": "6"}, "el servidor tiene 4 CPU"),
    ("postgres", {"max_connections": "5"}, "entre 20 y 1000"),
    ("postgres", {"work_mem": "4GB"}, "Memoria por consulta inválida"),
    ("redis", {"policy": "borrar-todo"}, "Política inválida"),
    ("postgres", {"mem": "6g"}, "70 %"),
    ("redis", {"engine": "keydb"}, "Motor inválido"),
    ("redis", {"engine": "dragonfly", "mem": "128m"}, "al menos 256m"),
    ("redis", {"engine": "dragonfly", "policy": "volatile-ttl"}, "Dragonfly no tiene volatile-ttl"),
])
def test_rejected_configs(andamio, svc, values, error):
    assert error in andamio.services_check(svc, new_config(andamio, svc, **values), SERVER)


def test_good_config_passes(andamio):
    assert andamio.services_check("postgres", new_config(andamio, "postgres", mem="2g", cpus="2", work_mem="16MB"), SERVER) == ""
    assert andamio.services_check("redis", new_config(andamio, "redis", mem="1g", policy="allkeys-lru"), SERVER) == ""
    assert andamio.services_check("redis", new_config(andamio, "redis", engine="valkey"), SERVER) == ""
    assert andamio.services_check("redis", new_config(andamio, "redis", engine="dragonfly", policy="allkeys-lfu"), SERVER) == ""


def test_max_connections_cannot_go_under_an_app_limit(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    f = fake_copy / "apps/web/app.yml"
    f.write_text(f.read_text() + "db: true\ndb_connections: 40\n")
    assert "al menos 45" in andamio.services_check("postgres", new_config(andamio, "postgres", max_connections="30"), SERVER)


def test_panel_action_builds_the_command(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_server_action({"action": "services", "service": "postgres", "set": {"mem": "2g", "max_connections": "150"}})
    assert plan["argv"] == ["servicios", "postgres", "--mem", "2g", "--max-connections", "150"] and plan["sudo"]
    assert "inválido" in andamio.ui_server_action({"action": "services", "service": "redis", "set": {"max_connections": "1"}})
    assert "inválido" in andamio.ui_server_action({"action": "services", "service": "postgres", "set": {"mem": "1g; rm"}})
    assert "Servicio inválido" in andamio.ui_server_action({"action": "services", "service": "mysql", "set": {}})
    plan = andamio.ui_server_action({"action": "services", "service": "redis", "set": {"engine": "valkey"}})
    assert plan["argv"] == ["servicios", "redis", "--engine", "valkey"]


def test_app_set_db_limits_in_the_panel(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    plan = andamio.ui_action_argv({"action": "set", "app": "web", "set": {"db_connections": "20", "db_timeout": "30s"}})
    assert plan["argv"] == ["app", "set", "web", "--db-connections", "20", "--db-timeout", "30s"]
    assert "Valor inválido" in andamio.ui_action_argv({"action": "set", "app": "web", "set": {"db_timeout": "30 s"}})


def test_servicios_yml_and_stack_env_exist():
    play = yaml.safe_load((ROOT / "ansible/servicios.yml").read_text())
    names = [t.get("ansible.builtin.include_role", {}).get("tasks_from") for t in play[0]["tasks"]]
    assert names == ["repo.yml", "services.yml"], "las tareas van en el rol: ahí se ven sus valores por defecto"
    tasks = yaml.safe_load((ROOT / "ansible/roles/andamio/tasks/services.yml").read_text())
    # El motor primero: si la copia falla, el .env no cambia.
    assert [t.get("ansible.builtin.include_tasks") for t in tasks[:2]] == ["redis-engine.yml", "stack-env.yml"]
    assert Path(ROOT / "ansible/roles/andamio/tasks/stack-env.yml").is_file()


# ---- kv-copy.py: la copia clave por clave al cambiar de motor ----

def kv_copy():
    import importlib.util
    spec = importlib.util.spec_from_file_location("kv_copy", ROOT / "scripts/kv-copy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeSource:
    """Un origen de mentira: responde lo que respondería Redis a cada lectura."""
    REPLIES = {
        ("GET", b"a:s"): b"\x01 binario",
        ("HGETALL", b"a:h"): [b"f", b"1", b"g", b"2"],
        ("LRANGE", b"a:l", 0, -1): [b"x", b"y"],
        ("SMEMBERS", b"a:set"): [b"m"],
        ("ZRANGE", b"a:z", 0, -1, "WITHSCORES"): [b"uno", b"1.5", b"dos", b"2"],
        ("XRANGE", b"a:st", "-", "+"): [[b"1-0", [b"k", b"v"]]],
        ("XINFO", "GROUPS", b"a:st"): [[b"name", b"g", b"consumers", 0, b"pending", 0, b"last-delivered-id", b"1-0"]],
    }

    def call(self, *args):
        return self.REPLIES[args]


@pytest.mark.parametrize("key, kind, expected", [
    (b"a:s", "string", [["SET", b"a:s", b"\x01 binario"]]),
    (b"a:h", "hash", [["HSET", b"a:h", b"f", b"1", b"g", b"2"]]),
    (b"a:l", "list", [["RPUSH", b"a:l", b"x", b"y"]]),
    (b"a:set", "set", [["SADD", b"a:set", b"m"]]),
    (b"a:z", "zset", [["ZADD", b"a:z", b"1.5", b"uno", b"2", b"dos"]]),
    (b"a:st", "stream", [["XADD", b"a:st", b"1-0", b"k", b"v"], ["XGROUP", "CREATE", b"a:st", b"g", b"1-0", "MKSTREAM"]]),
])
def test_kv_copy_recreates_each_type(key, kind, expected):
    assert kv_copy().dump(FakeSource(), key, kind) == expected


def test_kv_copy_parses_resp():
    import socket
    mod = kv_copy()
    a, b = socket.socketpair()
    conn = mod.Conn.__new__(mod.Conn)
    conn.sock, conn.buf = a, a.makefile("rb")
    b.sendall(b"*3\r\n$1\r\nx\r\n:5\r\n$-1\r\n" b"-NOPERM no\r\n")
    assert conn.read() == [b"x", 5, None]
    with pytest.raises(RuntimeError, match="NOPERM"):
        conn.read()


# ---- MariaDB: Servicios, detección y consola ----

def test_mariadb_service_checks(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    assert "MariaDB necesita" not in andamio.services_check("mariadb", new_config(andamio, "mariadb"), SERVER)
    assert "desde 256m" in andamio.services_check("mariadb", new_config(andamio, "mariadb", mem="128m"), SERVER)
    assert "entre 20 y 1000" in andamio.services_check("mariadb", new_config(andamio, "mariadb", max_connections="5"), SERVER)
    assert "el servidor tiene 4 CPU" in andamio.services_check("mariadb", new_config(andamio, "mariadb", cpus="8"), SERVER)
    # Sin apps con MariaDB, su memoria no cuenta para el 70 %; con una, sí.
    big = new_config(andamio, "postgres", mem="4g")
    big["mariadb"]["mem"] = "2g"
    assert andamio.services_check("postgres", big, SERVER) == ""
    f = fake_copy / "apps/web/app.yml"
    f.write_text(f.read_text() + "mysql: true\ndb_connections: 50\n")
    assert "MariaDB" in andamio.services_check("postgres", big, SERVER)
    assert "MariaDB necesita al menos 55" in andamio.services_check(
        "mariadb", new_config(andamio, "mariadb", max_connections="40"), SERVER)


def test_mariadb_panel_action(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    plan = andamio.ui_server_action({"action": "services", "service": "mariadb", "set": {"mem": "1g", "max_connections": "150"}})
    assert plan["argv"] == ["servicios", "mariadb", "--mem", "1g", "--max-connections", "150"]
    assert "inválido" in andamio.ui_server_action({"action": "services", "service": "mariadb", "set": {"engine": "valkey"}})


@pytest.mark.parametrize("files, expected", [
    ({".env.example": "DB_CONNECTION=mysql\nDB_HOST=127.0.0.1\n"}, True),             # Laravel
    ({".env.example": "DB_CONNECTION=pgsql\n"}, False),
    ({"package.json": '{"dependencies": {"mysql2": "^3.9.0"}}'}, True),
    ({"package.json": '{"dependencies": {"pg": "^8"}}'}, False),
    ({"prisma/schema.prisma": 'datasource db {\n  provider = "mysql"\n  url = env("DATABASE_URL")\n}'}, True),
    ({"prisma/schema.prisma": 'datasource db {\n  provider = "postgresql"\n}'}, False),
    ({"requirements.txt": "django\nmysqlclient==2.2\n"}, True),
    ({"go.mod": "module x\nrequire github.com/go-sql-driver/mysql v1.8.1\n"}, True),
    ({"composer.json": '{"require": {"laravel/framework": "^11"}}'}, False),   # Laravel solo no dice qué base
])
def test_detect_mysql(andamio, tmp_path, files, expected):
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    assert andamio.detect_mysql(tmp_path) is expected


def test_create_with_mysql_from_the_panel(andamio, fake_copy, monkeypatch):
    monkeypatch.setattr(andamio, "ROOT", fake_copy)
    monkeypatch.setattr(andamio, "CONFIG", fake_copy / "ansible/group_vars/all.yml")
    base = {"name": "nueva", "repo": "yo/nueva", "host": "nueva", "port": "3000", "mem": "256m", "access": "vpn",
            "mysql": True, "secrets": []}
    plan = andamio.ui_create_argv(base)
    assert "--mysql" in plan["argv"] and "--db" not in plan["argv"]


def test_mariadb_batch_output_is_parsed():
    """mariadb --batch: tabulaciones entre campos y, dentro de un dato, \\n \\t \\\\ escapados."""
    import subprocess
    import importlib.machinery
    import importlib.util
    ld = importlib.machinery.SourceFileLoader("am_sql", str(ROOT / "bin/andamio"))
    spec = importlib.util.spec_from_loader("am_sql", ld)
    m = importlib.util.module_from_spec(spec)
    ld.exec_module(m)
    out = "id\temail\tbio\n1\ta@b.co\tuno\\ndos\\ttab \\\\ barra\n2\tc@d.co\tNULL\n"
    r = m.sql_result_mysql(subprocess.CompletedProcess([], 0, out, ""))
    assert r["columns"] == ["id", "email", "bio"]
    assert r["rows"] == [["1", "a@b.co", "uno\ndos\ttab \\ barra"], ["2", "c@d.co", "NULL"]] and r["count"] == 2
    err = m.sql_result_mysql(subprocess.CompletedProcess([], 1, "", "ERROR 1142 (42000) at line 1: DELETE command denied to user\n"))
    assert err["error"] == "DELETE command denied to user"
