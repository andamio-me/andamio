#!/usr/bin/python
"""Varios archivos en una sola tarea: una ida y vuelta por SSH en total, no una (o dos) por
archivo como copy o template en un loop. Con el servidor lejos, cada ida y vuelta son ~2 s.

Escribe solo lo que cambió (contenido, dueño o permisos), de forma atómica (archivo temporal
en la misma carpeta y rename), y devuelve en `files` la lista de los que cambió. La carpeta de
cada archivo tiene que existir. Para secretos: no_log en la tarea."""

DOCUMENTATION = r"""
module: andamio_files
short_description: Escribe varios archivos de una vez, solo los que cambiaron
options:
  files:
    description: Lista de archivos, cada uno con dest, content, owner, group y mode.
    type: list
    elements: dict
    required: true
"""

import grp
import os
import pwd
import stat
import tempfile

from ansible.module_utils.basic import AnsibleModule


def ids(owner, group):
    owner, group = str(owner), str(group)
    uid = int(owner) if owner.isdigit() else pwd.getpwnam(owner).pw_uid
    gid = int(group) if group.isdigit() else grp.getgrnam(group).gr_gid
    return uid, gid


def main():
    module = AnsibleModule(argument_spec={"files": {"type": "list", "elements": "dict", "required": True}},
                           supports_check_mode=True)
    changed = []
    for f in module.params["files"]:
        dest = f["dest"]
        data = str(f["content"]).encode()
        uid, gid = ids(f.get("owner", "root"), f.get("group", "root"))
        mode = f.get("mode", "0644")
        mode = int(mode, 8) if isinstance(mode, str) else mode
        try:
            st = os.stat(dest)
            with open(dest, "rb") as h:
                same = h.read() == data
            meta = (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) == (uid, gid, mode)
        except FileNotFoundError:
            same = meta = False
        if same and meta:
            continue
        changed.append(dest)
        if module.check_mode:
            continue
        if same:
            os.chown(dest, uid, gid)
            os.chmod(dest, mode)
            continue
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), prefix=".andamio-")
        try:
            os.fchown(fd, uid, gid)
            os.fchmod(fd, mode)
            with os.fdopen(fd, "wb") as h:
                h.write(data)
                h.flush()
                os.fsync(h.fileno())
            os.replace(tmp, dest)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    module.exit_json(changed=bool(changed), files=changed)


if __name__ == "__main__":
    main()
