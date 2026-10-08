# 0007. PostgreSQL y Redis compartidos en la red data

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Decisión
- Un PostgreSQL 18 compartido (`stacks/data`). Cada app tiene su propio usuario
  y su propia base (`scripts/pg-create-app.sh`), con `REVOKE ALL ... FROM PUBLIC`.
- Un Redis 8 compartido, con contraseña, AOF activado y `noeviction` (requisito de BullMQ).
- Los dos solo en la red `data` (internal): sin internet y sin puertos publicados.
- `shm_size: 256m` para PostgreSQL (el default de Docker, 64 MB, rompe consultas paralelas).

## Alternativas
- Un PostgreSQL por app: más aislamiento, más RAM y backups dispersos.
- Valkey: fork open source de Redis, compatible. Se eligió Redis 8 (licencia AGPL)
  por ser el que ya se usa en los proyectos.

## Consecuencias
- Una app comprometida solo ve su base. Backups centralizados (Fase 5).
- Redis es compartido: las apps deben usar prefijos de clave propios.
  Si hace falta aislamiento real, usar ACLs de Redis por app.
- La contraseña de Redis es visible en `docker inspect` (aceptable: docker = root).
