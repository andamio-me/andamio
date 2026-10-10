---
title: Introduction
description: What andamio is, how it works and where to start.
---

andamio is an open source PaaS for **a single VPS**. First it secures your server (own user,
key-only SSH, firewall, VPN, automatic patches, backups), then it deploys your apps, each one
isolated, with a `git push`. No web panel: everything goes through your terminal and your
repo.

## Pick a page

| I want to… | Go to |
|---|---|
| See what I need before starting | [Requirements](/en/docs/start/requirements/) |
| Install andamio and set up my server | [Install](/en/docs/start/install/) and [Your server](/en/docs/start/server/) |
| Ship my first app | [Create an app](/en/docs/apps/create/) |
| Understand what happens on every `git push` | [Deploys](/en/docs/apps/deploys/) |
| Use my domain or a subdomain | [Domains and URLs](/en/docs/apps/domains/) |
| Give my app an API key | [Variables and secrets](/en/docs/apps/secrets/) |
| Keep the frontend on Vercel and the backend here | [Backend only](/en/docs/apps/backend-only/) |
| Find out why a deploy failed | [When something fails](/en/docs/apps/failures/) |
| Stop, roll back or delete an app | [Manage an app](/en/docs/apps/manage/) |
| Keep files that last (uploads, SQLite) | [Persistent folders](/en/docs/apps/manage/#persistent-folders) |
| Run something every night (cleanups, reports) | [Scheduled tasks](/en/docs/apps/manage/#scheduled-tasks) |
| See everything in the browser | [Local panel](/en/docs/apps/panel/) (`andamio ui`) |
| Get notified if something goes down | [Phone alerts](/en/docs/server/monitoring/#phone-alerts) |
| Check that my server is secure | [Security](/en/docs/server/security/) |
| Back up my data off the server | [Backups](/en/docs/server/backups/) |
| Get andamio's improvements | [Update](/en/docs/server/update/) |
| See every command | [Commands](/en/docs/reference/commands/) |

## Quick start

```bash
# 1. On your machine (Linux, macOS or WSL): installs what's missing and creates your private copy
curl -fsSL https://raw.githubusercontent.com/Geovani29/andamio/main/install.sh | sh

# 2. Your configuration: guided questions, all local
cd ~/my-andamio
andamio init

# 3. Your server: hardens it and starts the platform (safe to repeat)
andamio server

# 4. Your first app, from a repo of yours in any language
andamio app create myapp --repo your-user/myapp --health /healthz --public
```

From then on, every `git push` to `main` of your app's repo deploys it to
`https://myapp.yourdomain.com`.

## How it works

Owning a server has two stages, and andamio covers both:

1. **"I bought a VPS, now what?"** It usually comes with root, a password and every port
   open. `andamio server` hardens it and starts the platform: Traefik with automatic HTTPS,
   shared PostgreSQL and Redis (with one user per app), monitoring and the VPN.
2. **"I want to ship my apps."** Each app is built on GitHub Actions (never on your VPS),
   goes through a secrets scan, your tests and a vulnerability scan, and reaches your server
   with a key that can only deploy that app.

Everything about your server lives in **your copy of andamio**, a private repo on your
GitHub: the configuration, the secrets (encrypted with sops and age) and each app's
definition. If the server disappears, it's rebuilt from that repo and your backups.

## What andamio isn't

- **It isn't high availability.** It's a single server: if it goes down, your apps go down
  with it.
- **It has no web panel.** If you'd rather manage everything with clicks, Coolify or Dokploy
  will feel more comfortable.
- **It isn't for not having a server.** If you don't want one, a managed PaaS (Railway,
  Render, Vercel) is simpler.
