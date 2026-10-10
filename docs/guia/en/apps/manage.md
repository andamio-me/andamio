---
title: Manage an app
description: List, see details, change resources, scheduled tasks, see logs, stop, roll back, apply changes and delete.
---

## See your apps

```bash
andamio app list
```

```
APP          URL                                ACCESS  STATUS
blog         https://blog.yourdomain.com        public  Up 3 hours (healthy)
panel        https://panel.yourdomain.com       vpn     Up 2 days (healthy)
```

## See one app

```bash
andamio app info myapp
```

```
  myapp  ● running, started 2 h ago  v 8e71e29
  URL       https://myapp.yourdomain.com  (public)
  Repo      your-user/myapp
  Port      3000   health /healthz
  RAM       256m   using 74 MiB
  CPU       0.5   using 0.30%
  Data      PostgreSQL
  Secrets   ANTHROPIC_API_KEY
```

What its `app.yml` says and how it's doing on the server right now. Secrets: names only.

## Change RAM, CPU, port or access

```bash
andamio app set myapp --mem 512m             # or several at once: --mem 512m --cpus 1
andamio app set myapp --port 8080 --health /healthz
andamio app set myapp --public               # or --vpn: only from your VPN
```

It shows you the change (`resources.mem: 256m → 512m`), asks and applies it: a restart with the
same image, no deploy. If you change the port, your app has to listen on the new one; if you
changed the code for that, `git push` (that deploys).

## Live logs

```bash
andamio app logs myapp
```

## Stop and start

```bash
andamio app stop myapp     # turns it off without deleting anything: data, database, secrets and domain stay
andamio app start myapp    # turns it back on
```

A stopped app stays stopped even if you re-apply the server, and a `git push` doesn't deploy
it until you `start` it. It frees its memory and CPU.

## Roll back

```bash
andamio app rollback myapp
```

Goes back to the previous successful deploy.

## Apply changes

```bash
andamio app apply myapp
```

Applies on the server whatever is pending for that app (variables saved with `--later`,
manual changes to `app.yml`), with a single restart. It only runs that app's tasks: it
takes seconds.

## Persistent folders

A new container starts empty on every deploy: whatever your app stores on disk (uploads, a
SQLite database) is lost. For what must last, a persistent folder:

```bash
andamio app volume add myapp /data       # or when creating it: --volume /data
andamio app volume list myapp
andamio app volume rm myapp /data        # stops mounting it; the files stay on the server
```

- It lives on the server in `/srv/andamio/data/apps/myapp/`, and **is in the daily backup**.
- andamio gives it to the user your image runs as: your app can write even if it runs
  without root.
- The app's web and worker see the same folder.
- `app destroy` archives it (in `/srv/andamio/archive/`) before deleting it.

:::tip
For write-heavy data or several processes at once, `--db` (PostgreSQL) is better: a SQLite
database in a persistent folder works, but the backup copies the file as is.
:::

## Scheduled tasks

Something that runs by itself every so often: clean up old data, send a report, sync.

```bash
andamio app cron add myapp "0 3 * * *" "python cleanup.py"          # every day at 3:00
andamio app cron add myapp "*/15 * * * *" "node sync.js" --name sync # every 15 minutes
andamio app cron list myapp       # schedule, next run and how the last one went
andamio app cron run myapp sync   # run it now and see its output (to try it)
andamio app cron rm myapp sync
```

- The schedule is cron's: `minute hour day month weekday`. `*/15`, `1-5`, `0,30` and the
  shortcuts `@hourly`, `@daily`, `@weekly`, `@monthly` all work.
- **In your time**, not the server's (UTC): the first time, andamio takes your machine's time
  zone and asks you to confirm it (`andamio_timezone` in your configuration).
- It runs with **the same as your app**: its image, secrets, database, folders and RAM and CPU
  limits, in a separate container that's removed when it ends. It gets no traffic.
- **If it fails, you get a phone notice** (with [`andamio alerts`](/en/docs/server/monitoring/#phone-alerts)),
  with the last lines of its output: once, and again when it works again. Past one hour,
  it's stopped.
- If the server was off at that time, it runs when it boots. If it's still running when its
  next time comes, it doesn't double up. A stopped app doesn't run its tasks.
- Without `--name`, the name comes from the command (`python cleanup.py` → `cleanup`).

:::note
The command runs as is inside the image. If it uses `&&`, `|`, `>` or `$VARIABLE`, it goes
through `sh -c`: distroless images (like the one andamio generates for Go) have no `sh`, so
there use a plain command (`/server cleanup`).
:::

## Delete it

```bash
andamio app destroy myapp
```

It asks you to type its name to confirm, and before deleting it backs up its database and
archives its persistent folders. It removes its container, its configuration, its deploy key,
its database, its Redis user and its folders.

The app's repo and its images on GHCR stay on GitHub: delete them yourself if you no longer
want them.

## Resources

By default each app gets 256 MB of RAM and half a CPU. To change it, in
`apps/myapp/app.yml`:

```yaml
resources:
  mem: 512m
  cpus: 1
  pids: 200
```

And `andamio app apply myapp`.
