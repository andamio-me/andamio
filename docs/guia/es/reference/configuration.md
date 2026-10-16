---
title: Configuración
description: Las opciones de tu servidor, en ansible/group_vars/all.yml.
---

La configuración de tu servidor vive en un solo archivo de tu copia:
`ansible/group_vars/all.yml`. La crea `andamio init`; puedes editarla y aplicar con
`andamio servidor`.

```yaml
andamio_user: andamio
andamio_ssh_port: 28980
andamio_server_ip: 203.0.113.10
andamio_domain: tudominio.com
andamio_tls: http
andamio_monitoring: auto
andamio_backups: false
andamio_telegram: false
```

## Opciones

| Clave | Qué es |
|---|---|
| `andamio_domain` | El dominio de tu servidor: cada app es un subdominio suyo |
| `andamio_server_ip` | La IP pública del VPS |
| `andamio_user` | Tu usuario de operación en el servidor (SSH, Docker) |
| `andamio_ssh_port` | El puerto SSH (no el 22) |
| `andamio_ssh_host_key` | La huella verificada del servidor: andamio no se conecta a otro |
| `andamio_hostname` | El nombre del servidor en las métricas |
| `andamio_tls` | `http` (Let's Encrypt por app), `cloudflare` (comodín por DNS) o `custom` (tu certificado). Ver [HTTPS y certificados](/es/docs/server/certificate/) |
| `andamio_acme_email` | Tu correo para los avisos de Let's Encrypt |
| `andamio_monitoring` | `auto`, `minimo` o `completo`. Ver [Monitoreo](/es/docs/server/monitoring/) |
| `andamio_postgres_*`, `andamio_redis_*` | Memoria, CPU y ajustes de PostgreSQL y Redis (los deja `andamio servicios`). Ver [PostgreSQL y Redis](/es/docs/server/services/) |
| `andamio_backups` | `true` lo activa `andamio backups`. Ver [Backups](/es/docs/server/backups/) |
| `andamio_telegram` | `true` con el bot y el chat en `host/sops/telegram-env.sops` |
| `andamio_forge` | `github`. Todo lo de la forja pasa por `bin/forge`: agregar GitLab es implementar ese archivo |
| `andamio_registry` | El registro de las imágenes de tus apps (`ghcr.io`) |
| `andamio_github_owner` | El usuario u organización dueño de tus apps |
| `andamio_repo` | Tu copia de andamio: de ahí baja el servidor su configuración |

## Qué más es tuyo en tu copia

| Archivo | Qué es |
|---|---|
| `apps/<app>/app.yml` | La definición de cada app. Ver [Crear una app](/es/docs/apps/create/#appsmiappappyml) |
| `apps/<app>/secrets.sops.env` | Sus variables, cifradas |
| `stacks/*/secrets.sops.env` | Las contraseñas de la plataforma, cifradas |
| `ansible/inventory.yml` | Cómo llegar a tu servidor (el alias de `~/.ssh/config`) |
| `.sops.yaml` | Con qué llave se cifra |

`andamio update` nunca toca esos archivos.
