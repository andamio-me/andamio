---
title: HTTPS y certificados
description: Let's Encrypt por app, un comodín por Cloudflare o tu propio certificado.
---

Lo eliges en `andamio init` (`andamio_tls` en tu configuración):

| Modo | Cómo | Cuándo |
|---|---|---|
| `http` (por defecto) | Un certificado de Let's Encrypt por app, con cualquier DNS. Se renuevan solos | Para empezar |
| `cloudflare` | Un solo certificado comodín de Let's Encrypt, validado por DNS. Se renueva solo | Si tu dominio está en Cloudflare y no quieres que los nombres de tus apps privadas aparezcan en los registros públicos de certificados |
| `custom` | Tu propio certificado (de una CA comercial, o un Origin Certificate de Cloudflare) | Si ya tienes uno |

## Modo `cloudflare`

Necesita el DNS de tu dominio en Cloudflare y un token con permiso **Zone:DNS:Edit** para
esa zona. `andamio init` te lo pide y lo valida.

## Tu propio certificado

```bash
andamio certificado fullchain.pem privada.key   # lo valida y lo guarda
andamio certificado                             # muestra el actual y cuándo vence
```

Revisa que la llave corresponda, que cubra `tudominio.com` y `*.tudominio.com`, que traiga
la cadena de intermedios y cuánto le queda. La llave se guarda cifrada con sops.

**Nadie lo renueva por ti.** Con el monitoreo `completo`, Grafana avisa 20 días antes de que
venza cualquier certificado (también los de Let's Encrypt, por si la renovación falla).
Renovar es el mismo comando con los archivos nuevos.

:::caution[Origin Certificate de Cloudflare]
Solo es válido a través del proxy de Cloudflare. Tus apps privadas (por la VPN) no pasan
por ahí, así que los navegadores lo rechazarán en ellas. Si tu dominio ya está en
Cloudflare, el modo `cloudflare` es gratis, se renueva solo y sirve para ambas.
:::
