---
title: Your server
description: andamio server hardens your VPS and starts the platform.
---

```bash
andamio server
```

You can run it as many times as you want: it resumes where it stopped, and it's also how you
re-apply everything after a change.

## Only lock down the VPS: `andamio security`

If for now you only want the VPS safe (or you'll set up the platform later):

```bash
andamio security
```

If you come from `andamio setup` choosing "only lock down my VPS", it starts by itself. It asks:

- the VPS's **IP**;
- **where it is** (Azure, AWS, Hetzner…) and the **user your provider gave you** (the one that
  already exists: `azureuser`, `ubuntu`, `root` or the one you picked when creating it);
- **your new user**, different from the provider's (if you type the same, it's refused right
  away). The provider's keeps existing and works on its web console, but can no longer log
  in over SSH;
- the **new SSH port**: Enter takes a random one. If your provider has a firewall, that's
  where you open this same number (andamio tells you if you forget);
- the **name to log in with** (`ssh <name>`): it suggests one that says which server it is.

And it does the same as `andamio server`'s lockdown, without installing anything else:

1. Creates your SSH key if you don't have one, and warns you it'll be your only way in (keep it).
2. Checks the server's fingerprint and installs your key with the password or `.pem` your
   provider gave you (once).
3. **Before moving SSH, it tests that the new port reaches the server.** If your provider's
   firewall blocks it, it stops and tells you where to open it: you don't get locked out.
   Open it and run the command again: it resumes where it stopped.
4. Creates your user and, in the same step, turns off passwords and root and turns on the firewall.
5. Checks it from outside: root and the other users get refused with a password, and `22`
   no longer answers.
6. Automatic patches, strict sshd and fail2ban.
7. Applies the **pending patches** your provider's image ships with right away and, if they
   need a reboot (the kernel), offers to do it now: nothing runs on the server yet.
8. The server's security check, all in view.

Safe to repeat: what's done is skipped.

When you want the platform: if your copy is local only (`setup` made it when you chose "only
lock down"), `andamio setup` inside it connects it to GitHub. Then `andamio init` fills in
what's missing (domain, repo, HTTPS) without asking the above again, and `andamio server`.

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
4. **Hardens it:** key-only SSH on your port, no root login and its password locked, UFW
   firewall (all three as soon as your user exists, before going on), fail2ban, automatic
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
memory only (never on disk). In the panel, **Settings → Sudo password** picks how long: 15 min,
1 h, 4 h or 8 h (a preference of your machine, in `~/.config/andamio`), and **Forget now** wipes
it. In the terminal, `andamio forget` does the same; `ANDAMIO_SUDO_MINUTES` overrides the setting
(`0` turns remembering off).
