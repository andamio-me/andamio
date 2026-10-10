---
title: Solo el backend
description: Tu frontend en Vercel (o donde quieras) y tu API, con su base, en tu servidor.
---

Un caso común: el frontend vive en Vercel, Netlify o Cloudflare Pages, y lo que necesitas
es un backend con base de datos. andamio corre la API; tu frontend la llama.

```bash
andamio app create api --repo tu-usuario/backend --public --db --redis --host api \
  --cors https://miapp.vercel.app
```

| Opción | Por qué |
|---|---|
| `--public` | Los navegadores (y los servidores de Vercel, si renderizas ahí) tienen que llegar. Sin ella, solo por la VPN |
| `--db`, `--redis` | Propios de la API y **nunca expuestos a internet**: solo tu backend llega a ellos. Tu frontend habla con la API, no con la base |
| `--host api` | Queda en `api.tudominio.com` |
| `--cors https://miapp.vercel.app` | Traefik responde CORS solo para ese origen |

Tu frontend la llama en `https://api.tudominio.com`.

## CORS

Con `--cors`, Traefik responde los encabezados CORS **solo** para los orígenes que
indiques, nunca `*`. Los demás sitios no reciben `Access-Control-Allow-Origin` y el
navegador los bloquea.

```bash
andamio app cors add api https://staging.miapp.vercel.app
andamio app cors list api
andamio app cors rm api https://staging.miapp.vercel.app
```

Para comprobarlo:

```bash
curl -s -o /dev/null -D - -H "Origin: https://miapp.vercel.app" https://api.tudominio.com/ | grep -i access-control
```

Debería responder `access-control-allow-origin: https://miapp.vercel.app`. Con otro origen,
nada.

:::caution[Usa una sola de las dos]
Si tu framework ya maneja CORS (`CORSMiddleware` en FastAPI, `cors` en Express), no uses
también `--cors`: el navegador recibiría el encabezado duplicado y bloquearía el pedido.
Elige uno: el de tu código o el de andamio.
:::

## Con tu propio dominio

```bash
andamio app domain add api api.suempresa.com
```

Apunta antes su registro `A` a tu servidor. Ver [Dominios y URLs](/es/docs/apps/domains/).
