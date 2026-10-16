---
title: Front and back in one repo
description: Several apps in one repo (frontend/, backend/), each with its folder, its deploy and its key.
---

If your repo has the front end and back end together (a monorepo), each folder deploys as
its own app:

```text
my-project/
├── frontend/     → app web
├── backend/      → app api
└── packages/     (shared code, optional)
```

```bash
andamio app create web --repo your-user/my-project --dir frontend --host myapp --public
andamio app create api --repo your-user/my-project --dir backend --host myapp --path /api \
  --public --db --health /api/health
```

The front end lives at `https://myapp.yourdomain.com` and the back end at
`https://myapp.yourdomain.com/api`: **the same domain, no CORS**, and cookies just work. If
you'd rather have the back end on its own subdomain, use `--host api` without `--path` (and
`--cors` for the front end).

## What `--dir` does

- **Its Dockerfile** lives in that folder. If it has none, andamio proposes one (like for an
  app at the root) and the pre-check looks at that folder.
- **Its own pipeline**: `.github/workflows/andamio-<app>.yml`. It only runs when something in
  its folder changes: a front-end change doesn't redeploy the back end.
- **Its own image** (`ghcr.io/your-user/<app>`) and **its own deploy key**
  (`DEPLOY_SSH_KEY_<APP>` in the repo). Each key can only deploy its app.
- Rollback, **Deploy now**, retry and the panel's deploy list only see that app's runs.

## Shared code

If both apps use a common folder (`packages/`) or the root lockfile (pnpm or npm
workspaces), the image is built from the root with the folder's Dockerfile:

```bash
andamio app create api --repo your-user/my-project --dir backend --context . --watch packages/
```

| Option | What it does |
|---|---|
| `--context .` | Builds from the repo's root (the Dockerfile is still `backend/Dockerfile`; its `COPY`s are relative to the root). It also redeploys when the root manifests change: `package.json`, the lockfiles, `pnpm-workspace.yaml` |
| `--watch packages/` | Besides its folder, a change there also deploys it. A folder (`packages/`), a file (`tsconfig.base.json`) or a pattern (`config/*.yml`). Repeat it for several |

## Changing it later

```bash
andamio app source api                          # where it comes from: repo, folder, paths
andamio app source api --watch-add packages/    # another path that triggers its deploy
andamio app source api --watch-rm packages/
andamio app source api --context .              # build from the root (- to go back to its folder)
andamio app source api --dir services/api       # it moved folders
```

It rewrites its pipeline in the app's repo and saves it in `app.yml`; it doesn't touch the
server. Changing the folder or where it's built from deploys; adding or removing paths doesn't.
In the panel: **Settings → Code**.

## Paths

With `--path /api`, Traefik sends everything starting with `/api` to that app and the rest
to the front end. The path **isn't stripped**: your back end gets `/api/users`, so its routes
carry the prefix (the usual in Express, FastAPI, Django and friends).

Two apps can't have the same host and the same path.

## In the panel

In **New app**, when you pick a repo with several folders, the panel shows them and you pick one:

- First the ones the repo declares as part of its monorepo (pnpm, npm or yarn workspaces,
  `lerna.json`, `go.work`), then the ones with a Dockerfile or a project, up to 3 levels deep.
- Each one says what it is: **front end** (Next.js, Vite, Astro…), **API** (Express, NestJS,
  FastAPI, Django…), **worker** (Celery…) or **site**.
- **Libraries** (packages that only export code, like `packages/ui`) go apart, under "Show N
  libraries": they aren't deployed on their own.
- Folders inside an app (`frontend/public`, `backend/src`) don't show up: they're part of it.
- With many folders there's a search box, and **Another folder** reviews any path you type.

From the terminal, if the repo has several apps and its root isn't one, `andamio app create`
tells you which ones and asks for `--dir`.

If another app already comes from that repo, the panel offers to use its same address with the
`/api` path. In the menu, apps from the same repo show up together, with their folder next to them.
