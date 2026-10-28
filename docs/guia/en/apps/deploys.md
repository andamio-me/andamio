---
title: Deploys
description: What happens, in order, every time you git push to main.
---

Every `git push` to `main` of your app's repo deploys it. Like this:

```
git push ─► GitHub Actions ─► gitleaks ─► "test" stage ─► build ─► Trivy ─► GHCR
                                                                          │
your VPS ◄── SSH with a key that can only run "deploy <this app>" ◄───────┘
  └─ pulls the image ─► migrations ─► new version next to the old ─► health check
                                         └─ healthy: stops the old  └─ fails: old keeps running
```

## Step by step

1. **Secrets.** gitleaks looks for keys and tokens that slipped into the code. If it finds
   one, it stops.
2. **Tests.** Builds your Dockerfile's `test` stage, if there is one, in whatever language.
   If it fails, nothing is deployed.
3. **Image and scan.** Builds the image and Trivy checks it against known vulnerabilities. A
   vulnerable image never reaches the registry.
4. **Publish.** The image goes to GHCR (GitHub's registry), private.
5. **Its own key.** The pipeline reaches your server with a key that can only run that
   app's deploy. It doesn't open a shell.
6. **Migrations.** If your app defines them (`migrate` in `app.yml`), they run before what's
   in production changes.
7. **New version alongside.** Starts next to the current one and has to pass its health
   check: your `--health` route, or the image's `HEALTHCHECK`, or 10 s without restarting.
8. **The switch.** Only then is the old one stopped. If something failed, the old one keeps
   running and the pipeline tells you why: see [When something fails](/en/docs/apps/failures/).
9. **Cleanup.** Only the new image and the previous one stay on the server; the rest are
   removed so the disk doesn't fill up (they stay on GHCR: `andamio app rollback` pulls them again).

Images are built on GitHub Actions, never on your VPS: that's why a small server is enough.

## Build secrets

Some secrets are only needed **to build** the image, not to run it: a private npm package's
token, Sentry's for uploading source maps. Those go in your app repo's *Secrets* on GitHub,
and are named in its workflow:

```yaml
# .github/workflows/andamio.yml
    with:
      build_secrets: NPM_TOKEN SENTRY_AUTH_TOKEN
    secrets:
      ANDAMIO_SECRETS: ${{ toJSON(secrets) }}   # already there
```

And in your Dockerfile:

```dockerfile
RUN --mount=type=secret,id=NPM_TOKEN NPM_TOKEN=$(cat /run/secrets/NPM_TOKEN) npm ci
```

BuildKit mounts each one only during that `RUN`: it never stays in an image layer. Secrets
your app reads **while running** go through
[`andamio app secret`](/en/docs/apps/secrets/).

## If Trivy blocks your image

Official base images usually ship their package manager (`npm`, `pip`, `setuptools`), with
its own vulnerabilities, and it isn't used in production. Remove it from the final stage:

```dockerfile
RUN pip uninstall -y pip setuptools
# or
RUN rm -rf /usr/local/lib/node_modules/npm
```

If the findings are in your dependencies, update them. The Dockerfiles andamio generates
already come this way.

## Bring your apps' pipeline up to date

Each app's pipeline is pinned to an andamio version (a SHA in its
`.github/workflows/andamio.yml`): that way an andamio update never changes how an app
deploys without warning. To bring the pipeline's improvements (the error hints, for
example) to your existing apps:

```bash
andamio app ci-update          # all of them
andamio app ci-update myapp    # one
```

By default it doesn't deploy: the improvements are used on each app's next `git push`. If
you answer yes, it deploys each one right away.

## See the logs

```bash
andamio app logs myapp
```

Live logs of the container that's in production.
