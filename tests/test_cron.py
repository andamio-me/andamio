"""Tareas programadas: el horario cron traducido a systemd, la edición de app.yml y la CLI."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess

import pytest

from conftest import APP_YML, ROOT, git

spec = importlib.util.spec_from_file_location("andamio_cron", ROOT / "ansible" / "filter_plugins" / "andamio_cron.py")
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)

CASES = [
    ("0 3 * * *", "*-*-* 03:00:00"),
    ("*/15 * * * *", "*-*-* *:00/15:00"),
    ("30 8 * * 1-5", "Mon..Fri *-*-* 08:30:00"),
    ("0 0 * * 0", "Sun *-*-* 00:00:00"),
    ("0 0 * * 7", "Sun *-*-* 00:00:00"),
    ("0 9 * * sat,sun", "Sun,Sat *-*-* 09:00:00"),
    ("0 12 1 * *", "*-*-01 12:00:00"),
    ("0 6 1 jan *", "*-01-01 06:00:00"),
    ("0,30 9-17 * * *", "*-*-* 09,10,11,12,13,14,15,16,17:00,30:00"),
    ("5 */2 * * *", "*-*-* 00/2:05:00"),
    ("0 10-20/5 * * *", "*-*-* 10,15,20:00:00"),
    ("0 0 */2 * *", "*-*-01/2 00:00:00"),
    ("@daily", "*-*-* 00:00:00"),
    ("@hourly", "*-*-* *:00:00"),
    ("@weekly", "Sun *-*-* 00:00:00"),
]


@pytest.mark.parametrize("expr, calendar", CASES)
def test_cron_to_systemd(expr, calendar):
    assert cron.cron_calendar(expr) == calendar


@pytest.mark.skipif(not shutil.which("systemd-analyze"), reason="sin systemd-analyze")
@pytest.mark.parametrize("expr, calendar", CASES)
def test_systemd_accepts_it(expr, calendar):
    """Lo que generamos, systemd lo entiende (con la zona horaria, como en el timer)."""
    r = subprocess.run(["systemd-analyze", "calendar", f"{calendar} America/Bogota"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("expr, error", [
    ("0 3 * *", "5 campos"),
    ("60 * * * *", "minuto"),
    ("0 24 * * *", "hora"),
    ("0 0 32 * *", "día del mes"),
    ("0 0 * 13 *", "mes"),
    ("0 0 * * 8", "día de la semana"),
    ("0 0 1 * 1", "no los dos"),
    ("*/0 * * * *", "paso"),
    ("5-1 * * * *", "al revés"),
    ("*,5 * * * *", "no se combina"),
    ("@reboot", "Atajo desconocido"),
    ("a b c d e", "fuera de rango"),
])
def test_invalid_schedules(expr, error):
    with pytest.raises(cron.CronError, match=error):
        cron.cron_calendar(expr)


# ---- app.yml ----

def test_cron_write_roundtrip(andamio):
    entries = [{"name": "limpiar", "schedule": "0 3 * * *", "command": 'python limpiar.py --dias "30"'}]
    text = andamio.cron_write(APP_YML, entries)
    assert andamio.cron_entries(text) == entries
    assert text.startswith(APP_YML), "el resto del archivo queda igual"
    assert andamio.cron_write(text, []) == APP_YML, "sin tareas, el bloque desaparece"
    # Con algo después del bloque (editado a mano): no se pierde.
    moved = text + "stopped: true\n"
    again = andamio.cron_write(moved, entries + [{"name": "b", "schedule": "@daily", "command": "x"}])
    assert "stopped: true" in again and len(andamio.cron_entries(again)) == 2


@pytest.mark.parametrize("command, taken, name", [
    ("python limpiar.py", [], "limpiar"),
    ("node scripts/sync.js --full", [], "sync"),
    ("python manage.py clearsessions", [], "clearsessions"),
    ("python limpiar.py", ["limpiar"], "limpiar-2"),
    ("python 2fa_reset.py", [], "tarea"),
])
def test_default_name(andamio, command, taken, name):
    assert andamio.cron_default_name(command, taken) == name


# ---- CLI ----

def cron_cli(copy, env, *args, stdin=None):
    return subprocess.run([str(copy / "bin" / "andamio"), "_cron", *args], cwd=copy, env=env, input=stdin,
                          capture_output=True, text=True, timeout=60)


def test_add_asks_the_timezone_once(fake_copy, env):
    yml = fake_copy / "apps/web/app.yml"
    r = cron_cli(fake_copy, env, "add", str(yml), "0 3 * * *", "python limpiar.py", "", stdin="Europe/Madrid\n")
    assert r.returncode == 0, r.stderr
    assert "limpiar" in r.stdout and "Europe/Madrid" in r.stdout
    assert 'andamio_timezone: "Europe/Madrid"' in (fake_copy / "ansible/group_vars/all.yml").read_text()
    # La segunda ya no pregunta (sin entrada: si preguntara, fallaría).
    r = cron_cli(fake_copy, env, "add", str(yml), "@hourly", "python sync.py", "sync")
    assert r.returncode == 0, r.stderr
    assert [e["name"] for e in __import__("yaml").safe_load(yml.read_text())["cron"]] == ["limpiar", "sync"]


def test_add_rejects_bad_timezone(fake_copy, env):
    yml = fake_copy / "apps/web/app.yml"
    r = cron_cli(fake_copy, env, "add", str(yml), "0 3 * * *", "x", "", stdin="Marte/Olympus\n")
    assert r.returncode != 0 and "No conozco la zona" in r.stdout
    assert yml.read_text() == APP_YML


@pytest.mark.parametrize("schedule, command, name, error", [
    ("0 3 * *", "x", "", "5 campos"),
    ("0 3 * * *", "", "", "una sola línea"),
    ("0 3 * * *", "a\nb", "", "una sola línea"),
    ("0 3 * * *", "x", "Mala", "Nombre inválido"),
])
def test_add_rejections(fake_copy, env, schedule, command, name, error):
    yml = fake_copy / "apps/web/app.yml"
    r = cron_cli(fake_copy, env, "add", str(yml), schedule, command, name)
    assert r.returncode != 0 and error in r.stderr
    assert yml.read_text() == APP_YML


def test_rm_and_duplicates(fake_copy, env):
    yml = fake_copy / "apps/web/app.yml"
    (fake_copy / "ansible/group_vars/all.yml").open("a").write("andamio_timezone: UTC\n")
    assert cron_cli(fake_copy, env, "add", str(yml), "@daily", "python a.py", "").returncode == 0
    r = cron_cli(fake_copy, env, "add", str(yml), "@daily", "python b.py", "a")
    assert r.returncode != 0 and "Ya hay una tarea a" in r.stderr
    r = cron_cli(fake_copy, env, "rm", str(yml), "nada")
    assert r.returncode != 0 and "Tareas: a" in r.stderr
    assert cron_cli(fake_copy, env, "rm", str(yml), "a").returncode == 0
    assert yml.read_text() == APP_YML


def test_app_cron_cli_rejections(fake_copy, env):
    run = lambda *a: subprocess.run([str(fake_copy / "bin" / "andamio-app"), "app", "cron", *a], cwd=fake_copy,
                                    env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    start_new_session=True, timeout=60)
    r = run("run", "web", "nada")
    assert r.returncode != 0 and "no tiene una tarea nada" in r.stderr
    r = run("add", "web", "0 99 * * *", "python x.py")
    assert r.returncode != 0 and "hora" in r.stderr
    r = run("add", "web", "@daily", "python x.py", "--otra")
    assert r.returncode != 0 and "Opción desconocida" in r.stderr
    assert git(fake_copy, "status", "--porcelain") == ""


def test_edit_changes_schedule_or_command_only(fake_copy, env):
    yml = fake_copy / "apps/web/app.yml"
    (fake_copy / "ansible/group_vars/all.yml").open("a").write("andamio_timezone: UTC\n")
    assert cron_cli(fake_copy, env, "add", str(yml), "@daily", "python a.py", "a").returncode == 0
    r = cron_cli(fake_copy, env, "edit", str(yml), "a", "0 4 * * *", "")
    assert r.returncode == 0 and "@daily  →  0 4 * * *" in r.stdout
    r = cron_cli(fake_copy, env, "edit", str(yml), "a", "", "python b.py --todo")
    assert r.returncode == 0
    from conftest import load_andamio
    assert load_andamio().cron_entries(yml.read_text()) == [{"name": "a", "schedule": "0 4 * * *", "command": "python b.py --todo"}]
    assert "Nada que cambiar" in cron_cli(fake_copy, env, "edit", str(yml), "a", "0 4 * * *", "").stderr
    assert "No hay una tarea zz" in cron_cli(fake_copy, env, "edit", str(yml), "zz", "@daily", "").stderr
    assert "minuto" in cron_cli(fake_copy, env, "edit", str(yml), "a", "61 * * * *", "").stderr
