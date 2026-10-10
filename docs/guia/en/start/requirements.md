---
title: Requirements
description: The server, domain, account and machine you need before starting.
---

## A VPS

- **Ubuntu 24.04**, freshly created. andamio sets it up from scratch.
- **1 GB of RAM** minimum; 2 GB or more is comfortable. Images are built on GitHub Actions,
  not on your server, so a small one is enough.
- Its **public IP**, and access as root or as your provider's initial user (with a password
  or the `.pem` key they gave you).

Tested end to end on fresh Azure VPSs (1 vCPU and 1 GB). Other providers running Ubuntu
24.04 should work the same; testing on Hetzner, DigitalOcean, Oracle and AWS is on the
roadmap.

## A domain

With **two DNS `A` records** pointing to your VPS's IP:

| Name | Type | Value |
|---|---|---|
| `yourdomain.com` | A | your VPS's IP |
| `*.yourdomain.com` | A | your VPS's IP |

The `*` makes every new app (`blog.yourdomain.com`, `api.yourdomain.com`…) point to your
server without touching DNS again. It can be a subdomain (`lab.yourdomain.com` and
`*.lab.yourdomain.com`) if the main domain is already used elsewhere.

:::tip[Cloudflare?]
If you use Cloudflare's proxy (the orange cloud), turn it off on those two records (grey
cloud) so Let's Encrypt can issue the certificates, or use the `cloudflare` HTTPS mode. See
[HTTPS and certificates](/en/docs/server/certificate/).
:::

## A GitHub account

That's where your private copy of andamio, your apps' repos, their images (on GHCR) and the
pipeline that builds them live. GitLab is on the roadmap.

## Your machine

- **Linux** (Ubuntu or Debian), **macOS**, or **Windows with WSL**.
- On Windows: `wsl --install` in PowerShell, then you work inside Ubuntu.
- You don't need to install anything else by hand: `andamio setup` installs git, gh, sops,
  age and Ansible, asking first.
