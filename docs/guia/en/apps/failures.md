---
title: When something fails
description: A broken deploy doesn't take your app down, and the message tells you what to fix.
---

If the new version doesn't become healthy, it **never gets traffic**: it's discarded and the
previous one keeps running. The pipeline tells you why.

## Where to see it

- **In your terminal**, if andamio started the deploy (`app create`, a retry): the step that
  failed, its last log lines and the link to the run.
- **On GitHub**, on top of the run (your app repo's *Actions* tab), as annotations:

```
❌ The new version didn't become healthy. The previous version keeps running.
💡 Variable STRIPE_KEY is missing. Add it: andamio app secret set myapp STRIPE_KEY
```

Below, in the deploy step, are your app's last logs. Messages come in your server's
language.

## The hints

andamio recognizes the typical errors of an app that isn't ready for a server:

| Symptom in the logs | Hint |
|---|---|
| Listens on `127.0.0.1` or `localhost` | Make it listen on `0.0.0.0` (inside the container, nobody else reaches localhost) |
| `EADDRINUSE`, *address already in use* | The port is already in use: does your app start two servers? |
| `KeyError: 'X'`, *X is not set*, *missing variable X* | The variable is missing: `andamio app secret set myapp X` |
| *ModuleNotFoundError*, *Cannot find module* | A dependency is missing from `requirements.txt`, `package.json` or `go.mod` |
| *Permission denied*, *EACCES* | It writes where it can't (it runs without root): use `/tmp`, or the database for what must last |
| Exits without printing anything | Check your Dockerfile's start command (`CMD`) |
| Runs, but doesn't answer | Does it listen on the right port and on `0.0.0.0`? Does your health route return `200`? |

## Fix it

If it was the code: fix it and `git push`. Every push tries again.

If a variable was missing: create it, and andamio offers to retry the failed deploy.

```bash
andamio app secret set myapp STRIPE_KEY
```

```
myapp's last deploy failed. Retry it now, with the changes? [Y/n]
```

## Go back

If the bug was already in production (the deploy passed, but the new version has a bug):

```bash
andamio app rollback myapp
```

Goes back to the previous successful deploy.

## If the whole server goes down

Everything about your server is described in your copy of andamio (Ansible), and your data
in your [backups](/en/docs/server/backups/). Rebuilding it is: a new VPS, `andamio server`,
and restoring the last backup.
