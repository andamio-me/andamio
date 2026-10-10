# Runbook: agregar una app

Todo desde tu máquina (WSL, Linux o macOS). `andamio` funciona en cualquier carpeta: dentro
de tu copia usa esa; afuera, la de `andamio use`. Requisitos: `gh` con sesión, la llave age
en `~/.config/sops/age/keys.txt` y tu copia sin cambios pendientes.

## 1. Registrar
~~~bash
andamio app create <nombre> --repo dueño/repo [--health /healthz] [--public] [--db] [--redis] [--host <sub>|@] [--mem 256m]
~~~
- El repo de la app, en cualquier lenguaje. Sin `Dockerfile`, andamio detecta Node, Python,
  Go o un sitio estático y propone uno (confirmas el comando de arranque antes de subir nada).
- Hoy el repo de la app tiene que ser **privado**: el pipeline vive en tu copia (privada) y
  GitHub no deja que un repo público lo use. `app create` lo avisa antes de tocar nada.
- Sin `--public`, la app solo se abre con la VPN (`vpn-only`).
- `--db`: usuario y base propios en PostgreSQL (`DATABASE_URL`). `--redis`: usuario de Redis
  propio; solo claves y canales `<nombre>:*` (`REDIS_URL`).

Hace: `apps/<nombre>/app.yml`, secretos cifrados, llave de deploy (la privada, como secret
`DEPLOY_SSH_KEY` del repo de la app), compose, commit + push de tu copia y la aplica en el
servidor (pide la contraseña de sudo). Después ofrece subir al repo de la app el Dockerfile
y `.github/workflows/andamio.yml`: ese push es el primer deploy, y lo sigue en la terminal.
Si falla, muestra el paso, sus últimas líneas de log, una pista (💡) y el link.

## 2. Día a día
Cada `git push` a `main` del repo de la app despliega (tests, escaneo, build, deploy sin
caída). Si la versión nueva no queda sana, sigue corriendo la anterior.
~~~bash
andamio app list                 # apps, URL, acceso y estado
andamio app logs <nombre>        # logs en vivo
andamio app rollback <nombre>    # volver al deploy exitoso anterior
andamio app stop|start <nombre>  # apagarla sin borrar nada / volver
~~~

## Variables y secretos
~~~bash
andamio app secret set <nombre> <CLAVE>            # cifra, commit, push y aplica (reinicia la app)
andamio app secret set <nombre> <CLAVE> --later    # solo guarda: para juntar varias...
andamio app apply <nombre>                         # ...y aplicarlas de una vez
andamio app secret list <nombre>                   # solo nombres
~~~
Mismo nombre = reemplaza el valor. Si el último deploy falló (típico: faltaba la variable),
`secret set` y `app apply` ofrecen reintentarlo.

## Worker (procesos en segundo plano)
Agregar a `apps/<nombre>/app.yml`:
~~~yaml
worker:
  command: node worker.cjs   # misma imagen que la web, otro proceso
  mem: 192m                  # opcional (256m); también cpus (0.25)
~~~
- El worker debe escribir la hora actual en `/tmp/heartbeat` cada pocos segundos: es
  su healthcheck (enfermo si el latido tiene más de 60 s). Contenido que cambie: un
  archivo vacío reescrito vacío puede no actualizar su fecha.
- El deploy lo reemplaza cuando la web nueva ya está sana; si el worker nuevo no
  late, todo vuelve a la versión anterior.
- Orden la primera vez: desplegar la imagen que ya trae el worker y **después**
  agregar `worker:` al app.yml (si no, arranca con una imagen sin el archivo).

## Cambiar algo de una app
- Dominio propio o CORS: `andamio app domain|cors add|rm|list <nombre> [valor]`.
- RAM, CPU, puerto, salud, acceso: `andamio app set <nombre> --mem 512m` (`--cpus`, `--port`,
  `--health`, `--public`, `--vpn`). Un reinicio, sin deploy. Ver cómo está: `andamio app info <nombre>`.
- Lo demás (host, worker...): editar `apps/<nombre>/app.yml` y `andamio app apply <nombre>`
  (regenera el compose, commitea, sube y aplica).
- Rotar la llave de deploy: borrar `apps/<nombre>/deploy_key.pub` y seguir como arriba.

## Quitar una app
~~~bash
andamio app destroy <nombre>   # pide escribir su nombre; respalda su base antes
~~~
Revoca su llave, quita su configuración, su contenedor, su base y su usuario de Redis.
El repo de la app y sus imágenes en GHCR quedan: bórralos tú si ya no los quieres.
