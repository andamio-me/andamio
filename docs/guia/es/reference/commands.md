---
title: Comandos
description: Todos los comandos de andamio, en el orden en que se usan.
---

`andamio help` muestra esta lista en tu terminal; `andamio help <comando>`, el detalle de
uno. Los nombres en inglés también funcionan: `server`, `status`, `certificate`, `forget`.

## Empezar (una vez)

| Comando | Qué hace |
|---|---|
| `andamio setup` | Deja tu máquina lista: instala git, gh, sops, age y Ansible, y crea tu copia privada |
| `andamio init` | Preguntas guiadas: configuración, llave de cifrado y secretos. Solo local |
| `andamio servidor` | Prepara el VPS: usuario, SSH, firewall, VPN y la plataforma. Se puede repetir |
| `andamio backups` | Backups diarios, cifrados y fuera del servidor (B2 o S3), con prueba |
| `andamio alertas` | Aviso al celular (ntfy, sin cuenta) si un contenedor se cae o el disco se llena |

## Tus apps

| Comando | Qué hace |
|---|---|
| `andamio app create <app> --repo <dueño/repo>` | La registra; desde ahí, cada `git push` a `main` la despliega. Opciones en [Crear una app](/es/docs/apps/create/#opciones) |
| `andamio app list` | Todas, con su URL, acceso y estado |
| `andamio app info <app>` | Su configuración y cómo está ahora: estado, RAM y CPU en uso, versión |
| `andamio app set <app> [--mem 512m] [--cpus 1] [--port 8080] [--health /ruta] [--public\|--vpn]` | Cambiarla sin editar `app.yml`: un reinicio, sin deploy |
| `andamio app logs <app>` | Logs en vivo |
| `andamio app secret set <app> <CLAVE> [--later]` | Crea o cambia una variable (el valor se pide oculto) |
| `andamio app secret rm <app> <CLAVE>` | La quita |
| `andamio app secret list <app>` | Solo los nombres |
| `andamio app apply [<app>]` | Aplica lo pendiente en el servidor; reintenta un deploy fallido |
| `andamio app domain add\|rm\|list <app> [dominio]` | Un dominio propio, además del tuyo |
| `andamio app cors add\|rm\|list <app> [origen]` | Frontend en otro lado (Vercel…) |
| `andamio app volume add\|rm\|list <app> [/data]` | Carpeta que persiste entre deploys (entra al backup) |
| `andamio app stop\|start <app>` | Apagarla sin borrar nada / volver |
| `andamio app rollback <app>` | Volver al deploy anterior |
| `andamio app destroy <app>` | Borrarla (respalda su base y sus carpetas antes) |
| `andamio app ci-update [<app>]` | El pipeline de tus apps, a la versión actual de andamio |

## Día a día

| Comando | Qué hace |
|---|---|
| `andamio estado` | Chequeo de seguridad y salud, desde el servidor y desde internet. No cambia nada |
| `andamio update [--check]` | Trae las mejoras y los parches de andamio sin tocar lo tuyo |
| `andamio certificado [cert llave]` | Tu propio certificado HTTPS: ver o reemplazar |
| `andamio servidor` | También vuelve a aplicar todo |
| `andamio use [carpeta\|dominio]` | Con varios servidores: qué copia usa `andamio` fuera de sus carpetas |
| `andamio olvidar` | Borra ya tu contraseña de sudo recordada |

## Variables de entorno

| Variable | Qué hace |
|---|---|
| `ANDAMIO_LANG` | `es` o `en`. Si no está, sigue a `LANG` |
| `ANDAMIO_SUDO_MINUTES` | Minutos que se recuerda tu contraseña de sudo sin uso (15 por defecto; `0` = nunca) |
| `ANDAMIO_VERBOSE` | `1` muestra la salida completa de Ansible en vez del resumen |
