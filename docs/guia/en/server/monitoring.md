---
title: Monitoring
description: Metrics always; logs, dashboards, alerts and an external check if you want them.
---

In your configuration (`ansible/group_vars/all.yml`):

```yaml
andamio_monitoring: auto
```

| Level | What runs | RAM |
|---|---|---|
| `minimo` | Prometheus, cAdvisor and node-exporter: metrics for the server and each container | ~115 MiB |
| `completo` | the above, plus Loki and Alloy (logs), Grafana (dashboards and alerts) and Uptime Kuma (checks your sites from outside) | ~670 MiB |
| `auto` (default) | `completo` if the server has 3 GB of RAM or more; otherwise `minimo` | |

To change it, edit the value and apply:

```bash
andamio server
```

Going down to `minimo` stops what's left over. Its data (logs, dashboards, monitors) stays:
if you go back to `completo`, it returns with its history.

## Where to see it

With the `completo` level, through the VPN:

- **Grafana** at `grafana.yourdomain.com`: dashboards for the server, each container and the
  logs, and alerts (full disk, container down, certificate about to expire).
- **Uptime Kuma** at `status.yourdomain.com`: checks every minute that your sites answer.

## Telegram alerts

With `andamio_telegram: true` and the bot's token and your chat in
`host/sops/telegram-env.sops`: notices of failed deploys and of the backup, a daily server
summary, and a bot that answers `/system`. Grafana's alerts go there too, with the
`completo` level.
