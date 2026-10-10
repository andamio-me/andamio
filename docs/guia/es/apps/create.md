---
title: Crear una app
description: Registra un repo tuyo, en cualquier lenguaje, y despliégalo con un git push.
---

```bash
andamio app create miapp --repo tu-usuario/miapp --health /healthz --public
```

Se hace **una vez** por app. Desde ahí, cada `git push` a `main` del repo de tu app la
despliega.

## Qué necesita tu app

- **Un repo privado en GitHub.** Mientras tu copia de andamio sea privada, GitHub no deja
  que un repo público use su pipeline; `app create` te avisa antes de tocar nada.
- **Un `Dockerfile`.** Es el contrato: con él, cualquier lenguaje funciona. Si no lo tiene,
  andamio te propone uno (ver abajo).
- **Escuchar en `0.0.0.0`**, no en `localhost`, y en el puerto que diga `$PORT` (o el del
  `EXPOSE` de tu Dockerfile).
- Opcional, pero recomendado:
  - una **ruta de salud** que responda `200` cuando la app está lista (por ejemplo
    `/healthz`);
  - una etapa **`test`** en tu Dockerfile: el pipeline la construye antes de desplegar, y si
    falla no se despliega nada.

## Si no tiene Dockerfile

`app create` detecta el lenguaje y te propone uno listo para el pipeline:

| Detecta | Por |
|---|---|
| Node (npm, pnpm, yarn) | `package.json` |
| Python | `requirements.txt` o `pyproject.toml` |
| Go | `go.mod` |
| Sitio estático | `index.html` |

El Dockerfile que genera tiene una etapa `test` si encuentra tests, una imagen final mínima
**sin npm ni pip** (para que el escaneo de vulnerabilidades no la frene) y corre **sin
root**. Antes de subir nada te muestra:

```
Tu app arrancará con:  uvicorn main:app --host 0.0.0.0 --port $PORT
(escucha en el puerto 8000: andamio le pasa $PORT=8000)
¿Arranca así?
```

Si tu app arranca distinto, escribe tu comando. Si respondes solo un número, lo toma como el
puerto. Es tuyo: después cámbialo lo que necesites.

## Qué hace `app create`

1. Revisa el repo de tu app y, si hace falta, genera el Dockerfile.
2. **Revisión previa:** busca lo que haría fallar el primer deploy o perder datos (ver abajo).
3. Crea `apps/miapp/app.yml` en tu copia, sus secretos cifrados y una **llave de deploy**
   que solo puede desplegar esa app.
4. Si pediste `--db` o `--redis`, prepara su usuario y su base.
5. Sube tu copia y la aplica en el servidor (te pide tu contraseña de sudo).
6. Te ofrece subir al repo de tu app lo que le falta: el Dockerfile y
   `.github/workflows/andamio.yml`.
7. Ese push es el **primer deploy**, y lo sigue en tu terminal: secretos, tests, escaneo,
   imagen y deploy. Si falla, te muestra el paso, sus últimas líneas de log y una pista.

## Revisión previa

Antes de registrar nada, andamio lee el código de tu app y te avisa, con el archivo y la
línea:

| Encuentra | Por qué importa |
|---|---|
| Un `.env` subido al repo | **Grave:** tus secretos quedan en el historial de git. Sácalo, cambia esas claves y ponlas con `andamio app secret set` |
| Escucha en `localhost` | **Grave:** dentro del contenedor nadie más llega. Haz que escuche en `0.0.0.0` |
| Un puerto fijo distinto del que se va a usar | Lee el puerto de `PORT`, o crea la app con `--port` |
| Guarda archivos o una base SQLite | En un contenedor se pierden en cada deploy: usa `--volume /data` o `--db` |

Si hay algo grave, te pregunta si seguir igual. Lo que solo corre en tu máquina (el bloque
`if __name__ == "__main__":` cuando el contenedor arranca con uvicorn o gunicorn) no cuenta.

## Opciones

| Opción | Qué hace |
|---|---|
| `--repo dueño/repo` | El repo de tu app |
| `--public` | Accesible desde internet. Sin ella, **solo por la VPN** |
| `--health /ruta` | Ruta de salud: la versión nueva tiene que responder `200` antes de recibir tráfico |
| `--port 3000` | Puerto de tu app (por defecto, el `EXPOSE` del Dockerfile) |
| `--db` | Su propia base y usuario de PostgreSQL (`DATABASE_URL`) |
| `--redis` | Su propio usuario de Redis, limitado a sus claves (`REDIS_URL`) |
| `--host api` | Otro subdominio: `api.tudominio.com`. `--host @` es el dominio raíz |
| `--domain app.suempresa.com` | Un dominio propio además del tuyo |
| `--cors https://miapp.vercel.app` | Permite que ese frontend llame a tu app |
| `--volume /data` | Una carpeta que persiste entre deploys y entra al backup. Se puede repetir. Ver [Administrar una app](/es/docs/apps/manage/#carpetas-persistentes) |
| `--mem 512m` | Límite de memoria (por defecto 256m) |

Ver [Dominios y URLs](/es/docs/apps/domains/) y [Solo el backend](/es/docs/apps/backend-only/).

## `apps/miapp/app.yml`

La definición de tu app, en tu copia. La genera `app create`. Lo más común se cambia sin
editarla, con [`andamio app set`](/es/docs/apps/manage/#cambiar-ram-cpu-puerto-o-acceso)
(RAM, CPU, puerto, salud, acceso); para lo demás, edítala y aplica con `andamio app apply miapp`.

| Clave | Significado |
|---|---|
| `port` | Puerto en el que escucha tu app dentro del contenedor |
| `health` | Ruta HTTP que se consulta antes de que una versión nueva reciba tráfico. Sin ella, se usa el `HEALTHCHECK` de la imagen; sin ninguno, "sana" = 10 s corriendo sin reiniciarse |
| `access` | `vpn` (por defecto) o `public` |
| `db`, `redis` | Su propia base y usuario de PostgreSQL, y su usuario de Redis |
| `migrate` | `{ command: "python manage.py migrate" }`: corre con la imagen de tu app antes de cada deploy |
| `worker` | `{ command: "..." }`: un segundo proceso con la misma imagen |
| `volumes` | `[/data]`: carpetas que persisten entre deploys |
| `resources` | Límites de `mem`, `cpus` y `pids` |
