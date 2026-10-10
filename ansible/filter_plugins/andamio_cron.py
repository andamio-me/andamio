"""Horario cron (5 campos, el de siempre) → OnCalendar de systemd, para las tareas programadas
de las apps (`cron:` en app.yml). Lo usan Ansible (filtro cron_calendar) y bin/andamio (para
validar y mostrar la próxima vez antes de guardar). Un solo lugar: los dos coinciden siempre.

    0 3 * * *      → *-*-* 03:00:00
    */15 * * * *   → *-*-* *:00/15:00
    30 8 * * 1-5   → Mon..Fri *-*-* 08:30:00
"""
from __future__ import annotations

import os

SHORTCUTS = {
    "@hourly": "*-*-* *:00:00",
    "@daily": "*-*-* 00:00:00",
    "@midnight": "*-*-* 00:00:00",
    "@weekly": "Sun *-*-* 00:00:00",
    "@monthly": "*-*-01 00:00:00",
    "@yearly": "*-01-01 00:00:00",
    "@annually": "*-01-01 00:00:00",
}
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _L(es: str, en: str) -> str:
    return es if os.environ.get("ANDAMIO_LANG", "").startswith("es") else en


class CronError(ValueError):
    pass


def _number(text: str, lo: int, hi: int, what: str, names: list[str] | None = None) -> int:
    t = text.lower()
    if names and t[:3] in [n.lower() for n in names] and len(t) == 3:
        n = [x.lower() for x in names].index(t)
        return n + 1 if names is MONTHS else n
    if not t.isdigit() or not lo <= int(t) <= hi:
        raise CronError(_L(f"{what}: «{text}» fuera de rango ({lo}-{hi})", f"{what}: '{text}' out of range ({lo}-{hi})"))
    return int(t)


def _field(text: str, lo: int, hi: int, what: str, names: list[str] | None = None) -> list[str] | None:
    """Un campo → partes de systemd (sin formato aún), o None si es '*' (cualquiera)."""
    if text == "*":
        return None
    out = []
    for part in text.split(","):
        rng, _, step = part.partition("/")
        if step and (not step.isdigit() or int(step) == 0):
            raise CronError(_L(f"{what}: paso inválido en «{part}»", f"{what}: invalid step in '{part}'"))
        if rng == "*":
            if not step:
                raise CronError(_L(f"{what}: «*» no se combina con otros valores", f"{what}: '*' can't be combined"))
            out.append(("step", lo, hi, int(step)))
        elif "-" in rng:
            a, b = (_number(x, lo, hi, what, names) for x in rng.split("-", 1))
            if a > b:
                raise CronError(_L(f"{what}: rango al revés «{part}»", f"{what}: backwards range '{part}'"))
            out.append(("range", a, b, int(step) if step else 1))
        else:
            a = _number(rng, lo, hi, what, names)
            out.append(("range", a, hi if step else a, int(step) if step else 1))
    return out


def _values(parts) -> list[int]:
    vals: set[int] = set()
    for _, a, b, step in parts:
        vals.update(range(a, b + 1, step))
    return sorted(vals)


def _time_part(parts, lo: int) -> str:
    if parts is None:
        return "*"
    # Un paso desde el inicio (*/15) queda como lo escribe systemd: 00/15.
    if len(parts) == 1 and parts[0][0] == "step" and parts[0][1] == lo:
        return f"{lo:02d}/{parts[0][3]}"
    return ",".join(f"{v:02d}" for v in _values(parts))


def cron_calendar(expr: str) -> str:
    """Horario cron → OnCalendar de systemd (sin zona horaria). CronError si no es válido."""
    expr = " ".join(str(expr).split())
    if expr.startswith("@"):
        if expr in SHORTCUTS:
            return SHORTCUTS[expr]
        raise CronError(_L(f"Atajo desconocido: {expr} (sirven {', '.join(SHORTCUTS)})",
                           f"Unknown shortcut: {expr} (valid: {', '.join(SHORTCUTS)})"))
    fields = expr.split(" ")
    if len(fields) != 5:
        raise CronError(_L("El horario tiene 5 campos: minuto hora día mes día-de-la-semana (ej. «0 3 * * *»)",
                           "The schedule has 5 fields: minute hour day month weekday (e.g. '0 3 * * *')"))
    minute = _field(fields[0], 0, 59, _L("minuto", "minute"))
    hour = _field(fields[1], 0, 23, _L("hora", "hour"))
    dom = _field(fields[2], 1, 31, _L("día del mes", "day of month"))
    month = _field(fields[3], 1, 12, _L("mes", "month"), MONTHS)
    dow = _field(fields[4], 0, 7, _L("día de la semana", "weekday"), DAYS)
    if dom is not None and dow is not None:
        # cron corre si coincide CUALQUIERA de los dos; systemd exige los dos: no se traduce igual.
        raise CronError(_L("Usa el día del mes o el día de la semana, no los dos",
                           "Use the day of the month or the weekday, not both"))
    days = ""
    if dow is not None:
        names = sorted({v % 7 for v in _values(dow)})
        days = ",".join(DAYS[v] for v in names) + " "
        if len(names) > 2 and names == list(range(names[0], names[-1] + 1)):
            days = f"{DAYS[names[0]]}..{DAYS[names[-1]]} "
    date = f"*-{_time_part(month, 1)}-{_time_part(dom, 1)}"
    return f"{days}{date} {_time_part(hour, 0)}:{_time_part(minute, 0)}:00"


class FilterModule:
    def filters(self):
        return {"cron_calendar": cron_calendar}
