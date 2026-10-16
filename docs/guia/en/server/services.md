---
title: PostgreSQL, MariaDB and Redis
description: The databases and the Redis your apps share, how much they use and how to tune them.
---

Your apps with `--db` or `--redis` don't each get their own database server: they share one
**PostgreSQL** and one **Redis**, and each app has its own user. In PostgreSQL, its own database
(it can't see the others); in Redis, only its own keys (`myapp:…`). On a small VPS that saves a
lot of memory: one PostgreSQL per app would be hundreds of MB each.

That's why there are two levels of settings: the **service's**, which apply to every app, and
**each app's**, which limit it so it doesn't hog what's shared.

## See how they're doing

```bash
andamio services
```

```
==> PostgreSQL 18.6
  Memory               1g   (using 83 MB)
  CPU                  1.5   (0.0 %)
  Max connections      100   (open 3)
  Memory per query     4MB
==> Redis 8.10.2
  Memory (data)        256m   (using 3 MB)
  CPU                  0.5
  When full            noeviction
```

In the panel, **Services** shows the same plus what each app uses: its database size, its open
connections, its limits and its Redis clients.

## Change the service

```bash
andamio services postgres --mem 2g --cpus 2 --max-connections 150 --work-mem 8MB
andamio services redis --mem 512m --cpus 0.5 --policy noeviction
```

| Option | What it is | Default |
|---|---|---|
| `postgres --mem` | All of PostgreSQL's memory; 25% goes to its cache (`shared_buffers`, computed for you) | `1g` |
| `postgres --cpus` | How many CPUs it can use at most (never more than the server has) | `1.5` |
| `postgres --max-connections` | Connections across all apps (20 to 1000). Each one takes memory | `100` |
| `postgres --work-mem` | A query's memory to sort and group before using disk | `4MB` |
| `redis --mem` | Memory for data (`maxmemory`); the container has 1.5× to save to disk | `256m` |
| `redis --cpus` | How many CPUs it can use at most | `0.5` |
| `redis --policy` | What it does when full | `noeviction` |
| `redis --engine` | The engine: `redis`, `valkey` or `dragonfly` (below) | `redis` |

Before touching anything, andamio checks that PostgreSQL and Redis together stay under **70% of
the server's memory** (the rest is for your apps), and that `--max-connections` isn't below any
app's limit. Then it saves it in your configuration (a commit), pushes it and applies it: **the
service restarts**, and apps lose the connection for a few seconds and reconnect by themselves.

### When Redis fills up

- **`noeviction`** (recommended): rejects new writes and deletes nothing. If an app keeps queues
  in Redis (BullMQ, Sidekiq, Celery), it's the only safe one.
- **`allkeys-lru`**, **`allkeys-lfu`**: deletes the least used keys to make room. Only if your
  apps use Redis as a cache: a queue would lose jobs silently.
- **`volatile-lru`**, **`volatile-lfu`**, **`volatile-ttl`**: deletes only keys with an expiry;
  if none expire, rejects writes.

## The Redis engine

Three engines speak the same protocol as Redis. Your apps change nothing: they keep using
`REDIS_URL`, with the same user and the same keys.

```bash
andamio services redis --engine valkey
```

| Engine | What for | Keep in mind |
|---|---|---|
| **Redis 8** | The usual one | AGPL license since Redis 8 |
| **Valkey 9** (recommended) | Redis's free continuation (BSD license, Linux Foundation) | Same options and behavior: saves every second (AOF) |
| **Dragonfly 2** | Lots of data or traffic: uses several cores and less memory | Saves **every minute** and on shutdown, not every second: on a power cut you could lose up to a minute. Needs 256 MB per thread (from `--mem 256m`). No `volatile-*` policies |

**Switching engines copies the data.** Each engine saves in a file format the others can't
read, so andamio:

1. starts the new engine on the side, with its own volume;
2. pauses writes on the current one (reads go on) and copies every key, by type and with its
   expiry: strings, hashes, lists, sets, sorted sets and streams with their groups;
3. stops the current one and leaves the new one named `redis`.

Writes wait a few seconds; apps with ioredis or BullMQ resend them by themselves on reconnect.
If anything fails before step 3, the current engine stays as it was. The previous one's volume
is kept, and going back is another engine switch.

What does **not** travel: stream messages delivered but not yet acknowledged, and keys of module
types (if there are any, andamio doesn't switch and tells you which).

With any engine, andamio checks at the end that it asks for a password: an engine that couldn't
read its users would be left open, and that makes the switch fail instead of passing silently.

## MariaDB (MySQL)

For apps that use MySQL: Laravel, WordPress, PHP in general, or Node with `mysql2`. It's
**MariaDB 11.8**, MySQL-compatible, with the same model as PostgreSQL: one server for every app,
and each one with its own database and user, which can't see the other databases, create new
ones or read files on the server.

```bash
andamio app create myapp --repo me/myapp --mysql
```

The app gets:

| Variable | Value |
|---|---|
| `MYSQL_URL` | `mysql://myapp:…@mariadb:3306/myapp` |
| `DB_CONNECTION`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` | Laravel's, ready (only if the app doesn't also have `--db`) |

It doesn't get `DATABASE_URL`: that one is PostgreSQL's. With Prisma or Drizzle, point to
`MYSQL_URL` (`url = env("MYSQL_URL")`).

- **It only runs if some app uses it.** The first app with `--mysql` turns it on (about 150 MB of
  RAM, 512 MB at most); while no app uses it, it costs nothing.
- **Daily backup:** a full, consistent dump that doesn't lock tables, next to PostgreSQL's.
- **When you delete an app** (`andamio app destroy`), its database is backed up to
  `/srv/andamio/archive/` before it's dropped, like PostgreSQL's.
- No public port, like PostgreSQL and Redis.
- **In the panel:** **New app** ticks it by itself if the code declares it (`DB_CONNECTION=mysql`,
  `mysql2`, Prisma with `provider = "mysql"`, `mysqlclient`, `go-sql-driver/mysql`…); never by the
  language, since Laravel can use PostgreSQL too. **Services** shows its memory, connections and
  each database's size, and changes its configuration:

  ```bash
  andamio services mariadb --mem 1g --cpus 1 --max-connections 150
  ```

- **Read-only SQL console**, like PostgreSQL's: `andamio app sql myapp` (with both databases,
  `--mysql` picks MariaDB), or **Database** in the panel. It connects with a separate read-only
  user, only from inside the MariaDB server, with 5 s per query.
- When the last app using it is deleted, it turns itself off (its volume is kept).

## Limit an app

```bash
andamio app set myapp --db-connections 20    # how many connections it can open (0 = no limit)
andamio app set myapp --db-timeout 30s       # how long a query can take (0 = no limit)
```

- **Connections:** an app with a bug that opens connections without closing them (or with
  several connection pools at once) doesn't leave the others without a database: it hits its
  limit and stays there.
- **Time per query:** a stuck query is cut off instead of blocking the database. It applies to
  new connections, so andamio restarts the app when you change it.

They apply to its database, PostgreSQL or MariaDB. They're saved in its `app.yml`
(`db_connections`, `db_timeout`) and applied without redeploying.
In the panel, in the app's **Settings**, section **Database limits**.

## What isn't done

PostgreSQL and Redis **have no public port**, on purpose. To query an app's database from your
machine there's the SQL console (`andamio app sql myapp`, or **Database** in the panel), which
connects with a read-only user; or your VPN.
