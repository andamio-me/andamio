# andamio

**A secure-by-default PaaS for a single VPS.** Take a server you just bought, harden it,
and deploy your apps to it, each one isolated, with every change going through git.

[Español](README.es.md)

> **Status: alpha.** andamio runs a real server in production (apps, a file-sync service,
> monitoring, backups). The guided install from a brand-new VPS (`andamio server`) is
> written but **has not yet been tested end-to-end on a fresh machine**. Expect rough edges.
> The CLI currently talks in Spanish.

---

## Why andamio

Self-hosting has two stages, and most tools only cover the second one:

1. **"I just bought a VPS, now what?"** It usually comes with root, a password, and every
   port open. andamio hardens it: your own user, SSH with keys only on a non-default port,
   root login disabled, a firewall, automatic security updates, a VPN for private tools,
   and HTTPS.
2. **"I want to deploy my apps."** On that hardened server, every app gets its own
   database and Redis users; a deploy key that can deploy *that app and nothing else*;
   and a pipeline that runs your tests and scans for vulnerabilities and
   leaked secrets **before** anything reaches the server.

| | andamio | Coolify / Dokploy | Dokku | Kamal |
|---|---|---|---|---|
| Hardens the server (SSH, firewall, updates, VPN) | ✅ | you do it | you do it | you do it |
| Web panel | none (git + CLI) | yes | no | no |
| Where images are built | GitHub Actions | on your VPS | on your VPS | your machine or CI |

What andamio adds on top, built in: tests, secret and vulnerability scanning before any
image is published; least privilege per app; and backups that can be made undeletable
from the server, with a restore drill.

andamio is not trying to be the easiest panel. It's the PaaS you can **fully understand**:
no hidden state, the whole server rebuilds from your repo, and every design decision is
written down.

## What you get

**Stage 1: a hardened server** (no third-party accounts needed)
- Dedicated operator user; SSH with keys only, on a port you choose; root login disabled.
- UFW firewall: only SSH, HTTP/HTTPS, and the VPN port are open.
- Unattended security upgrades; no snapd, no unneeded services.
- Docker with log rotation; the Docker socket is only reachable through a read-only proxy.
- Traefik with automatic HTTPS (Let's Encrypt) and security headers.
- WireGuard VPN, generated for you, with your first client config ready to import.
  Admin tools (Grafana, status page, your private apps) answer **only** through it.
- Monitoring sized to your RAM: metrics everywhere; logs, dashboards, alerts and an
  uptime monitor when the server has 3 GB or more.

**Stage 2: isolated, verified deploys**
- Any language. Your app needs a `Dockerfile`, that's the contract.
- Built in GitHub Actions, never on your VPS (so a 1-2 GB server is enough).
- Before publishing an image: secret scan (gitleaks), your tests (a `test` stage in your
  Dockerfile), vulnerability scan (Trivy). A vulnerable image never reaches the registry.
- Zero-downtime deploys: the new version starts next to the old one and must pass its
  health check before the old one stops. Rollback is one command.
- Per app: its own PostgreSQL user and database, its own Redis user (ACL, limited to the
  app's keys), and a deploy key restricted to deploying that single app.

**Optional, guided** (they need an account somewhere)
- Encrypted, deduplicated backups with restic to any backend (S3, B2, SFTP, ...). With
  Backblaze B2 they can be made **undeletable from the server**, and a restore drill
  verifies they actually restore.
- Telegram alerts, a daily summary and a small ops bot.
- A wildcard certificate through Cloudflare DNS (keeps private app names out of public
  certificate logs).

## Requirements

- A VPS with **Ubuntu 24.04**, 1 GB RAM minimum (2 GB+ is comfortable), and its public IP.
- A **domain** with two DNS `A` records pointing to that IP: `example.com` and `*.example.com`.
- A **GitHub** account (your apps live there and their images in GHCR).
- On your machine (Linux, macOS, or WSL): `git`, `gh` (logged in), `ssh`, `sops`, `age`,
  `ansible` and `python3-yaml`. `andamio init` checks them and tells you how to install
  anything missing.

## Quickstart

```bash
# 1. Create your own (private) copy of this repo: "Use this template" on GitHub, then
git clone git@github.com:<you>/<your-andamio>.git && cd <your-andamio>

# 2. Answer a few questions. Creates your config, an encryption key (age) and the
#    platform secrets, all encrypted. Touches no server.
bin/andamio init

# 3. Commit your encrypted configuration
git add -A && git commit -m "andamio: my server" && git push

# 4. Prepare the server: verifies its SSH fingerprint, installs your key (works whether
#    your provider gave you a key or a root password), creates your user, hardens it,
#    sets up the VPN and starts the platform. Safe to re-run: it resumes.
bin/andamio server
```

### Before `andamio server`: two checks at your provider

1. **Its firewall.** Azure, AWS, Oracle and Google Cloud (and some Hetzner or
   DigitalOcean setups) filter traffic before it reaches your VPS. Allow inbound
   **TCP** `<your SSH port>`, `80`, `443` and **UDP** `51820`, and keep `22` open until
   `andamio server` finishes. Otherwise, when SSH moves to your port, you're locked out.
   `andamio init` prints the exact ports at the end.
2. **The server's fingerprint.** `andamio server` shows it before the first connection.
   Check it from *inside* the server through a path that isn't the network: the web
   console of your VPS (Hetzner, DigitalOcean, Vultr, Linode, Contabo), *Run command* in
   Azure, or *Session Manager* in AWS. Run
   `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` there; it must match.

Then import `~/andamio-vpn/mi-pc.conf` into the WireGuard app (or show it as a QR code for
your phone with `qrencode -t ansiutf8 < ~/andamio-vpn/mi-pc.conf`).

## Deploy your first app

Your app, any language, needs a `Dockerfile`. Optionally:

- a stage named **`test`**: CI builds it before deploying; if it fails, nothing is deployed;
- an HTTP **health route** (e.g. `/healthz`) that returns 200 when the app is ready.

```bash
# Register an existing repo: creates its deploy key, the CI variables, a database
# and Redis user if you ask for them, and prints the CI workflow to add to your repo.
bin/homelab app create myapp --repo <you>/myapp --port 8000 --health /healthz

# Add the printed .github/workflows/ci.yml to your app repo, then
git push   # tests, scans, builds and deploys
```

Your app is at `https://myapp.example.com` (through the VPN, unless you passed `--public`).

Useful flags: `--public` (reachable from the internet), `--db` (PostgreSQL), `--redis`,
`--host <sub>` or `--host @` (root domain), `--mem 512m`.

### `apps/<app>/app.yml`

| Key | Meaning |
|---|---|
| `port` | Port your app listens on inside the container |
| `health` | HTTP path checked from the host before a new version takes traffic. Without it, the image's `HEALTHCHECK` is used; without either, "healthy" means running for 10 s without restarting |
| `access` | `vpn` (default) or `public` |
| `db`, `redis` | Your own PostgreSQL database/user and Redis user |
| `migrate` | `{ command: "python manage.py migrate" }` runs with your app image before each deploy |
| `worker` | `{ command: "...", heartbeat: false }`: a second process from the same image |
| `resources` | `mem`, `cpus`, `pids` limits |

### When Trivy blocks your image

Official base images usually ship their package manager (`npm`, `pip`, `setuptools`), which
brings its own vulnerabilities and isn't used in production. Remove it from your final
stage, for example `RUN pip uninstall -y pip setuptools` or
`RUN rm -rf /usr/local/lib/node_modules/npm`. If the findings are in your own dependencies,
update them.

## Optional modules

All in `ansible/group_vars/all.yml`:

| Setting | Values |
|---|---|
| `homelab_tls` | `http` (default: one Let's Encrypt certificate per app, any DNS provider), `cloudflare` (one wildcard certificate; needs the zone in Cloudflare and an API token) or `custom` (your own certificate, see below) |
| `homelab_forge` | `github` (default). Everything andamio needs from it goes through `bin/forge`; adding GitLab means implementing that one file plus its pipeline |
| `homelab_monitoring` | `auto` (default), `minimo` (~115 MiB: metrics) or `completo` (~670 MiB: + logs, Grafana with alerts, Uptime Kuma) |
| `homelab_backups` | `false` (default). `bin/andamio backups` turns it on: see below |
| `homelab_telegram` | `false` (default) or `true` with a bot token and chat id in `host/sops/telegram-env.sops` |

### Backups

```bash
bin/andamio backups
```

Asks where to store them (Backblaze B2 or any S3-compatible storage: AWS, Cloudflare R2,
Wasabi, MinIO), tests the destination from your server, runs the first backup right away
and then a restore test: it restores the dump into a temporary PostgreSQL and compares it
with production, without touching it. After that, every night at 03:30 UTC.

- restic encrypts everything on the server before upload: the storage provider never sees
  your data. The repository password is random and lives encrypted in your repo (sops).
- With B2, andamio can create the server's key **without delete permission**, limited to
  one bucket (it needs your master key once and doesn't keep it). Whoever takes over the
  server can't delete your backups.
- Kept: 7 daily, 4 weekly, 6 monthly.

### Your own certificate

With a certificate from a commercial CA, or a Cloudflare Origin Certificate, choose
`custom` in `andamio init`, or switch later:

```bash
bin/andamio certificado fullchain.pem private.key   # validates, then stores it (key encrypted with sops)
bin/andamio certificado                             # shows the current one and its expiry
```

It checks that the key matches, that the certificate covers `yourdomain` and `*.yourdomain`,
that it includes the intermediate chain, and how long it has left. Nobody renews it for
you: Grafana alerts 20 days before any certificate expires (Let's Encrypt ones too, in
case renewal breaks). Renewing is the same command with the new files.

A Cloudflare Origin Certificate is only trusted through Cloudflare's proxy. Your VPN-only
panels don't go through it, so browsers will reject it there. If your domain is already on
Cloudflare, `cloudflare` mode is free, renews itself and works for both.

## Security model, honestly

What it protects:
- **The server's surface:** only SSH (keys, custom port), HTTP/HTTPS and the VPN are open.
  andamio only publishes 80/443 (Traefik); internal services listen on localhost or on
  internal Docker networks. (Careful: a port you publish yourself with `-p` bypasses UFW.)
- **Apps' data from each other:** separate database and Redis users; an app can't read
  another app's tables or keys. Apps do share the proxy network.
- **The deploy path:** CI can only ask the server to deploy one app (a forced command
  per key), and only images that passed the scans.
- **Secrets:** encrypted in the repo with sops + age; the key never lives on the server.

What it doesn't:
- **One server.** No high availability; if the VPS is gone, you rebuild from the repo and
  your backups (there is a runbook and a restore drill).
- In `http` TLS mode, every app name, private ones included, appears in public
  certificate transparency logs. Use `cloudflare` mode if that matters to you.
- A compromised GitHub account can push code that gets deployed. Protect it with 2FA.

## How a deploy works

```
git push ─► GitHub Actions ─► gitleaks ─► Dockerfile "test" stage ─► build ─► Trivy ─► GHCR
                                                                                    │
VPS ◄── SSH with a key that can only run "deploy <this app>" ◄──────────────────────┘
 └─ pull image ─► migrations ─► start new version next to the old ─► health check
                                  └─ healthy: stop the old one   └─ failing: keep the old one, alert
```

## Design decisions

Every significant decision is written down, with its context, the alternatives and the
consequences, in [`docs/decisions/`](docs/decisions/) (in Spanish). A few that shaped the
project: immutable backups (0014), a declarative mini-PaaS (0015), CI quality and security
gates (0021), and apps in any language (0022).

## Roadmap

- [x] End-to-end test on a fresh VPS (Azure, 1 vCPU and 1 GB)
- [ ] The same test on more providers (Hetzner, DigitalOcean, Oracle, AWS)
- [ ] GitLab as well as GitHub (repos, image registry and pipeline)
- [ ] CLI in English
- [x] Guided backups (`andamio backups`)
- [ ] Guided Telegram alerts (`andamio telegram`)
- [ ] Preview environments per pull request

## License

[MIT](LICENSE) © 2026 Geovani Pérez Guerra
