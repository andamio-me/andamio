---
title: Your server
description: andamio server hardens your VPS and starts the platform.
---

```bash
andamio server
```

You can run it as many times as you want: it resumes where it stopped, and it's also how you
re-apply everything after a change.

## Before: two checks at your provider

1. **Its firewall.** Azure, AWS, Oracle and Google Cloud (and some Hetzner or DigitalOcean
   setups) filter traffic before it reaches your VPS. Open inbound **TCP** for your SSH
   port, `80` and `443`, and **UDP** `51820`. Keep `22` open until `andamio server` finishes:
   otherwise you're locked out when SSH moves to your port.
2. **The server's fingerprint.** `andamio server` shows it before the first connection.
   Check it from *inside* the server through a path that isn't the network: your VPS's web
   console, *Run command* on Azure or *Session Manager* on AWS:

   ```bash
   ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   ```

   It has to match. If it doesn't, stop: someone may be in the middle.

## What it does, step by step

1. **Gets into the server** with what your provider gave you: a root password or the `.pem`
   key. It asks which provider you use, to know its initial user.
2. **Installs your SSH key** and verifies the fingerprint.
3. **Creates your user** for operations and asks for a new sudo password (twice).
4. **Hardens it:** key-only SSH on your port, no root login, UFW firewall, automatic
   security patches and unused services removed.
5. **Installs Docker** (rotated logs; the socket only through a read-only proxy).
6. **Sets up the WireGuard VPN** and generates your first device's configuration.
7. **Prepares the key** the server uses to pull your copy of andamio (read-only, that repo
   only).
8. **Starts the platform:** Traefik with HTTPS, PostgreSQL, Redis and monitoring.

When it's done, close `22` in your provider's firewall.

## The VPN

Your first device is in `~/andamio-vpn/mi-pc.conf`. Import it in the WireGuard app; for your
phone, show it as a QR code:

```bash
qrencode -t ansiutf8 < ~/andamio-vpn/mi-pc.conf
```

Private apps (the ones you create without `--public`) and the admin tools answer **only**
with the VPN connected.

## Check that it's right

```bash
andamio status
```

Checks the server's security and health from inside and from the internet, and tells you how
to fix each problem. See [Security](/en/docs/server/security/).

## Your sudo password

Commands that change the server ask for it **once** and remember it for 15 idle minutes, in
memory only (never on disk). `andamio forget` wipes it right away; `ANDAMIO_SUDO_MINUTES=0`
turns remembering off.
