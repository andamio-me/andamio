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
| `andamio seguridad` | Solo blinda el VPS: tu llave, tu usuario, SSH sin contraseñas ni root, firewall y fail2ban. Se puede repetir |
| `andamio servidor` | Prepara el VPS: usuario, SSH, firewall, VPN y la plataforma. Se puede repetir: el blindaje solo se repite si cambió (o cada 7 días); `--completo` lo fuerza |
| `andamio backups` | Backups diarios, cifrados y fuera del servidor (B2 o S3), con prueba |
| `andamio backups now\|list` | Un respaldo ya / los que hay (fecha, duración, tamaño) |
| `andamio alertas` | Aviso al celular (ntfy, sin cuenta) si un contenedor se cae o el disco se llena |
| `andamio telegram [prueba\|desactivar]` | Avisos por Telegram, guiado: tu bot, tu chat (sin buscar IDs), cifrado y aplicado |
| `andamio alertas --ntfy nuevo\|URL\|quitar` | Lo mismo sin preguntas: tema nuevo en ntfy.sh, tu propio tema, o quitar ntfy |
| `andamio alertas prueba` | Un aviso de prueba por todos los canales activos (ntfy y Telegram) |
| `andamio zona [<zona>]` | La zona horaria de tus tareas programadas: verla o cambiarla (`America/Bogota`) |
| `andamio servicios [postgres\|redis\|mariadb] [--mem 2g] [--cpus 1] [--engine valkey] …` | PostgreSQL y Redis compartidos: cómo están, y su memoria, CPU y ajustes. Ver [PostgreSQL y Redis](/es/docs/server/services/) |

## Tus apps

| Comando | Qué hace |
|---|---|
| `andamio app create <app> --repo <dueño/repo>` | La registra; desde ahí, cada `git push` a `main` la despliega. Opciones en [Crear una app](/es/docs/apps/create/#opciones) |
| `andamio app list` | Todas, con su URL, acceso y estado |
| `andamio ui` | [Panel en tu navegador](/es/docs/apps/panel/): el plano de tu servidor, apps, logs en vivo y acciones (corre en tu máquina) |
| `andamio app info <app>` | Su configuración y cómo está ahora: estado, RAM y CPU en uso, versión |
| `andamio app set <app> [--mem 512m] [--cpus 1] [--port 8080] [--health /ruta] [--public\|--vpn]` | Cambiarla sin editar `app.yml`: un reinicio, sin deploy |
| `andamio app set <app> [--db-connections 20] [--db-timeout 30s]` | Los límites de su base: conexiones y tiempo por consulta. Ver [PostgreSQL y Redis](/es/docs/server/services/#limitar-una-app) |
| `andamio app logs <app> [--worker]` | Logs en vivo (de la web, o de su worker) |
| `andamio app restart <app>` | Reinicia sus contenedores con la misma versión |
| `andamio app deploy <app>` | Despliega de nuevo lo último de main que se construyó bien, sin push |
| `andamio app create <app> --repo … --branch production` | Despliega desde otra rama (sin `--branch`: la principal del repo) |
| `andamio app create <app> --repo … --dir backend [--path /api]` | Una de varias apps de un repo ([Front y back en un repo](/es/docs/apps/monorepo/)) |
| `andamio app source <app> [--dir …] [--context .\|-] [--watch-add …] [--watch-rm …]` | De dónde sale: su carpeta y qué rutas disparan su deploy |
| `andamio app secret set <app> <CLAVE> [--later]` | Crea o cambia una variable (el valor se pide oculto) |
| `andamio app secret import <app> <.env\|-> [--later]` | Varias de una vez desde un `.env` (o stdin): un commit, un reinicio |
| `andamio app secret rm <app> <CLAVE>` | La quita |
| `andamio app secret list <app>` | Solo los nombres |
| `andamio app apply [<app>]` | Aplica lo pendiente en el servidor; reintenta un deploy fallido |
| `andamio app domain add\|rm\|list <app> [dominio]` | Un dominio propio, además del tuyo |
| `andamio app cors add\|rm\|list <app> [origen]` | Frontend en otro lado (Vercel…) |
| `andamio app volume add\|rm\|list <app> [/data]` | Carpeta que persiste entre deploys (entra al backup) |
| `andamio app cron add <app> "<horario>" "<comando>" [--name x]` | [Tarea programada](/es/docs/apps/manage/#tareas-programadas), en tu hora; avisa si falla |
| `andamio app cron list\|run\|rm <app> [tarea]` | Verlas (próxima vez y última), correr una ya, quitarla |
| `andamio app cron edit <app> <tarea> [--schedule '…'] [--command '…']` | Cambiar su horario o su comando |
| `andamio app cron runs <app> <tarea>` | Sus últimas 5 corridas programadas, con su salida |
| `andamio app stop\|start <app>` | Apagarla sin borrar nada / volver |
| `andamio app rollback <app> [<commit>]` | Volver al deploy anterior, o a ese commit |
| `andamio app restore <app> [<respaldo>\|latest]` | Su base y sus carpetas, como en ese respaldo (lo de ahora se guarda antes) |
| `andamio app sql <app> ["SELECT …"]` | Su base, de solo lectura: `psql` o una consulta |
| `andamio app revert <app> <commit>` | Deshace un cambio de su configuración (RAM, dominios, tareas…) con un commit nuevo |
| `andamio app destroy <app>` | Borrarla (respalda su base y sus carpetas antes) |
| `andamio app ci-update [<app>]` | El pipeline de tus apps, a la versión actual de andamio |
| `andamio app retry <app>` | Reintenta su último deploy, si falló (sin hacer otro push) |

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
