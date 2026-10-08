# Runbook: restaurar desde backup

Antes de necesitarlo de verdad: `sudo scripts/restore-drill.sh` prueba el último
backup contra producción sin tocarla (ADR 0020). Última prueba: 2026-10-08, 72 s.

Requisitos: contraseña de restic y credenciales de B2 (gestor de contraseñas).

## 1. Preparar restic (si el servidor es nuevo)
~~~bash
sudo apt install -y restic
sudo mkdir -p /etc/restic && sudo chmod 700 /etc/restic
# /etc/restic/password  -> la contraseña de restic (chmod 600)
# /etc/restic/env       -> B2_ACCOUNT_ID, B2_ACCOUNT_KEY,
#                          RESTIC_REPOSITORY=b2:mis-backups:homelab,
#                          RESTIC_PASSWORD_FILE=/etc/restic/password (chmod 600)
~~~

## 2. Ver snapshots y restaurar
~~~bash
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic snapshots'
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic restore latest --tag homelab --target /tmp/restore'
~~~
Contenido: `/tmp/restore/srv/homelab` (repo + `.env`) y `/tmp/restore/var/backups/homelab`
(`postgres.sql`, `redis.rdb`).

## 3. PostgreSQL
Con el stack `data` levantado (postgres vacío):
~~~bash
sudo cat /tmp/restore/var/backups/homelab/postgres.sql \
  | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d postgres'
~~~

## 4. Redis
~~~bash
docker compose -f /srv/homelab/infra/stacks/data/compose.yaml stop redis
sudo cp /tmp/restore/var/backups/homelab/redis.rdb \
  "$(docker volume inspect data_redisdata -f '{{.Mountpoint}}')/dump.rdb"
docker compose -f /srv/homelab/infra/stacks/data/compose.yaml start redis
~~~
(Con AOF activo, Redis carga el AOF si existe. Para forzar el RDB, mover antes
`appendonlydir/` fuera del volumen.)

## 5. Seafile (archivos + MariaDB)
Los archivos vienen en `/tmp/restore/srv/homelab/data/seafile` y la base en
`/tmp/restore/var/backups/homelab/seafile-mysql.sql`. Con el stack `seafile` detenido:
~~~bash
docker compose -f /srv/homelab/infra/stacks/seafile/compose.yaml down
sudo rsync -a --delete /tmp/restore/srv/homelab/data/seafile/ /srv/homelab/data/seafile/
docker compose -f /srv/homelab/infra/stacks/seafile/compose.yaml up -d seafile-mysql
sudo cat /tmp/restore/var/backups/homelab/seafile-mysql.sql   | docker exec -i seafile-mysql sh -c 'mariadb -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD"'
docker compose -f /srv/homelab/infra/stacks/seafile/compose.yaml up -d
~~~
Esperar a MariaDB por TCP (`-h 127.0.0.1`): durante su inicialización corre un
servidor temporal que rechaza la contraseña de root.

## 6. Limpiar
~~~bash
sudo rm -rf /tmp/restore
~~~

## Si alguien ocultó los backups (ADR 0014)
La llave del VPS no puede borrar: lo "borrado" queda oculto 30 días. Desde el WSL,
con la master key (nunca en el VPS):
~~~bash
b2 account authorize
b2 ls --recursive --versions b2://mis-backups/homelab/   # ver versiones ocultas
b2 file unhide b2://mis-backups/homelab/<ruta>          # por archivo
b2 account clear
~~~
Después, desde el VPS: `restic snapshots` y `restic check`. Rotar la llave del VPS
(`scripts/b2-create-restic-key.sh`) porque el atacante la conoce.
