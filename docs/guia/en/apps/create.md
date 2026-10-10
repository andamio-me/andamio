---
title: Create an app
description: Register a repo of yours, in any language, and deploy it with a git push.
---

```bash
andamio app create myapp --repo your-user/myapp --health /healthz --public
```

You do this **once** per app. From then on, every `git push` to `main` of your app's repo
deploys it.

## What your app needs

- **A private GitHub repo.** While your copy of andamio is private, GitHub doesn't let a
  public repo use its pipeline; `app create` warns you before touching anything.
- **A `Dockerfile`.** That's the contract: with it, any language works. If it doesn't have
  one, andamio suggests one (see below).
- **To listen on `0.0.0.0`**, not `localhost`, on the port in `$PORT` (or your Dockerfile's
  `EXPOSE`).
- Optional, but recommended:
  - a **health route** that returns `200` when the app is ready (for example `/healthz`);
  - a **`test`** stage in your Dockerfile: the pipeline builds it before deploying, and if
    it fails nothing is deployed.

## If it has no Dockerfile

`app create` detects the language and suggests one ready for the pipeline:

| Detects | From |
|---|---|
| Node (npm, pnpm, yarn) | `package.json` |
| Python | `requirements.txt` or `pyproject.toml` |
| Go | `go.mod` |
| Static site | `index.html` |

The Dockerfile it generates has a `test` stage if it finds tests, a minimal final image
**without npm or pip** (so the vulnerability scan doesn't block it) and runs **without
root**. Before pushing anything it shows you:

```
Your app will start with:  uvicorn main:app --host 0.0.0.0 --port $PORT
(it listens on port 8000: andamio passes it $PORT=8000)
Start it like this?
```

If your app starts differently, type your command. If you answer just a number, it's taken
as the port. It's yours: change it as needed afterwards.

## What `app create` does

1. Checks your app's repo and, if needed, generates the Dockerfile.
2. Creates `apps/myapp/app.yml` in your copy, its encrypted secrets and a **deploy key**
   that can only deploy that app.
3. If you asked for `--db` or `--redis`, prepares its user and database.
4. Pushes your copy and applies it on the server (asks for your sudo password).
5. Offers to push to your app's repo what it's missing: the Dockerfile and
   `.github/workflows/andamio.yml`.
6. That push is the **first deploy**, and it follows it in your terminal: secrets, tests,
   scan, image and deploy. If it fails, it shows the step, its last log lines and a hint.

## Options

| Option | What it does |
|---|---|
| `--repo owner/repo` | Your app's repo |
| `--public` | Reachable from the internet. Without it, **VPN only** |
| `--health /path` | Health route: the new version has to answer `200` before getting traffic |
| `--port 3000` | Your app's port (default: the Dockerfile's `EXPOSE`) |
| `--db` | Its own PostgreSQL database and user (`DATABASE_URL`) |
| `--redis` | Its own Redis user, limited to its keys (`REDIS_URL`) |
| `--host api` | Another subdomain: `api.yourdomain.com`. `--host @` is the root domain |
| `--domain app.yourcompany.com` | A domain of your own, besides yours |
| `--cors https://myapp.vercel.app` | Lets that frontend call your app |
| `--mem 512m` | Memory limit (default 256m) |

See [Domains and URLs](/en/docs/apps/domains/) and [Backend only](/en/docs/apps/backend-only/).

## `apps/myapp/app.yml`

Your app's definition, in your copy. `app create` generates it; you can edit it and apply
with `andamio app apply myapp`.

| Key | Meaning |
|---|---|
| `port` | The port your app listens on inside the container |
| `health` | HTTP path checked before a new version gets traffic. Without it, the image's `HEALTHCHECK` is used; with neither, "healthy" = 10 s running without restarting |
| `access` | `vpn` (default) or `public` |
| `db`, `redis` | Its own PostgreSQL database and user, and its Redis user |
| `migrate` | `{ command: "python manage.py migrate" }`: runs with your app's image before each deploy |
| `worker` | `{ command: "..." }`: a second process with the same image |
| `resources` | `mem`, `cpus` and `pids` limits |
