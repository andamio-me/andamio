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
4. **Tests the restore:** loads the database backup into a temporary PostgreSQL and compares
   it with production, without touching it.

From then on, every night at 03:30 UTC.

## What's backed up

Your apps' databases (a consistent PostgreSQL dump), Redis, the platform's files and what's
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

## Restore

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
