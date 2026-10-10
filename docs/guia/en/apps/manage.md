---
title: Manage an app
description: List, see logs, stop, roll back, apply changes and delete.
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
