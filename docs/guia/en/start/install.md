---
title: Install
description: Get your machine ready and create your private copy of andamio.
---

## 1. The installer

On your machine (Linux, macOS or the Ubuntu terminal in WSL):

```bash
curl -fsSL https://raw.githubusercontent.com/Geovani29/andamio/main/install.sh | sh
```

It's short: read it first if you prefer. It does the same as this, by hand:

```bash
git clone https://github.com/Geovani29/andamio.git ~/andamio
~/andamio/bin/andamio setup
```

## 2. `andamio setup`

The first thing it asks is what you want to do:

- **Only lock down my VPS.** It installs just what's needed (git, ssh and Ansible), creates
  your copy of andamio **only on your machine** (for example `~/my-andamio`) and goes
  straight on to [`andamio security`](/en/docs/start/server/#only-lock-down-the-vps-andamio-security).
  No GitHub account or repos. If one day you want the platform, run `andamio setup` inside
  your copy: it connects it to GitHub (a new private repo, with what you've already done) and
  you go on with `andamio init`.
- **Full andamio.** What follows.

Runs once and asks before installing each thing:

1. Installs **git, gh, sops, age and Ansible** with their collections. sops is verified
   against its checksum.
2. Sets your git identity.
3. Logs you into GitHub (`gh auth login`) with an SSH key, and pins GitHub's official keys so
   nobody can impersonate it.
4. Creates **your private copy of andamio** from the template, in your account, and clones
   it (for example into `~/my-andamio`).
5. Installs the `andamio` command in `~/.local/bin`, to use it from any folder.

:::note
Your copy is **private** and it's yours: your server's configuration, its encrypted secrets
and your apps will live there. andamio's public repo is only the template.
:::

## 3. `andamio init`

Inside your copy:

```bash
cd ~/my-andamio
andamio init
```

Guided questions, one at a time, validated on the spot:

- your server's IP and domain;
- the name of the Linux user andamio creates for you on the server, and the SSH port you'll
  use (not 22);
- your GitHub user or organization;
- the HTTPS mode: `http` (Let's Encrypt, the default), `cloudflare` (wildcard via DNS) or
  `custom` (your own certificate), and your email for Let's Encrypt notices;
- the monitoring level: `auto`, `minimo` or `completo`.

It creates your configuration in `ansible/group_vars/all.yml`, an encryption key (age) that
lives **only on your machine** and the platform's secrets, encrypted. It doesn't touch any
server.

At the end it shows the ports to open in your provider's firewall. Push it:

```bash
git add -A && git commit -m "andamio: my server" && git push
```

:::caution[Your age key]
`~/.config/sops/age/keys.txt` is the only key that decrypts your secrets. Keep it in a
password manager: without it you can't rebuild your server.
:::

Continue with [Your server](/en/docs/start/server/).
