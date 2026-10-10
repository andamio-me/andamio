---
title: Dominios y URLs
description: Dónde queda cada app, y cómo usar un subdominio, el dominio raíz o un dominio propio.
---

El dominio que le diste a `andamio init` es el **dominio de tu servidor**. Cada app es un
subdominio suyo, con el nombre de la app:

| Al crearla | Su dirección |
|---|---|
| `andamio app create blog` | `blog.tudominio.com` |
| `--host api` | `api.tudominio.com` |
| `--host @` | `tudominio.com` (el dominio raíz) |
| `--domain app.suempresa.com` | `app.suempresa.com`, además de la suya |

Si el dominio de tu servidor es a su vez un subdominio (`lab.tudominio.com`), todo cuelga de
él: `blog.lab.tudominio.com`, `api.lab.tudominio.com`.

Cada dirección tiene su propio certificado de Let's Encrypt, que se renueva solo.

## Por qué dos registros DNS

Creaste `tudominio.com` y `*.tudominio.com` una sola vez. El `*` hace que **cualquier app
nueva** ya apunte a tu servidor: no vuelves a tocar el DNS para `blog`, `api` ni ninguna
otra.

## Un dominio propio

Para un dominio que no es el de tu servidor (`api.suempresa.com`) o un nombre de más niveles
(`v2.api.tudominio.com`):

1. Apunta su registro `A` a la IP de tu servidor.
2. Agrégalo:

```bash
andamio app domain add miapp api.suempresa.com
andamio app domain list miapp
andamio app domain rm miapp api.suempresa.com
```

andamio revisa que el DNS ya apunte a tu servidor antes de pedir el certificado, y te avisa
si no.

:::note
Para un subdominio directo del tuyo (`api.tudominio.com`) usa `--host api` al crearla; para
el dominio raíz, `--host @`. `domain add` te lo sugiere si lo intentas.
:::

## Privada o pública

Sin `--public`, la app responde **solo dentro de tu VPN**: desde internet ni siquiera
carga. Es lo más seguro para paneles, admins y herramientas internas.

:::caution
En el modo HTTPS `http` (el por defecto), el nombre de cada app, también las privadas,
aparece en los registros públicos de certificados. Si te importa, usa el modo `cloudflare`
(un solo certificado comodín). Ver [Certificado propio](/es/docs/server/certificate/).
:::
