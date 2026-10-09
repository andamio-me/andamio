# Runbook: agregar una app

Todo desde el WSL. Requisitos: `gh` autenticado, llave age en
`~/.config/sops/age/keys.txt` y `andamio` sin cambios pendientes.

## 1. Crear
~~~bash
andamio app create <nombre> [--repo dueño/repo] [--public] [--db] [--redis] [--host <sub>] [--mem 256m]
~~~
- Sin `--public`, la app solo se abre con la VPN (`vpn-only`).
- `--db`: usuario y base propios en PostgreSQL (`DATABASE_URL`) y migraciones Prisma.
- `--redis`: usuario de Redis propio; solo claves y canales `<nombre>:*` (`REDIS_URL`).

Hace: repo privado desde `tu-plantilla`, `apps/<nombre>/app.yml`, secretos
cifrados, llave de deploy (privada como secret `DEPLOY_SSH_KEY` en GitHub), compose,
commit + push de `andamio` y `./hl aplicar andamio` (pide la contraseña de sudo).

El CI de "Initial commit" del repo nuevo falla (aún no había llave): es esperado.

## 2. Primer deploy
~~~bash
cd ~/projects/<nombre>
git commit --allow-empty -m "primer deploy" && git push
~~~

## 3. Día a día
~~~bash
andamio app list                 # apps, URL, acceso y estado
andamio app logs <nombre>        # logs en vivo
andamio app rollback <nombre>    # volver al deploy exitoso anterior
~~~

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
- Ejemplo real: `shortener` (BullMQ, cola `shortener:bull:clicks`).

## Cambiar algo de una app
- Recursos, acceso, host: editar `apps/<nombre>/app.yml`, `cd ansible && ansible-playbook apps.yml`,
  commit + push y `./hl aplicar andamio`.
- Un secreto o variable: `andamio app secret set <nombre> <CLAVE>` (cifra, commit, push y aplica).
- Rotar la llave de deploy: borrar `apps/<nombre>/deploy_key.pub` y seguir como arriba.

## Quitar una app (manual por ahora)
Borrar `apps/<nombre>/`, commit + push y `./hl aplicar andamio` (revoca su llave y la
quita del registro). En el servidor: `docker compose down` en su carpeta. La base y el
usuario de Redis se borran a mano, después de un backup.
