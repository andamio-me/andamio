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
| `andamio_provider`, `andamio_provider_user` | Where the VPS is and the user your provider gave you (set by `andamio security`; only used to get in the first time) |
| `andamio_rate_average`, `andamio_rate_burst` | Per-IP request limit on public apps: per second sustained (100) and at once (300) |
| `andamio_pipeline` | The repo your apps' pipeline comes from (`andamio-me/andamio`, set by `setup`). Without it, your copy's |
| `andamio_vpn_dns` | The DNS new VPN clients get (e.g. `10.8.0.1`, your own DNS on the VPN). Empty: their network's |
| `andamio_open_ports` | Ports open to the internet on purpose, each with its reason: `andamio status` treats them as fine |

## Your own stacks

Besides the platform's, you can run your own (a password manager, a DNS, a game): a
`stacks/<stack>/` folder with its `compose.yaml` and `secrets.sops.env`, and in the config:

```yaml
andamio_stacks: [..., stacks/my-stack]
andamio_data_dirs:            # under /srv/andamio/data: part of the daily backup
  - { name: my-stack, owner: "1000", mode: "0750" }   # root and 0700 if not given
andamio_stack_env:            # the non-secret part of its .env
  stacks/my-stack: { MY_VARIABLE: value }
andamio_extra_units: []       # your own units from host/systemd/ (installed and enabled)
```

If it needs a consistent copy (pausing the container, a dump of its database), add
`stacks/<stack>/backup-hook.sh`: the daily backup runs it before uploading, with the folder to
leave its files in as the argument.

## What else is yours in your copy

| File | What it is |
|---|---|
| `apps/<app>/app.yml` | Each app's definition. See [Create an app](/en/docs/apps/create/#appsmyappappyml) |
| `apps/<app>/secrets.sops.env` | Its variables, encrypted |
| `stacks/*/secrets.sops.env` | The platform's passwords, encrypted |
| `ansible/inventory.yml` | How to reach your server (the `~/.ssh/config` alias) |
| `.sops.yaml` | Which key encrypts |

`andamio update` never touches those files.
