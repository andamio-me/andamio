---
title: Backups
description: Backups diarios, cifrados y fuera del servidor, con una prueba de restauración.
---

```bash
andamio backups
```

Sin backups, tus datos solo viven en el VPS. Este comando lo deja configurado, guiado:

1. **Dónde guardarlos:** Backblaze B2 o cualquier almacenamiento compatible con S3 (AWS,
   Cloudflare R2, Wasabi, MinIO).
2. **Prueba el destino** desde tu servidor.
3. **Hace el primer backup** en el momento.
4. **Prueba la restauración:** carga el respaldo de la base en un PostgreSQL temporal y lo
   compara con producción, sin tocarla.

Desde ahí, cada noche a las 03:30 UTC.

## Qué se respalda

Las bases de tus apps (un dump consistente de PostgreSQL), Redis, los archivos de la
plataforma y lo necesario para reconstruir el servidor: la configuración de SSH, la VPN y
los secretos del servidor.

## Cómo se protegen

- **Cifrados en tu servidor antes de subir**, con restic: el proveedor nunca ve tus datos.
  La contraseña del repositorio es aleatoria y vive cifrada en tu copia (sops).
- **Imborrables desde el servidor**, con B2: andamio puede crear la llave del servidor
  **sin permiso de borrar**, limitada a un bucket. Necesita tu master key una sola vez y no
  la guarda. Quien tome tu servidor no puede borrar tus backups.
- Se guardan **7 diarios, 4 semanales y 6 mensuales**.

## Revisarlos

`andamio estado` te dice cuándo fue el último backup y si salió bien. Con Telegram activado,
te avisa cada noche.

## Restaurar

Si el servidor desaparece:

1. Crea un VPS nuevo y apunta el DNS a su IP (cambia `andamio_server_ip` en tu
   configuración).
2. `andamio servidor`.
3. Restaura el último backup en el servidor:

```bash
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic restore latest --tag andamio --target /'
```

4. `andamio servidor` otra vez, para que todo arranque con los datos restaurados.

La guía completa está en tu copia: `docs/runbooks/restaurar-backup.md`.
