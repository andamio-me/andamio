---
title: Several servers
description: One copy of andamio per server, and the andamio command from any folder.
---

Each server has **its own copy** of andamio: a repo with its configuration, its secrets and
its apps. For a second server (production and staging, or two clients), run `andamio setup`
again with another copy name and follow the same steps.

## Which copy `andamio` uses

The `andamio` command works from any folder:

- **Inside a copy's folder** (or any subfolder), it uses that one.
- **Elsewhere**, it uses the one you picked with `andamio use`.

```bash
andamio use
```

```
Your andamio copies (● = the one `andamio` uses outside their folders):
  ● /home/you/my-andamio        yourdomain.com  (203.0.113.10)
    /home/you/andamio-staging   staging.yourdomain.com  (203.0.113.20)
```

```bash
andamio use staging.yourdomain.com    # or the folder
```

Each copy is noted on its own the first time you use it.

:::tip
If an app command can't find the app, it tells you which server that copy points to and
which apps it has: it's almost always that you're in another copy's folder.
:::

## Your sudo password

Each server has its own, and andamio remembers them separately (15 idle minutes, in memory
only). `andamio forget` wipes them all.
