---
title: Commands
description: Every andamio command, in the order you'll use them.
---

`andamio help` shows this list in your terminal; `andamio help <command>`, the details of
one. Spanish names work too: `servidor`, `estado`, `certificado`, `olvidar`.

## Getting started (once)

| Command | What it does |
|---|---|
| `andamio setup` | Gets your machine ready: installs git, gh, sops, age and Ansible, and creates your private copy |
| `andamio init` | Guided questions: configuration, encryption key and secrets. Local only |
| `andamio server` | Sets up the VPS: user, SSH, firewall, VPN and the platform. Safe to repeat |
| `andamio backups` | Daily, encrypted, off-server backups (B2 or S3), tested |
| `andamio alerts` | Phone notice (ntfy, no account) if a container goes down or the disk fills up |

## Your apps

| Command | What it does |
|---|---|
| `andamio app create <app> --repo <owner/repo>` | Registers it; from then on, every `git push` to `main` deploys it. Options in [Create an app](/en/docs/apps/create/#options) |
| `andamio app list` | All of them, with URL, access and status |
| `andamio app info <app>` | Its configuration and how it's doing now: status, RAM and CPU in use, version |
| `andamio app set <app> [--mem 512m] [--cpus 1] [--port 8080] [--health /path] [--public\|--vpn]` | Change it without editing `app.yml`: a restart, no deploy |
| `andamio app logs <app>` | Live logs |
| `andamio app secret set <app> <KEY> [--later]` | Creates or changes a variable (the value is asked hidden) |
| `andamio app secret rm <app> <KEY>` | Removes it |
| `andamio app secret list <app>` | Names only |
| `andamio app apply [<app>]` | Applies what's pending on the server; retries a failed deploy |
| `andamio app domain add\|rm\|list <app> [domain]` | A domain of your own, besides yours |
| `andamio app cors add\|rm\|list <app> [origin]` | Frontend hosted elsewhere (Vercel…) |
| `andamio app volume add\|rm\|list <app> [/data]` | Folder that persists across deploys (backed up) |
| `andamio app stop\|start <app>` | Turn it off without deleting anything / back on |
| `andamio app rollback <app>` | Back to the previous deploy |
| `andamio app destroy <app>` | Delete it (backs up its database and folders first) |
| `andamio app ci-update [<app>]` | Your apps' pipeline, to the current andamio version |

## Day to day

| Command | What it does |
|---|---|
| `andamio status` | Security and health check, from the server and from the internet. Changes nothing |
| `andamio update [--check]` | Brings in andamio's improvements and patches, never touching yours |
| `andamio certificate [cert key]` | Your own HTTPS certificate: show or replace |
| `andamio server` | Also re-applies everything |
| `andamio use [folder\|domain]` | With several servers: which copy `andamio` uses outside their folders |
| `andamio forget` | Wipes your remembered sudo password now |

## Environment variables

| Variable | What it does |
|---|---|
| `ANDAMIO_LANG` | `es` or `en`. If unset, follows `LANG` |
| `ANDAMIO_SUDO_MINUTES` | Idle minutes your sudo password is remembered (15 by default; `0` = never) |
| `ANDAMIO_VERBOSE` | `1` shows Ansible's full output instead of the summary |
