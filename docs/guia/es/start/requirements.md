---
title: Requisitos
description: El servidor, el dominio, la cuenta y la máquina que necesitas antes de empezar.
---

## Un VPS

- **Ubuntu 24.04**, recién creado. andamio lo prepara desde cero.
- **1 GB de RAM** como mínimo; 2 GB o más es cómodo. Las imágenes se construyen en GitHub
  Actions, no en tu servidor, por eso alcanza con poco.
- Su **IP pública**, y acceso como root o con el usuario inicial de tu proveedor (con
  contraseña o con la llave `.pem` que te dio).

Probado de punta a punta en VPS nuevos de Azure (1 vCPU y 1 GB). Otros proveedores con
Ubuntu 24.04 deberían funcionar igual; la prueba en Hetzner, DigitalOcean, Oracle y AWS está
en la hoja de ruta.

## Un dominio

Con **dos registros DNS `A`** apuntando a la IP de tu VPS:

| Nombre | Tipo | Valor |
|---|---|---|
| `tudominio.com` | A | la IP de tu VPS |
| `*.tudominio.com` | A | la IP de tu VPS |

El `*` hace que cada app nueva (`blog.tudominio.com`, `api.tudominio.com`…) ya apunte a tu
servidor sin volver a tocar el DNS. Puede ser un subdominio (`lab.tudominio.com` y
`*.lab.tudominio.com`) si el dominio principal ya se usa en otro lado.

:::tip[¿Cloudflare?]
Si usas el proxy de Cloudflare (la nube naranja), desactívalo en esos dos registros (nube
gris) para que Let's Encrypt pueda emitir los certificados, o usa el modo HTTPS
`cloudflare`. Ver [Certificado propio](/es/docs/server/certificate/).
:::

## Una cuenta de GitHub

Ahí viven tu copia privada de andamio, los repos de tus apps, sus imágenes (en GHCR) y el
pipeline que las construye. GitLab está en la hoja de ruta.

## Tu máquina

- **Linux** (Ubuntu o Debian), **macOS**, o **Windows con WSL**.
- En Windows: `wsl --install` en PowerShell, y después trabajas dentro de Ubuntu.
- No necesitas instalar nada más a mano: `andamio setup` instala git, gh, sops, age y
  Ansible, preguntando antes.
