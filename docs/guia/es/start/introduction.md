---
title: Introducción
description: Qué es andamio, cómo funciona y por dónde empezar.
---

andamio es un PaaS open source para **un solo VPS**. Primero deja tu servidor seguro (usuario
propio, SSH solo con llave, firewall, VPN, parches automáticos, backups) y después despliega
tus apps, cada una aislada, con un `git push`. Sin panel web: todo pasa por tu terminal y tu
repo.

## Elige una página

| Quiero… | Ve a |
|---|---|
| Ver qué necesito antes de empezar | [Requisitos](/es/docs/start/requirements/) |
| Instalar andamio y preparar mi servidor | [Instalar](/es/docs/start/install/) y [Tu servidor](/es/docs/start/server/) |
| Publicar mi primera app | [Crear una app](/es/docs/apps/create/) |
| Entender qué pasa en cada `git push` | [Despliegues](/es/docs/apps/deploys/) |
| Usar mi dominio o un subdominio | [Dominios y URLs](/es/docs/apps/domains/) |
| Ponerle una API key a mi app | [Variables y secretos](/es/docs/apps/secrets/) |
| Tener el frontend en Vercel y el backend aquí | [Solo el backend](/es/docs/apps/backend-only/) |
| Saber por qué falló un deploy | [Cuando algo falla](/es/docs/apps/failures/) |
| Apagar, volver atrás o borrar una app | [Administrar una app](/es/docs/apps/manage/) |
| Revisar que mi servidor esté seguro | [Seguridad](/es/docs/server/security/) |
| Respaldar mis datos fuera del servidor | [Backups](/es/docs/server/backups/) |
| Traer las mejoras de andamio | [Actualizar](/es/docs/server/update/) |
| Ver todos los comandos | [Comandos](/es/docs/reference/commands/) |

## Inicio rápido

```bash
# 1. En tu máquina (Linux, macOS o WSL): instala lo que falta y crea tu copia privada
curl -fsSL https://raw.githubusercontent.com/Geovani29/andamio/main/install.sh | sh

# 2. Tu configuración: preguntas guiadas, todo local
cd ~/mi-andamio
andamio init

# 3. Tu servidor: lo endurece y levanta la plataforma (se puede repetir)
andamio servidor

# 4. Tu primera app, desde un repo tuyo en cualquier lenguaje
andamio app create miapp --repo tu-usuario/miapp --health /healthz --public
```

Desde ahí, cada `git push` a `main` del repo de tu app la despliega en
`https://miapp.tudominio.com`.

## Cómo funciona

Tener tu propio servidor tiene dos etapas, y andamio cubre las dos:

1. **"Compré un VPS, ¿y ahora?"** Suele venir con root, una contraseña y todos los puertos
   abiertos. `andamio servidor` lo endurece y levanta la plataforma: Traefik con HTTPS
   automático, PostgreSQL y Redis compartidos (con un usuario por app), monitoreo y la VPN.
2. **"Quiero publicar mis apps."** Cada app se construye en GitHub Actions (nunca en tu
   VPS), pasa escaneo de secretos, tus tests y un escaneo de vulnerabilidades, y llega a tu
   servidor con una llave que solo puede desplegar esa app.

Todo lo de tu servidor vive en **tu copia de andamio**, un repo privado en tu GitHub: la
configuración, los secretos (cifrados con sops y age) y la definición de cada app. Si el
servidor desaparece, se reconstruye desde ese repo y tus backups.

## Lo que andamio no es

- **No es alta disponibilidad.** Es un solo servidor: si se cae, tus apps se caen con él.
- **No tiene panel web.** Si prefieres administrar todo con clics, Coolify o Dokploy te van
  a resultar más cómodos.
- **No es para no tener servidor.** Si no quieres uno, un PaaS administrado (Railway,
  Render, Vercel) es más simple.
