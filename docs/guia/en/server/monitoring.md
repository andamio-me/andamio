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

## Phone alerts

```bash
andamio alerts
```

With any monitoring level, the minimal one too, andamio tells you if:

- a container goes down, keeps restarting, or its health check fails, for over a minute (a
  deploy doesn't trigger anything);
- the disk goes over 85%.

And another notice when it's resolved. Apps you stopped with `andamio app stop` don't count.

Notices arrive through **ntfy**: a free app (Android, iOS or the browser) that receives
notifications from a "topic" **without an account**. `andamio alerts` makes up a long random
topic, tells you how to subscribe (with a QR code) and sends a test one from the server. If
you prefer, use your own ntfy server. With Telegram on, they arrive there too. You can also
set it up from the panel (`andamio ui`, Settings).

`andamio status` warns you if nobody is alerting you.

## Where to see it

With the `completo` level, through the VPN:

- **Grafana** at `grafana.yourdomain.com`: dashboards for the server, each container and the
  logs, and alerts (full disk, container down, certificate about to expire).
- **Uptime Kuma** at `status.yourdomain.com`: checks every minute that your sites answer.

## Telegram alerts

```bash
andamio telegram          # guided: your bot, your chat, encrypted in your repo and applied
andamio telegram test     # a test notice
andamio telegram off      # no notices, no daily summary and no bot
```

1. In Telegram, open @BotFather, send it `/newbot` and paste the token it gives you (it isn't
   shown). andamio checks it with Telegram.
2. Open your bot and tap **Start**: andamio finds your chat by itself (no IDs to look up).
3. It's encrypted in `host/sops/telegram-env.sops`, pushed and applied on your server; a test
   message reaches you.

From then on: notices of failed deploys, of the backup and of failing tasks, a daily server
summary, and a bot that answers `/system`. Grafana's alerts go there too, with the `completo`
level. In the [panel](/en/docs/apps/panel/): **Settings → Set up Telegram**.
