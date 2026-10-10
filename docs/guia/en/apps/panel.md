---
title: Local panel
description: Your apps in the browser, with their status, tasks, deploys and live logs. It runs on your machine, not the server.
---

```bash
andamio ui
```

It opens your browser on a panel with:

- **Your server:** how long it's been up, load, RAM and disk.
- **Your apps:** status, URL, public or VPN, RAM in use, the version running and their tasks.
  The list refreshes by itself every 30 seconds.
- **Each app:** its configuration, how it's doing now, its secrets (names only), its
  [scheduled tasks](/en/docs/apps/manage/#scheduled-tasks) with the next run and how the last one
  went, its latest deploys (with the GitHub link) and its **live logs**.

Ctrl+C in the terminal closes it.

## It runs on your machine, not the server

Panels like Coolify live on the server: a page with a login that can deploy and read your
secrets, exposed to the internet. andamio's is different:

- **Nothing new on the server.** The panel is a small web server on your machine that talks to
  your VPS over SSH, just like andamio's commands. Not one more door open.
- **It only answers you.** It listens on `127.0.0.1` only, on a random port. The link
  `andamio ui` prints carries a key that changes every time; without it, the answer is
  "forbidden". And it rejects requests from other sites open in your browser.
- **For now, view only.** It changes nothing on the server and doesn't ask for your sudo
  password. To change something, the usual commands (`andamio app set`, `app secret`, `app cron`…).

The trade-off: you use it from the machine that holds your keys, not from your phone or someone
else's computer. To keep an eye from afar there are the
[phone alerts](/en/docs/server/monitoring/#phone-alerts).

## Options

| Option | What it does |
|---|---|
| `--no-browser` | Doesn't open the browser: it just prints the link (copy it yourself) |
| `--port 8765` | Uses that port instead of a random one |

On WSL it opens the Windows browser, which reaches the panel with no setup.
