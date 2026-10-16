#!/usr/bin/env python3
"""Copia todas las claves de un Redis (o Valkey, o Dragonfly) a otro, por tipo y con su vencimiento.

Lo usa redis-engine.sh al cambiar de motor: Redis 8, Valkey y Dragonfly guardan en formatos de
archivo que los otros no leen, así que los datos pasan clave por clave, como comandos. Solo usa
la biblioteca estándar (el servidor no tiene más).

  kv-copy.py <origen host:puerto> <destino host:puerto>     (la clave del admin: REDIS_PASSWORD)

Copia strings, hashes, listas, sets, sets ordenados y streams (con sus grupos de consumidores;
los mensajes pendientes de entregar no viajan). Un tipo que no conoce (de un módulo) detiene
todo antes de escribir: mejor no cambiar de motor que perder algo sin avisar. Al final compara
cuántas claves hay en cada lado. Sale con 3 si no llega a alguno de los dos.
"""
from __future__ import annotations

import os
import socket
import sys


class Conn:
    """Un cliente RESP mínimo: comandos como listas de bytes, respuestas como valores de Python."""

    def __init__(self, addr: str, password: str):
        host, _, port = addr.rpartition(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        self.buf = self.sock.makefile("rb")
        if password:
            self.call("AUTH", password)

    def send(self, *args) -> None:
        parts = [b"*%d\r\n" % len(args)]
        for a in args:
            b = a if isinstance(a, bytes) else str(a).encode()
            parts.append(b"$%d\r\n%s\r\n" % (len(b), b))
        self.sock.sendall(b"".join(parts))

    def read(self):
        line = self.buf.readline()
        if not line:
            raise ConnectionError("se cerró la conexión")
        kind, rest = line[:1], line[1:-2]
        if kind == b"+":
            return rest.decode()
        if kind == b"-":
            raise RuntimeError(rest.decode())
        if kind == b":":
            return int(rest)
        if kind == b"$":
            n = int(rest)
            if n < 0:
                return None
            data = self.buf.read(n + 2)
            return data[:-2]
        if kind == b"*":
            n = int(rest)
            return None if n < 0 else [self.read() for _ in range(n)]
        raise RuntimeError(f"respuesta inesperada: {line!r}")

    def call(self, *args):
        self.send(*args)
        return self.read()


def pairs(flat: list) -> list[tuple]:
    return list(zip(flat[0::2], flat[1::2]))


def dump(src: Conn, key: bytes, kind: str) -> list[list]:
    """Los comandos que recrean una clave en el destino."""
    if kind == "string":
        return [["SET", key, src.call("GET", key)]]
    if kind == "hash":
        flat = src.call("HGETALL", key)
        return [["HSET", key, *flat]] if flat else []
    if kind == "list":
        items = src.call("LRANGE", key, 0, -1)
        return [["RPUSH", key, *items]] if items else []
    if kind == "set":
        items = src.call("SMEMBERS", key)
        return [["SADD", key, *items]] if items else []
    if kind == "zset":
        flat = src.call("ZRANGE", key, 0, -1, "WITHSCORES")
        args = [x for member, score in pairs(flat) for x in (score, member)]
        return [["ZADD", key, *args]] if args else []
    if kind == "stream":
        cmds = [["XADD", key, entry_id, *fields] for entry_id, fields in src.call("XRANGE", key, "-", "+")]
        for g in src.call("XINFO", "GROUPS", key) or []:
            info = dict(pairs(g))
            name = info.get(b"name") or info.get("name")
            last = info.get(b"last-delivered-id") or info.get("last-delivered-id") or b"0"
            cmds.append(["XGROUP", "CREATE", key, name, last, "MKSTREAM"])
        return cmds
    raise ValueError(kind)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    password = os.environ.get("REDIS_PASSWORD", "")
    try:
        src, dst = Conn(sys.argv[1], password), Conn(sys.argv[2], password)
    except OSError as e:   # no llego (p. ej., Docker Desktop no deja entrar a sus redes): 3
        print(f"No llego a {sys.argv[1]} o {sys.argv[2]}: {e}", file=sys.stderr)
        return 3
    if dst.call("DBSIZE"):
        print("✗ El destino ya tiene datos: no copio encima.", file=sys.stderr)
        return 1
    # Primero todo en memoria y revisado; recién después se escribe.
    plan, unknown, cursor = [], [], b"0"
    while True:
        cursor, keys = src.call("SCAN", cursor, "COUNT", 1000)
        for key in keys:
            kind = src.call("TYPE", key)
            if kind == "none":   # venció mientras tanto
                continue
            if kind not in ("string", "hash", "list", "set", "zset", "stream"):
                unknown.append(f"{key.decode(errors='replace')} ({kind})")
                continue
            plan.append((key, dump(src, key, kind), src.call("PTTL", key)))
        if cursor in (b"0", 0, "0"):
            break
    if unknown:
        print("✗ Claves de un tipo que no sé copiar (de un módulo): " + ", ".join(unknown[:10]), file=sys.stderr)
        return 1
    copied = 0
    for key, cmds, ttl in plan:
        for c in cmds:
            dst.call(*c)
        if ttl and ttl > 0:
            dst.call("PEXPIRE", key, ttl)
        copied += 1 if cmds else 0
    have = dst.call("DBSIZE")
    print(f"✓ {copied} claves copiadas (el destino tiene {have})")
    return 0 if have >= copied else 1


if __name__ == "__main__":
    sys.exit(main())
