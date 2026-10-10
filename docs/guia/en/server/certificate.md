---
title: HTTPS and certificates
description: Let's Encrypt per app, a wildcard through Cloudflare or your own certificate.
---

You pick it in `andamio init` (`andamio_tls` in your configuration):

| Mode | How | When |
|---|---|---|
| `http` (default) | One Let's Encrypt certificate per app, with any DNS. They renew on their own | To start |
| `cloudflare` | A single Let's Encrypt wildcard certificate, validated through DNS. It renews on its own | If your domain is on Cloudflare and you don't want your private apps' names in the public certificate logs |
| `custom` | Your own certificate (from a commercial CA, or a Cloudflare Origin Certificate) | If you already have one |

## `cloudflare` mode

It needs your domain's DNS on Cloudflare and a token with **Zone:DNS:Edit** permission for
that zone. `andamio init` asks for it and validates it.

## Your own certificate

```bash
andamio certificate fullchain.pem private.key   # validates it and stores it
andamio certificate                             # shows the current one and when it expires
```

It checks that the key matches, that it covers `yourdomain.com` and `*.yourdomain.com`, that
it includes the intermediate chain and how long it has left. The key is stored encrypted
with sops.

**Nobody renews it for you.** With the `completo` monitoring level, Grafana warns 20 days
before any certificate expires (Let's Encrypt ones too, in case renewal fails). Renewing is
the same command with the new files.

:::caution[Cloudflare Origin Certificate]
It's only valid through Cloudflare's proxy. Your private apps (through the VPN) don't go
through it, so browsers will reject it there. If your domain is already on Cloudflare, the
`cloudflare` mode is free, renews on its own and works for both.
:::
