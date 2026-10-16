---
title: Backups
description: Daily, encrypted, off-server backups, with a restore test.
---

```bash
andamio backups
```

Without backups, your data only lives on the VPS. This command sets them up, guided:

1. **Where to store them:** Backblaze B2 or any S3-compatible storage (AWS, Cloudflare R2,
   Wasabi, MinIO).
2. **Tests the destination** from your server.
3. **Runs the first backup** right away.
4. **Tests the restore:** loads the databases' backup into a temporary PostgreSQL (and a
   temporary MariaDB, if some app uses it) and compares it with production, without touching
   it. If a dump doesn't load or is missing databases or tables, the test fails.

From then on, every night at 03:30 UTC.

## What's backed up

Your apps' databases (a consistent dump of PostgreSQL and, if some app uses it, MariaDB), Redis, the platform's files and what's
needed to rebuild the server: the SSH configuration, the VPN and the server's secrets.

## How they're protected

- **Encrypted on your server before uploading**, with restic: the provider never sees your
  data. The repository password is random and lives encrypted in your copy (sops).
- **Undeletable from the server**, with B2: andamio can create the server's key **without
  delete permission**, limited to one bucket. It needs your master key once and doesn't keep
  it. Whoever takes your server can't delete your backups.
- It keeps **7 daily, 4 weekly and 6 monthly** backups.

## Check them

`andamio status` tells you when the last backup ran and whether it worked. With Telegram on,
it notifies you every night.

## Back up now and see the ones there are

```bash
andamio backups now     # the same as every night, with its output live
andamio backups list    # the ones there are: date, how long it took and size
```

In the [panel](/en/docs/apps/panel/), **See backups** shows the same.

## Restore one app

To take a single app back to an earlier day (its database and folders) without touching the
rest: `andamio app restore <app> <backup>`. See [Managing apps](/en/docs/apps/manage/#restore-from-a-backup).

## The archive of deleted things

Before deleting an app (`andamio app destroy`) or restoring it, andamio saves what it had in
`/srv/andamio/archive/`: its database and folders. That folder is included in the daily backup,
and **anything older than 90 days is deleted by itself** in each night's backup: by then it's in
the monthly backups, which last 6 more months. In the panel, **Backups → Archive** shows what's
there, how much it takes and when each item goes.

The days are set in your configuration (`andamio_archive_days: 90`; with `0`, nothing is deleted).

Deleting an app doesn't take it out of the backups that already exist: it stays in them until the
retention deletes them (7 daily, 4 weekly, 6 monthly). That way an accidental delete can be
undone.

## Restore the whole server

If the server disappears:

1. Create a new VPS and point DNS to its IP (change `andamio_server_ip` in your
   configuration).
2. `andamio server`.
3. Restore the last backup on the server:

```bash
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic restore latest --tag andamio --target /'
```

4. `andamio server` again, so everything starts with the restored data.

The full guide is in your copy: `docs/runbooks/restaurar-backup.md`.
