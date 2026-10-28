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
| `andamio_provider`, `andamio_provider_user` | Dónde está el VPS y el usuario que te dio el proveedor (los deja `andamio seguridad`; solo se usan para entrar la primera vez) |
| `andamio_rate_average`, `andamio_rate_burst` | Límite de peticiones por IP en las apps públicas: por segundo sostenido (100) y de golpe (300) |
| `andamio_pipeline` | El repo del pipeline de tus apps (`andamio-me/andamio`, lo deja `setup`). Sin él, el de tu copia |
| `andamio_vpn_dns` | El DNS que reciben los clientes nuevos de la VPN (p. ej. `10.8.0.1`, un DNS propio en la VPN). Vacío: el de su red |
| `andamio_open_ports` | Puertos abiertos a Internet a propósito, cada uno con su motivo: `andamio estado` los da por buenos |

## Stacks propios

Además de los de la plataforma, puedes correr los tuyos (un gestor de contraseñas, un DNS, un
juego): una carpeta `stacks/<stack>/` con su `compose.yaml` y su `secrets.sops.env`, y en la config:

```yaml
andamio_stacks: [..., stacks/mi-stack]
andamio_data_dirs:            # en /srv/andamio/data: entran al backup diario
  - { name: mi-stack, owner: "1000", mode: "0750" }   # dueño root y 0700 si no se dicen
andamio_stack_env:            # lo no secreto de su .env
  stacks/mi-stack: { MI_VARIABLE: valor }
andamio_extra_units: []       # units propios de host/systemd/ (se instalan y activan)
```

Si necesita una copia coherente (pausar el contenedor, un dump de su base), agrega
`stacks/<stack>/backup-hook.sh`: el backup diario lo corre antes de subir, con la carpeta donde
dejar lo suyo como argumento.

## Qué más es tuyo en tu copia

| Archivo | Qué es |
|---|---|
| `apps/<app>/app.yml` | La definición de cada app. Ver [Crear una app](/es/docs/apps/create/#appsmiappappyml) |
| `apps/<app>/secrets.sops.env` | Sus variables, cifradas |
| `stacks/*/secrets.sops.env` | Las contraseñas de la plataforma, cifradas |
| `ansible/inventory.yml` | Cómo llegar a tu servidor (el alias de `~/.ssh/config`) |
| `.sops.yaml` | Con qué llave se cifra |

`andamio update` nunca toca esos archivos.
