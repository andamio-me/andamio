---
title: Panel local
description: Tus apps en el navegador, con su estado, tareas, deploys y logs en vivo. Corre en tu máquina, no en el servidor.
---

```bash
andamio ui
```

Abre tu navegador en un panel con:

- **Tu servidor:** cuánto lleva encendido, la carga, la RAM y el disco.
- **Tus apps:** estado, URL, si es pública o por VPN, la RAM que usa, la versión que corre y
  sus tareas. La lista se pone al día sola cada 30 segundos.
- **Cada app:** su configuración, cómo está ahora, sus secretos (solo los nombres), sus
  [tareas programadas](/es/docs/apps/manage/#tareas-programadas) con la próxima vez y cómo salió
  la última, sus últimos deploys (con el link a GitHub) y sus **logs en vivo**.

Ctrl+C en la terminal lo cierra.

## Corre en tu máquina, no en el servidor

Paneles como Coolify viven en el servidor: una página con login que puede desplegar y leer
tus secretos, expuesta en internet. El de andamio es distinto:

- **En el servidor no hay nada nuevo.** El panel es un pequeño servidor web en tu máquina que
  habla con tu VPS por SSH, igual que los comandos de andamio. Ni una puerta más abierta.
- **Solo te responde a ti.** Escucha solo en `127.0.0.1`, en un puerto al azar. El link que
  muestra `andamio ui` trae una clave que cambia cada vez; sin ella responde "prohibido". Y
  rechaza pedidos de otros sitios abiertos en tu navegador.
- **Hoy solo mira.** No cambia nada en el servidor ni pide tu contraseña de sudo. Para cambiar
  algo, los comandos de siempre (`andamio app set`, `app secret`, `app cron`…).

La contrapartida: se usa desde la máquina que tiene tus llaves, no desde el celular o una
computadora ajena. Para mirar de lejos están las
[alertas al celular](/es/docs/server/monitoring/#alertas-al-celular).

## Opciones

| Opción | Qué hace |
|---|---|
| `--no-browser` | No abre el navegador: solo muestra el link (cópialo tú) |
| `--port 8765` | Usa ese puerto en vez de uno al azar |

En WSL se abre el navegador de Windows, que llega al panel sin configurar nada.
