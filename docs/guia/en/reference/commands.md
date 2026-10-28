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
| `andamio security` | Only locks down the VPS: your key, your user, SSH without passwords or root, firewall and fail2ban. Safe to repeat |
| `andamio server` | Sets up the VPS: user, SSH, firewall, VPN and the platform. Safe to repeat: the hardening only re-runs if it changed (or every 7 days); `--full` forces it |
| `andamio backups` | Daily, encrypted, off-server backups (B2 or S3), tested |
| `andamio backups now\|list` | A backup right now / the ones there are (date, duration, size) |
| `andamio alerts` | Phone notice (ntfy, no account) if a container goes down or the disk fills up |
| `andamio telegram [test\|off]` | Telegram notices, guided: your bot, your chat (no IDs to look up), encrypted and applied |
| `andamio alerts --ntfy new\|URL\|off` | Same with no questions: new topic on ntfy.sh, your own topic, or remove ntfy |
| `andamio alerts test` | A test notice through every active channel (ntfy and Telegram) |
| `andamio timezone [<zone>]` | Your scheduled tasks' time zone: see it or change it (`America/New_York`) |
| `andamio services [postgres\|redis\|mariadb] [--mem 2g] [--cpus 1] [--engine valkey] …` | Shared PostgreSQL and Redis: how they're doing, and their memory, CPU and settings. See [PostgreSQL and Redis](/en/docs/server/services/) |

## Your apps

| Command | What it does |
|---|---|
| `andamio app create <app> --repo <owner/repo>` | Registers it; from then on, every `git push` to `main` deploys it. Options in [Create an app](/en/docs/apps/create/#options) |
| `andamio app list` | All of them, with URL, access and status |
| `andamio ui` | [Panel in your browser](/en/docs/apps/panel/): your server's plan, apps, live logs and actions (runs on your machine) |
| `andamio app info <app>` | Its configuration and how it's doing now: status, RAM and CPU in use, version |
| `andamio app set <app> [--mem 512m] [--cpus 1] [--port 8080] [--health /path] [--public\|--vpn]` | Change it without editing `app.yml`: a restart, no deploy |
| `andamio app set <app> [--db-connections 20] [--db-timeout 30s]` | Its database limits: connections and time per query. See [PostgreSQL and Redis](/en/docs/server/services/#limit-an-app) |
| `andamio app logs <app> [--worker]` | Live logs (of the web, or of its worker) |
| `andamio app restart <app>` | Restarts its containers with the same version |
| `andamio app deploy <app>` | Deploys main's latest successful build again, no push |
| `andamio app create <app> --repo … --branch production` | Deploys from another branch (without `--branch`: the repo's main one) |
| `andamio app create <app> --repo … --dir backend [--path /api]` | One of several apps in a repo ([Front and back in one repo](/en/docs/apps/monorepo/)) |
| `andamio app source <app> [--dir …] [--context .\|-] [--watch-add …] [--watch-rm …]` | Where it comes from: its folder and which paths trigger its deploy |
| `andamio app secret set <app> <KEY> [--later]` | Creates or changes a variable (the value is asked hidden) |
| `andamio app secret import <app> <.env\|-> [--later]` | Several at once from a `.env` (or stdin): one commit, one restart |
| `andamio app secret rm <app> <KEY>` | Removes it |
| `andamio app secret list <app>` | Names only |
| `andamio app apply [<app>]` | Applies what's pending on the server; retries a failed deploy |
| `andamio app domain add\|rm\|list <app> [domain]` | A domain of your own, besides yours |
| `andamio app cors add\|rm\|list <app> [origin]` | Frontend hosted elsewhere (Vercel…) |
| `andamio app volume add\|rm\|list <app> [/data]` | Folder that persists across deploys (backed up) |
| `andamio app cron add <app> "<schedule>" "<command>" [--name x]` | [Scheduled task](/en/docs/apps/manage/#scheduled-tasks), in your time; notifies if it fails |
| `andamio app cron list\|run\|rm <app> [task]` | See them (next and last run), run one now, remove it |
| `andamio app cron edit <app> <task> [--schedule '…'] [--command '…']` | Change its schedule or command |
| `andamio app cron runs <app> <task>` | Its last 5 scheduled runs, with their output |
| `andamio app stop\|start <app>` | Turn it off without deleting anything / back on |
| `andamio app rollback <app> [<commit>]` | Back to the previous deploy, or to that commit |
| `andamio app restore <app> [<backup>\|latest]` | Its database and folders, as in that backup (the current ones are saved first) |
| `andamio app sql <app> ["SELECT …"]` | Its database, read-only: `psql` or one query |
| `andamio app revert <app> <commit>` | Undoes a change to its configuration (RAM, domains, tasks…) with a new commit |
| `andamio app destroy <app>` | Delete it (backs up its database and folders first) |
| `andamio app ci-update [<app>]` | Your apps' pipeline, to the current andamio version |
| `andamio app retry <app>` | Retries its last deploy, if it failed (no new push) |

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
