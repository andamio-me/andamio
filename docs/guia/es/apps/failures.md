---
title: Cuando algo falla
description: Un deploy roto no tumba tu app, y el mensaje te dice qué arreglar.
---

Si la versión nueva no queda sana, **nunca recibe tráfico**: se descarta y sigue corriendo
la anterior. El pipeline te dice por qué.

## Dónde verlo

- **En tu terminal**, si el deploy lo lanzó andamio (`app create`, un reintento): el paso
  que falló, sus últimas líneas de log y el link a la corrida.
- **En GitHub**, arriba de la corrida (pestaña *Actions* del repo de tu app), como
  anotaciones:

```
❌ La versión nueva no quedó sana. Sigue corriendo la versión anterior.
💡 Falta la variable STRIPE_KEY. Agrégala: andamio app secret set miapp STRIPE_KEY
```

Debajo, en el paso del deploy, están los últimos logs de tu app. Los mensajes salen en el
idioma de tu servidor.

## Las pistas

andamio reconoce los errores típicos de una app que no está lista para un servidor:

| Síntoma en los logs | Pista |
|---|---|
| Escucha en `127.0.0.1` o `localhost` | Haz que escuche en `0.0.0.0` (dentro del contenedor, nadie más llega a localhost) |
| `EADDRINUSE`, *address already in use* | El puerto ya está en uso: ¿tu app arranca dos servidores? |
| `KeyError: 'X'`, *X is not set*, *missing variable X* | Falta la variable: `andamio app secret set miapp X` |
| *ModuleNotFoundError*, *Cannot find module* | Falta una dependencia en `requirements.txt`, `package.json` o `go.mod` |
| *Permission denied*, *EACCES* | Escribe donde no puede (corre sin root): usa `/tmp`, o la base para lo que deba durar |
| Se cierra sin escribir nada | Revisa el comando de arranque (`CMD`) de tu Dockerfile |
| Corre, pero no responde | ¿Escucha en el puerto correcto y en `0.0.0.0`? ¿Tu ruta de salud responde `200`? |

## Arreglarlo

Si fue el código: arréglalo y haz `git push`. Cada push vuelve a intentar.

Si faltaba una variable: créala, y andamio te ofrece reintentar el deploy que falló.

```bash
andamio app secret set miapp STRIPE_KEY
```

```
El último deploy de miapp falló. ¿Lo reintento ahora, con los cambios? [S/n]
```

## Volver atrás

Si el error ya estaba en producción (el deploy pasó, pero la versión nueva tiene un bug):

```bash
andamio app rollback miapp
```

Vuelve al deploy exitoso anterior.

## Si se cae el servidor entero

Todo lo de tu servidor está descrito en tu copia de andamio (Ansible), y tus datos en tus
[backups](/es/docs/server/backups/). Reconstruirlo es: un VPS nuevo, `andamio servidor`, y
restaurar el último backup.
