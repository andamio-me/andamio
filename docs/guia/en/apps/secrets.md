---
title: Variables and secrets
description: API keys, passwords and any environment variable of your app, encrypted.
---

```bash
andamio app secret set myapp STRIPE_KEY
```

It asks for the value **hidden** (it isn't shown while you type, nor kept in your terminal's
history). It works the same for something secret (an API key) and for something that isn't
(a setting).

## What happens

1. The value is stored **encrypted** with sops in `apps/myapp/secrets.sops.env`, in your
   copy.
2. It's committed and pushed; the message carries only the name, never the value.
3. It's applied on the server: your app **restarts** with the new variable, in seconds. No
   deploy is needed, because the image is the same.

```
✓ STRIPE_KEY added (apps/myapp/secrets.sops.env, encrypted)
✓ myapp now runs with the changes (restarted, no deploy needed: same image)
```

If it already existed, its value is **replaced** (`✓ STRIPE_KEY updated`). There are never
two with the same name.

## If the last deploy failed

Typical: you pushed code that reads a new variable and forgot to create it. The deploy fails
(and your previous version stays online). When you create the variable, andamio asks:

```
myapp's last deploy failed. Retry it now, with the changes? [Y/n]
```

And re-runs that deploy without you going to GitHub.

## Several at once

Each `secret set` restarts the app. For several, save them without applying and apply once
at the end:

```bash
andamio app secret set myapp STRIPE_KEY --later
andamio app secret set myapp SMTP_PASSWORD --later
andamio app apply myapp
```

## Other commands

```bash
andamio app secret list myapp                  # names only, never values
andamio app secret rm myapp STRIPE_KEY         # remove it
cat key.txt | andamio app secret set myapp STRIPE_KEY   # the value from a file
```

`DOMAIN`, `DATABASE_URL`, `REDIS_URL` and `TAG` are set by andamio and can't be changed by
hand.

## Why not GitHub Secrets

GitHub's Secrets only exist inside the pipeline: taking them to your server would force the
deploy key to carry secrets, and they're write-only, so a rebuilt server would have nowhere
to get them from. With sops they live encrypted in your repo, the key to decrypt them is
**only on your machine**, and `andamio server` puts them back.

GitHub's Secrets are the right place for **build** secrets. See
[Deploys](/en/docs/apps/deploys/#build-secrets).
