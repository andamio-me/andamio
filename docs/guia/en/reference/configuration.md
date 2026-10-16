---
title: Configuration
description: Your server's options, in ansible/group_vars/all.yml.
---

Your server's configuration lives in a single file of your copy:
`ansible/group_vars/all.yml`. `andamio init` creates it; you can edit it and apply with
`andamio server`.

```yaml
andamio_user: andamio
andamio_ssh_port: 28980
andamio_server_ip: 203.0.113.10
andamio_domain: yourdomain.com
andamio_tls: http
andamio_monitoring: auto
andamio_backups: false
andamio_telegram: false
```

## Options

| Key | What it is |
|---|---|
| `andamio_domain` | Your server's domain: each app is a subdomain of it |
| `andamio_server_ip` | The VPS's public IP |
| `andamio_user` | Your operations user on the server (SSH, Docker) |
| `andamio_ssh_port` | The SSH port (not 22) |
| `andamio_ssh_host_key` | The server's verified fingerprint: andamio won't connect to another one |
| `andamio_hostname` | The server's name in the metrics |
| `andamio_tls` | `http` (Let's Encrypt per app), `cloudflare` (wildcard via DNS) or `custom` (your certificate). See [HTTPS and certificates](/en/docs/server/certificate/) |
| `andamio_acme_email` | Your email for Let's Encrypt notices |
| `andamio_monitoring` | `auto`, `minimo` or `completo`. See [Monitoring](/en/docs/server/monitoring/) |
| `andamio_postgres_*`, `andamio_redis_*` | PostgreSQL and Redis memory, CPU and settings (set by `andamio services`). See [PostgreSQL and Redis](/en/docs/server/services/) |
| `andamio_backups` | `andamio backups` sets it to `true`. See [Backups](/en/docs/server/backups/) |
| `andamio_telegram` | `true` with the bot and the chat in `host/sops/telegram-env.sops` |
| `andamio_forge` | `github`. Everything about the forge goes through `bin/forge`: adding GitLab is implementing that file |
| `andamio_registry` | The registry for your apps' images (`ghcr.io`) |
| `andamio_github_owner` | The user or organization that owns your apps |
| `andamio_repo` | Your copy of andamio: the server pulls its configuration from there |

## What else is yours in your copy

| File | What it is |
|---|---|
| `apps/<app>/app.yml` | Each app's definition. See [Create an app](/en/docs/apps/create/#appsmyappappyml) |
| `apps/<app>/secrets.sops.env` | Its variables, encrypted |
| `stacks/*/secrets.sops.env` | The platform's passwords, encrypted |
| `ansible/inventory.yml` | How to reach your server (the `~/.ssh/config` alias) |
| `.sops.yaml` | Which key encrypts |

`andamio update` never touches those files.
