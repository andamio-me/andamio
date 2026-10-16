---
title: Local panel
description: Your apps in the browser, with their status, live logs and actions (stop, change resources, run tasks). It runs on your machine, not the server.
---

```bash
andamio ui
```

It opens your browser on a panel with a **menu on the left**: your server and "Go to…"
(Ctrl+K) at the top; then Home, your apps (the one you open expands with its sections) and the
platform (Backups, History, Settings); at the bottom, notices and the button to collapse it to
icons. On small screens it opens with ☰. Each app has its sections, each with its own link:
**Overview** (how it's doing and what's worth a look), **Deploys**, **Logs** (full screen),
**Metrics**, **Variables**, **Tasks**, **Database** and **Settings**.

An app's **Overview** tells you how it's doing at a glance: its CPU and RAM over the last 24 h
against its limit (with a mini chart and the peak), its traffic, and whether it was online, hour
by hour. Below, its activity in a single timeline (deploys, configuration changes, starts,
outages and tasks) and its parts: the web container, the worker and the shared services it uses
(PostgreSQL, Redis) with their health and RAM, its tasks, its last backup and its certificates.

What you'll find:

- **Your server's plan**, live: the internet and your VPN come in through Traefik, which
  routes to your apps (public and VPN only); the ones using a database or Redis have their
  arrow. Each app shows its status and RAM; clicking it opens its detail. Next to it, the title
  block with the server: uptime, load, RAM and disk.
- **The platform**, at the foot of the plan: the last and next backup, whether phone alerts
  are on, and the last security check (with **Check now**, which runs `andamio status` in the
  terminal, and its warnings with their fix). Whatever isn't set up is drawn dashed, with the
  command that sets it up.
- **What needs attention**, at the very top and only if there's something: an app down, the
  disk almost full, a failed backup or a security problem.
- **Your apps** in a table: status, URL, access, RAM, version and tasks. It refreshes by itself
  every 30 seconds.
- **The server over time:** CPU, RAM and network for the last hours or days (1 h, 6 h, 24 h or
  7 days), from the server's Prometheus. Hover (or use the arrow keys) to see each moment's value.
- **Recent deploys** across all your apps, with the GitHub link.
- **Backups** (from the platform row, **See backups**): how the nightly one is doing, the ones
  there are (date, how long it took, size) and **Back up now**.
- **Each app:** its configuration, how it's doing now, its **usage over time** (CPU, RAM with
  its limit line, and network), its secrets (names only), its
  [scheduled tasks](/en/docs/apps/manage/#scheduled-tasks), its latest deploys (with the GitHub
  link), its **live logs** (with search, "errors only", 200, 1000 or 5000 lines back and
  **Download**) and its latest changes.
- **History** (the clock, at the top): every change to your configuration, by day, from your
  repo's commits. An app's configuration changes (RAM, domains, tasks, CORS, access) show their
  lines and have **Undo**.
- **An app's settings**: an index on the right and a filter at the top. **Code** says where it
  comes from (repo, branch, folder and which paths trigger its deploy); **Resources**, **Network
  and data**, **Changes** and the **Danger zone**.
- **Settings** (under Platform): the theme (system, light or dark, saved in your browser), which alerts are on and **Send a test**, the tasks' time
  zone, **Check for updates** of andamio, your servers and a summary of your configuration.

**Ctrl+K** (⌘K on Mac), or the search box at the top, opens "Go to…": type part of the name of
an app, a page or an action (stop or start an app, back up now, run a security check) and press
Enter. It works entirely from the keyboard.

Ctrl+C in the terminal closes it.

## Actions

In an app's detail:

- **Change RAM, CPU, port, health or access:** click the value and type the new one; Enter
  leaves it pending. At the bottom you see the command that will run
  (`andamio app set web --mem 512m`) and **Apply**. It's a restart with the same image, no deploy.
- **Stop and start** the app.
- **Secrets:** add or change one (the value goes in a hidden field and reaches the command
  through stdin: it's never shown, not even in the terminal) and remove it. **Paste several**
  adds a whole `.env` at once, with a single restart.
- **Scheduled tasks:** create one (as you type the schedule you see when it will run next, or
  what's wrong), run it now and remove it.
- **Own domains, CORS and persistent folders:** add and remove. Before adding a domain, the
  panel checks whether its DNS already points to your server; if not, it gives you the missing
  A record and only goes on if you tick "Add it anyway".
- **Retry the last deploy**, if it failed (for example, because a variable you've now set was
  missing).

Each action runs **the same CLI command** (commit, push and apply, as always) and shows it in a
terminal inside the page: first the command, then its real output. One action at a time. If
andamio needs your sudo password, it asks for it **inside that terminal**: it's checked against
your server and remembered only in your machine's memory, just like the CLI: 15 idle minutes,
or what you pick in **Settings → Sudo password** (up to 8 h), where you can also forget it.

- **Delete the app**, at the foot of its detail (**Danger zone**), with a double confirmation
  like GitHub's: you tick that you understand what gets deleted and type its exact name. It
  runs the same `andamio app destroy`: it backs up the database and archives its folders
  first; the GitHub repo is left alone. Your dashboard isn't deleted from here.

- **Roll back a deploy:** in its deploys, each successful one has **Roll back here** (the one
  running now says "in production"). A window shows the current version and the one it goes
  back to; it runs `andamio app rollback <app> <commit>`, the usual zero-downtime deploy: if that
  version doesn't come up healthy, the current one keeps running. The database doesn't change,
  and the next push to `main` deploys the latest again.
- **Restore from a backup:** in **Backups**, each one has **Restore an app…** (also reachable
  from the app's Danger zone). A two-step window, like deleting: you pick the app and read what
  gets replaced (its database and persistent folders), what's saved first and what's left alone
  (Redis, the code, the secrets); then you type its name. It runs
  `andamio app restore <app> <backup>`, which tests the backup in a temporary database before
  touching anything and saves the current data in `/srv/andamio/archive/`.

- **Undo a configuration change:** in History (or in the app's changes), **Undo**. The
  window shows how its configuration ends up; it runs `andamio app revert <app> <commit>`: a new
  commit (history isn't erased) and applying that app. Configuration changes only: never
  secrets, nor creating or deleting an app. If a later change touched the same lines, it doesn't
  do it and tells you.

- **Query its database, read-only:** in apps with PostgreSQL, **Database**: its tables (a
  click queries it) and an editor (Ctrl+Enter). It runs as a separate user that can only read,
  in a read-only transaction, 5 seconds max and up to 500 rows: nothing there can change data.
  Tables come with their rows and columns (searchable); results show as a table or record by
  record, with sensitive columns (passwords, hashes, secrets) hidden until you show them; click a
  cell to see it whole. Results download as CSV, and your last queries stay in a history.
- **Telegram:** in Settings, **Set up Telegram** in three steps (your bot, your chat, turn on),
  same as `andamio telegram`. The token is typed hidden and goes into the command via stdin.
- **ntfy:** in Settings, **Set up ntfy**: a new topic on ntfy.sh or your own server's URL. Then
  you see the topic's address to subscribe, copy it and send a test one.

- **Restart** (at the top, next to Stop): its containers, same version.
- **Deploy now** (in Deploys): main's latest successful build, no push needed.
- **Tasks:** **Edit** changes its schedule or command; **Runs** shows the last 5 scheduled ones,
  with their output (failed ones open).
- **Worker logs:** if the app has a worker, the logs have web and worker.
- **Availability and HTTPS:** in "Now", the % of time online over 24 h and 7 days (from its
  container's health) and when each domain's certificate expires. On the home page, the "Online
  24 h" column, and a notice at the top if a certificate isn't valid or expires in under 14 days.

- **Outages:** the last 7 days, one bar per hour (green online, amber partial, red down, gray not
  measured), and the list of outages with how long they lasted.
- **See why** on a failed deploy: the step that failed, the cause, the server's 💡 hints and the
  last lines of the log, without going to GitHub.
- **RAM and CPU suggestions** (with at least 2 days of data): if the peak gets close to the
  limit, raise it; if there's lots to spare, lower it. **Use** leaves it pending in the Apply bar:
  you decide.
- **Check variables** (in Secrets): compares the variables the code uses (main's latest) with
  the app's secrets and tells you which are missing, with **Add** next to them. If the last
  deploy failed, it checks by itself.
- **The bell** (at the top): the last 30 notices (deploys, actions, failures), even if you
  weren't looking. Kept only in your browser.

Opening an app you've already seen is instant (it shows what it had and updates by itself), and
hovering over an app fetches it before you open it. The connection to the server stays ready
while the panel is open.

## Services

**Services** (under Platform) shows the PostgreSQL and Redis your apps share: memory, CPU,
connections and keys in use, and what each app uses (its database size, its connections, its
limits, its Redis clients). Their configuration is changed right there; since it restarts the
service, a dialog says so before running anything. See [PostgreSQL and Redis](/en/docs/server/services/).

## Several servers

Each andamio copy manages one server (the ones `andamio use` knows). With more than one, the
domain at the top is a menu: picking another opens **its own panel** in another tab, with its
own key and keys; nothing gets mixed. Panels opened this way close with this one. They're also
in **Settings → Your servers**.

## Notifications

While the panel is open, it watches your deploys (every 15 seconds if one is running,
otherwise every minute). When one finishes, a notice shows up at the top right: "web deployed",
with the link to the app, or "web's deploy failed", with the link to the log (that one stays
until you close it). It works for the ones a `git push` starts too, not only the panel's.

With **Notify me** (at the top, once) the browser also shows a system notification when you're
in another tab or window. You ask for the permission with that button: the panel never asks
by itself.

## Create an app

On the home page, **New app** opens five steps on the same page:

1. **The repo:** search your GitHub repos (or type `owner/repo`), or start from your template.
   If the repo is public and your pipeline is private, it tells you before going on.
2. **The review:** the panel clones the repo into a temporary folder (reused for a few minutes
   if you pick another folder, then deleted) and
   shows what `andamio app create` would say, without changing anything: the language, the
   Dockerfile (its own, or the one andamio proposes, so you can read it), the start command
   (you can change it) and the [pre-check](/en/docs/apps/create/#pre-check). If it stores files,
   one click adds a persistent folder; if something is serious, you only go on by ticking
   "create anyway".
3. **Ready to deploy:** if the review came out clean, a summary (name, address, port, services
   and access) and one button, **Deploy with what was detected**, like Railway. PostgreSQL and
   Redis turn on by themselves if the code uses `DATABASE_URL` or `REDIS_*`. **Customize** opens
   the full configuration: name, address (or the root domain), access, port, health, RAM,
   PostgreSQL, Redis and persistent folder.
4. **Environment variables:** the ones the code uses (`os.getenv`, `process.env`, `os.Getenv` or
   a `.env.example`) come already listed, with where they were found. The ones the code
   **requires** (`getOrThrow`, `os.environ[...]`, `process.env.X!`) go first, marked "required";
   if they have a non-secret value in `.env.example`, one click uses it (never set by itself).
   Fill in their values in hidden fields, paste a whole `.env` or add others. They're encrypted before the first deploy and reach the command
   through stdin (`--env-file -`): never shown.
5. **Create:** the exact command (`andamio app create …`) and what will happen. First your sudo
   password; then, instead of the whole output, the stages with their time (review, register,
   server, pipeline, deploy); the detail stays folded. When it's done it opens the app, where you
   see the **first deploy live**: its three GitHub Actions jobs, the current step and a progress
   bar, and at the end whether it went well or why it failed.

## It runs on your machine, not the server

Panels like Coolify live on the server: a page with a login that can deploy and read your
secrets, exposed to the internet. andamio's is different:

- **Nothing new on the server.** The panel is a small web server on your machine that talks to
  your VPS over SSH, just like andamio's commands. Not one more door open.
- **It only answers you.** It listens on `127.0.0.1` only, on a random port. The link
  `andamio ui` prints carries a key that changes every time; without it, the answer is
  "forbidden". Actions also require the page's exact origin and a session key that another site
  open in your browser can't read or send.
- **Your secrets and keys never leave your machine**, and every change is a commit in your
  repo, as with the CLI.

The trade-off: you use it from the machine that holds your keys, not from your phone or someone
else's computer. To keep an eye from afar there are the
[phone alerts](/en/docs/server/monitoring/#phone-alerts).

## Options

| Option | What it does |
|---|---|
| `--no-browser` | Doesn't open the browser: it just prints the link (copy it yourself) |
| `--port 8765` | Uses that port instead of a random one |

On WSL it opens the Windows browser, which reaches the panel with no setup.
