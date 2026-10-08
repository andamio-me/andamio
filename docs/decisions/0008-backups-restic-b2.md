# 0008. Backups con restic en Backblaze B2

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Decisión
- restic con repositorio cifrado en B2 (`b2:mis-backups:homelab`).
- Diario a las 03:30 UTC (timer de systemd): `pg_dumpall` sin comprimir (mejor
  deduplicación), snapshot de Redis y `/srv/homelab` (incluye los `.env`).
- Retención: 7 diarios, 4 semanales, 6 mensuales. `restic check` en cada ejecución.
- Bucket privado, "keep only last version"; llave de aplicación limitada al bucket.
- Credenciales en `/etc/restic/` (root, 600). Copia de la contraseña en el gestor.

## Consecuencias
- Los backups sobreviven a la pérdida del VPS. Restauración probada.
- Sin la contraseña de restic, los backups son irrecuperables.
- Riesgo pendiente: con acceso root al VPS se pueden borrar los backups
  (evaluar Object Lock en Fase 7). Alertas de fallo: Fase 6.
