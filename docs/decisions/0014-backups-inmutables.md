# 0014. Backups a prueba de borrado desde el VPS

- **Estado:** Aceptada
- **Fecha:** 2026-10-07

## Problema
Con root en el VPS se leía `/etc/restic/env`, y esa llave de B2 tenía
`deleteFiles`: quien tomara el servidor podía borrar también los backups.

## Decisión
- **Llave de B2 del VPS sin `deleteFiles`** (`restic-vps-sin-borrar`: un solo
  bucket, `listBuckets,listFiles,readFiles,writeFiles`). Desde restic 0.17, si no
  puede borrar, **oculta** (B2 conserva la versión). Se crea con
  `scripts/b2-create-restic-key.sh` desde el WSL: el CLI `b2` nuevo crea llaves
  multi-bucket, que restic (autoriza con API v3) no acepta.
- **Ciclo de vida del bucket: lo oculto se borra a los 30 días.** Solo se cambia
  desde la cuenta de B2 (no desde el VPS). Es la ventana para detectar un ataque
  y recuperar.
- **restic oficial 0.19.1** (`/usr/local/bin`, rol `base`): el de Ubuntu (0.16) no
  sabe ocultar.
- La master key de B2 vive solo en el gestor de contraseñas, nunca en el VPS ni
  en el repo.

## Consecuencias
- `restic forget --prune` sigue funcionando; el espacio se libera 30 días después.
- Un atacante con root puede ocultar archivos y subir basura, pero no borrar nada
  durante 30 días. Telegram avisa de cada backup fallido.
- Recuperar tras un ataque: desocultar desde la cuenta de B2 (ver
  `docs/runbooks/restaurar-backup.md`, "Si alguien ocultó los backups").
- Sigue pendiente una copia fuera de B2 (otra cuenta o disco local).
