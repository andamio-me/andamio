---
title: Backend only
description: Your frontend on Vercel (or wherever) and your API, with its database, on your server.
---

A common case: the frontend lives on Vercel, Netlify or Cloudflare Pages, and what you need
is a backend with a database. andamio runs the API; your frontend calls it.

```bash
andamio app create api --repo your-user/backend --public --db --redis --host api \
  --cors https://myapp.vercel.app
```

| Option | Why |
|---|---|
| `--public` | Browsers (and Vercel's servers, if you render there) have to reach it. Without it, VPN only |
| `--db`, `--redis` | The API's own, and **never exposed to the internet**: only your backend reaches them. Your frontend talks to the API, not to the database |
| `--host api` | It lives at `api.yourdomain.com` |
| `--cors https://myapp.vercel.app` | Traefik answers CORS only for that origin |

Your frontend calls it at `https://api.yourdomain.com`.

## CORS

With `--cors`, Traefik answers the CORS headers **only** for the origins you list, never
`*`. Other sites don't get `Access-Control-Allow-Origin` and the browser blocks them.

```bash
andamio app cors add api https://staging.myapp.vercel.app
andamio app cors list api
andamio app cors rm api https://staging.myapp.vercel.app
```

To check it:

```bash
curl -s -o /dev/null -D - -H "Origin: https://myapp.vercel.app" https://api.yourdomain.com/ | grep -i access-control
```

It should answer `access-control-allow-origin: https://myapp.vercel.app`. With another
origin, nothing.

:::caution[Use only one of the two]
If your framework already handles CORS (`CORSMiddleware` in FastAPI, `cors` in Express),
don't also use `--cors`: the browser would get the header twice and block the request. Pick
one: your code's or andamio's.
:::

## With your own domain

```bash
andamio app domain add api api.yourcompany.com
```

Point its `A` record to your server first. See [Domains and URLs](/en/docs/apps/domains/).
