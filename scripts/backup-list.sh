#!/usr/bin/env bash
# La lista de respaldos, sin secretos (fecha, cuánto tardó, tamaño), y lo que hay en
# /srv/andamio/archive (nombre, tamaño, fecha), en un archivo que se puede leer sin sudo: el panel
# (andamio ui) la muestra sin pedirte la contraseña. La deja
# backup.sh al terminar cada respaldo; a mano: sudo scripts/backup-list.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Correr con sudo / Run with sudo"; exit 1; }
set -a; . /etc/restic/env; . /etc/andamio/andamio.env 2> /dev/null || true; set +a
OUT=/var/lib/andamio-backup/snapshots.json
install -d -m 755 "$(dirname "$OUT")"
restic snapshots --tag andamio --json | python3 -c '
import json, os, re, sys
from datetime import datetime
def epoch(s):   # restic: 2026-10-11T03:00:01.123456789-05:00 (nanosegundos, con zona)
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$", s or "")
    if not m:
        return None
    tz = m.group(3) or "Z"
    return datetime.fromisoformat(m.group(1) + ("+00:00" if tz == "Z" else tz)).timestamp() + float("0" + (m.group(2) or ""))
out = []
for s in json.load(sys.stdin):
    m = s.get("summary") or {}
    start, end = epoch(m.get("backup_start", "")), epoch(m.get("backup_end", ""))
    out.append({"id": s["id"], "short": s.get("short_id", s["id"][:8]), "time": epoch(s["time"]),
                "secs": round(end - start) if start and end else None,
                "size": m.get("total_bytes_processed"), "added": m.get("data_added_packed", m.get("data_added")),
                "files": m.get("total_files_processed")})
out.sort(key=lambda x: x["time"] or 0, reverse=True)
# El archivo: lo más nuevo primero. Solo nombres, tamaños y fechas (nunca su contenido).
archive, root = [], "/srv/andamio/archive"
for name in os.listdir(root) if os.path.isdir(root) else []:
    st = os.stat(os.path.join(root, name))
    if os.path.isfile(os.path.join(root, name)):
        archive.append({"name": name, "size": st.st_size, "time": st.st_mtime})
archive.sort(key=lambda x: x["time"], reverse=True)
days = os.environ.get("ANDAMIO_ARCHIVE_DAYS", "90")
json.dump({"at": datetime.now().timestamp(), "snapshots": out[:60], "archive": archive[:200],
           "archive_total": sum(a["size"] for a in archive), "archive_days": int(days) if days.isdigit() else 90}, sys.stdout)
' > "$OUT.tmp"
chmod 644 "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
echo "✓ $(python3 -c 'import json, sys; print(len(json.load(open(sys.argv[1]))["snapshots"]))' "$OUT") snapshots → $OUT"
