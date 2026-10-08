# 0020. Simulacro de restauración

- **Estado:** Aceptada
- **Fecha:** 2026-10-08

## Contexto
Había backups diarios cifrados en B2 (ADR 0008 y 0014), pero nunca se había
restaurado uno. Desde la ADR 0019 viven en el servidor mis archivos personales
(Seafile), así que un backup sin probar dejó de ser aceptable.

## Decisión
`scripts/restore-drill.sh` (root) prueba el último snapshot sin tocar producción:
1. Línea base en vivo: huella sha256 de cada archivo de Seafile (`seaf-fsck --export`)
   y conteos de la base de short.
2. `restic check --read-data-subset=5%` y `restic restore latest` a `/srv/restore-drill`.
3. Copias temporales `drill-*` en una red interna propia, sin Traefik ni puertos:
   PostgreSQL y MariaDB con los dumps restaurados, y Seafile con sus archivos.
4. Compara copia contra producción y borra todo al salir, también si falla.

Se corre después de un backup manual, para comparar contra el mismo momento.

## Resultado (2026-10-08)
4 de 4 comprobaciones correctas: Seafile arranca desde el backup, los archivos tienen
las mismas huellas y la base de short coincide. **Recuperación de datos: 72 s**
(restore 23 s, bases 33 s, Seafile en marcha 16 s; 368 MiB).

## Hallazgos
- **Un backup colgado bloqueaba todos los siguientes, en silencio.** El de la noche del
  2026-10-08 quedó 10 h en `restic forget --prune` esperando una respuesta de B2, sin
  salida y sin aviso; el timer no arranca otro mientras uno sigue activo. Arreglo: cada
  paso de restic con `timeout` (cuenta como fallo y avisa) y `TimeoutStartSec=3h` en el
  servicio, con aviso "cortado_por_tiempo". `forget` y `prune` corridos a mano
  terminaron bien: fue un cuelgue puntual, no la llave sin `deleteFiles`.
- **La guía de restauración no cubría Seafile** (se escribió antes que la ADR 0019).
  Agregado a `docs/runbooks/restaurar-backup.md`.
- `mariadb-admin ping` y `pg_isready` por socket dan "listo" durante el servidor
  temporal de la inicialización de sus imágenes: se espera por TCP a una consulta real.

## Consecuencias
- Hay una cifra real de recuperación de datos. No cubre reconstruir el servidor
  desde cero (Ansible + restore), que sigue pendiente de probar.
- Repetirlo al menos una vez al mes y después de cambios en backup.sh o en los stacks.
