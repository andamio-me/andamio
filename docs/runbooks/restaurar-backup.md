# Runbook: restaurar desde backup

Antes de necesitarlo de verdad: `andamio backups` (o `sudo scripts/restore-check.sh` en el
servidor) prueba que el último backup se lee y que sus bases cargan, sin tocar producción.

Requisitos: contraseña de restic y credenciales de B2 (gestor de contraseñas).

## 1. Preparar restic (si el servidor es nuevo)
~~~bash
sudo apt install -y restic
sudo mkdir -p /etc/restic && sudo chmod 700 /etc/restic
# /etc/restic/password  -> la contraseña de restic (chmod 600)
# /etc/restic/env       -> B2_ACCOUNT_ID, B2_ACCOUNT_KEY,
#                          RESTIC_REPOSITORY=b2:mis-backups:andamio,
#                          RESTIC_PASSWORD_FILE=/etc/restic/password (chmod 600)
~~~

## 2. Ver snapshots y restaurar
~~~bash
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic snapshots'
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic restore latest --tag andamio --target /tmp/restore'
~~~
Contenido: `/tmp/restore/srv/andamio` (repo + `.env`) y `/tmp/restore/var/backups/andamio`
(`postgres.sql`, `redis.rdb`).

## 3. PostgreSQL
Con el stack `data` levantado (postgres vacío):
~~~bash
sudo cat /tmp/restore/var/backups/andamio/postgres.sql \
  | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d postgres'
~~~

## 4. Redis
~~~bash
docker compose -f /srv/andamio/infra/stacks/data/compose.yaml stop redis
sudo cp /tmp/restore/var/backups/andamio/redis.rdb \
  "$(docker volume inspect data_redisdata -f '{{.Mountpoint}}')/dump.rdb"
docker compose -f /srv/andamio/infra/stacks/data/compose.yaml start redis
~~~
(Con AOF activo, Redis carga el AOF si existe. Para forzar el RDB, mover antes
`appendonlydir/` fuera del volumen.)

## 5. Stacks propios
Sus carpetas (`andamio_data_dirs`) vienen en `/tmp/restore/srv/andamio/data/<stack>`, y lo que
dejó su `backup-hook.sh` (un dump, un `.tgz`), en `/tmp/restore/var/backups/andamio`. Con el
stack detenido:
~~~bash
docker compose -f /srv/andamio/infra/stacks/<stack>/compose.yaml down
sudo rsync -a --delete /tmp/restore/srv/andamio/data/<stack>/ /srv/andamio/data/<stack>/
docker compose -f /srv/andamio/infra/stacks/<stack>/compose.yaml up -d
~~~
Si su hook dejó un `.tgz` (una copia coherente de la carpeta), úsalo en vez de la carpeta:
`sudo tar xzf /tmp/restore/var/backups/andamio/<stack>.tgz -C /srv/andamio/data/<stack>`.
Una base: cargar su dump con el cliente de su motor, como PostgreSQL en el paso 3.

## 6. Limpiar
~~~bash
sudo rm -rf /tmp/restore
~~~

## Si alguien ocultó los backups (ADR 0014)
La llave del VPS no puede borrar: lo "borrado" queda oculto 30 días. Desde el WSL,
con la master key (nunca en el VPS):
~~~bash
b2 account authorize
b2 ls --recursive --versions b2://mis-backups/andamio/   # ver versiones ocultas
b2 file unhide b2://mis-backups/andamio/<ruta>          # por archivo
b2 account clear
~~~
Después, desde el VPS: `restic snapshots` y `restic check`. Rotar la llave del VPS
(`scripts/b2-create-restic-key.sh`) porque el atacante la conoce.
