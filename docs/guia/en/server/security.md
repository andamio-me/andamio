---
title: Security
description: What andamio sets up on your server, how to check it and its limits.
---

## What's done for you

Without asking, `andamio server` leaves (and `andamio security`, if you only want the VPS
locked down, leaves the same except Docker, Traefik and the VPN; see
[Your server](/en/docs/start/server/#only-lock-down-the-vps-andamio-security)):

- **Your own user**, with sudo and a password. Root can't log in, and its password (the one
  your provider sends) is locked, on the web console too.
- **Key-only SSH**, on a port other than 22, with few tries per connection and no
  forwarding a server doesn't use.
- **UFW firewall:** only your SSH port, HTTP/HTTPS and the VPN get in.
- **Protected from the first minute:** SSH passwords go off and the firewall goes on as soon
  as your user exists, not at the end; the VPS isn't exposed even if something fails
  halfway.
- **fail2ban:** an IP that keeps trying SSH gets blocked (1 hour, longer if it comes back).
- **Automatic security patches**, the kernel with hardened network settings, and snapd and
  unused services removed.
- **Docker** with rotated logs; the socket only through a read-only proxy. A published port
  stays on `127.0.0.1` unless you say otherwise, and no container can gain privileges with
  `sudo` or `su`.
- **Traefik** with automatic HTTPS, security headers and a per-IP request limit (100 per
  second, 300 at once: `andamio_rate_average` and `andamio_rate_burst`).
- **WireGuard VPN:** private things answer only through it.

And every new app gets:

- its own PostgreSQL user and database, and its Redis user limited to its keys: one app
  can't read another's tables or keys;
- a deploy key that can only run that app's deploy (it doesn't open a shell);
- secrets encrypted with sops and age, with the key **only on your machine**;
- images checked (leaked secrets, tests, vulnerabilities) before they reach your server.

## `andamio status`

```bash
andamio status
```

A security and health check. **It changes nothing.**

- **From the server:** SSH (keys only, no root, your port, fail2ban), firewall, automatic and pending
  patches, disk, clock, last backup, certificates, containers with problems, isolation
  (privileged containers, the Docker socket, published ports that bypass the firewall) and
  the VPN.
- **From the internet**, from your machine: whether any port answers that shouldn't (Docker
  can bypass UFW: only a test from outside tells the truth), that `22` is closed, and the
  certificate and the HTTP → HTTPS redirect as a visitor sees them.

```
  ✓ SSH           Keys only (no passwords)
  ✓ Firewall      UFW active, incoming denied by default
  ! Patches       12 security updates pending
    → they arrive every night; to apply them now: sudo apt upgrade on the server
  ✓ Internet      Port 22 is closed (SSH only on yours)

14 good · 1 warning · 0 problems
```

Each problem comes with its fix. It exits with code 1 if there are problems, so it works in
scripts.

## What it doesn't protect

- **A single server.** No high availability: if the VPS disappears, it's rebuilt from your
  repo and your [backups](/en/docs/server/backups/).
- **Your apps' names.** In the `http` HTTPS mode, every name (private ones too) shows up in
  the public certificate logs. Use the `cloudflare` mode if that matters to you.
- **Your GitHub account.** Whoever controls it can push code that gets deployed. Protect it
  with 2FA.
- **Ports you publish yourself.** A Docker `-p 0.0.0.0:...` bypasses the firewall (without the IP it
  stays local). `andamio status` detects it.
- **The network between apps.** Apps share the proxy network; what isolates them are the
  database and Redis users.
