---
title: Domains and URLs
description: Where each app lives, and how to use a subdomain, the root domain or a domain of your own.
---

The domain you gave `andamio init` is **your server's domain**. Each app is a subdomain of
it, named after the app:

| When you create it | Its address |
|---|---|
| `andamio app create blog` | `blog.yourdomain.com` |
| `--host api` | `api.yourdomain.com` |
| `--host @` | `yourdomain.com` (the root domain) |
| `--domain app.yourcompany.com` | `app.yourcompany.com`, besides its own |

If your server's domain is itself a subdomain (`lab.yourdomain.com`), everything hangs from
it: `blog.lab.yourdomain.com`, `api.lab.yourdomain.com`.

Each address has its own Let's Encrypt certificate, renewed on its own.

## Why two DNS records

You created `yourdomain.com` and `*.yourdomain.com` once. The `*` makes **every new app**
already point to your server: you don't touch DNS again for `blog`, `api` or any other.

## A domain of your own

For a domain that isn't your server's (`api.yourcompany.com`) or a deeper name
(`v2.api.yourdomain.com`):

1. Point its `A` record to your server's IP.
2. Add it:

```bash
andamio app domain add myapp api.yourcompany.com
andamio app domain list myapp
andamio app domain rm myapp api.yourcompany.com
```

andamio checks that DNS already points to your server before asking for the certificate,
and warns you if it doesn't.

:::note
For a direct subdomain of yours (`api.yourdomain.com`) use `--host api` when creating it;
for the root domain, `--host @`. `domain add` suggests it if you try.
:::

## Private or public

Without `--public`, the app answers **only inside your VPN**: from the internet it doesn't
even load. It's the safest option for dashboards, admins and internal tools.

:::caution
In the `http` HTTPS mode (the default), every app's name, private ones too, shows up in the
public certificate logs. If that matters to you, use the `cloudflare` mode (a single
wildcard certificate). See [HTTPS and certificates](/en/docs/server/certificate/).
:::
