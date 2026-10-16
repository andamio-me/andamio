---
title: PostgreSQL, MariaDB y Redis
description: Las bases de datos y el Redis que comparten tus apps, cuánto usan y cómo ajustarlos.
---

Tus apps con `--db` o `--redis` no tienen cada una su servidor de base de datos: comparten un
**PostgreSQL** y un **Redis**, y cada app tiene su propio usuario. En PostgreSQL, su base (no ve
las demás); en Redis, solo sus claves (`miapp:…`). En un VPS chico eso ahorra mucha memoria:
un PostgreSQL por app serían cientos de MB cada uno.

Por eso hay dos niveles de ajustes: los del **servicio**, que valen para todas las apps, y los
de **cada app**, que la limitan para que no acapare lo compartido.

## Ver cómo están

```bash
andamio servicios
```

```
==> PostgreSQL 18.6
  Memoria              1g   (usa 83 MB)
  CPU                  1.5   (0.0 %)
  Conexiones máx.      100   (abiertas 3)
  Memoria por consulta 4MB
==> Redis 8.10.2
  Memoria (datos)      256m   (usa 3 MB)
  CPU                  0.5
  Si se llena          noeviction
```

En el panel, **Servicios** muestra lo mismo y además qué usa cada app: el tamaño de su base,
sus conexiones abiertas, sus límites y sus clientes de Redis.

## Cambiar el servicio

```bash
andamio servicios postgres --mem 2g --cpus 2 --max-connections 150 --work-mem 8MB
andamio servicios redis --mem 512m --cpus 0.5 --policy noeviction
```

| Opción | Qué es | Por defecto |
|---|---|---|
| `postgres --mem` | Toda la memoria de PostgreSQL; el 25 % va a su caché (`shared_buffers`, se calcula sola) | `1g` |
| `postgres --cpus` | Cuántas CPU puede usar como máximo (nunca más que las del servidor) | `1.5` |
| `postgres --max-connections` | Conexiones entre todas las apps (20 a 1000). Cada una ocupa memoria | `100` |
| `postgres --work-mem` | Memoria de una consulta para ordenar y agrupar antes de usar el disco | `4MB` |
| `redis --mem` | La memoria para datos (`maxmemory`); el contenedor tiene 1.5× para guardar en disco | `256m` |
| `redis --cpus` | Cuántas CPU puede usar como máximo | `0.5` |
| `redis --policy` | Qué hace cuando se llena | `noeviction` |
| `redis --engine` | El motor: `redis`, `valkey` o `dragonfly` (abajo) | `redis` |

andamio revisa antes de tocar nada que PostgreSQL y Redis juntos no pasen del **70 % de la
memoria del servidor** (el resto es para tus apps), y que `--max-connections` no quede por
debajo del límite de alguna app. Después lo guarda en tu configuración (un commit), lo sube y
lo aplica: **el servicio se reinicia**, y las apps pierden la conexión unos segundos y se
reconectan solas.

### Si Redis se llena

- **`noeviction`** (recomendado): rechaza escrituras nuevas y no borra nada. Si una app guarda
  colas en Redis (BullMQ, Sidekiq, Celery), es la única segura.
- **`allkeys-lru`**, **`allkeys-lfu`**: borra las claves menos usadas para hacer espacio. Solo
  si tus apps usan Redis como caché: una cola perdería trabajos sin avisar.
- **`volatile-lru`**, **`volatile-lfu`**, **`volatile-ttl`**: borra solo claves con
  vencimiento; si ninguna vence, rechaza escrituras.

## El motor de Redis

Tres motores hablan el mismo protocolo que Redis. Tus apps no cambian nada: siguen usando
`REDIS_URL`, con su mismo usuario y sus mismas claves.

```bash
andamio servicios redis --engine valkey
```

| Motor | Para qué | A tener en cuenta |
|---|---|---|
| **Redis 8** | El de siempre | Licencia AGPL desde Redis 8 |
| **Valkey 9** (recomendado) | La continuación libre de Redis (licencia BSD, de la Linux Foundation) | Mismas opciones y mismo comportamiento: guarda cada segundo (AOF) |
| **Dragonfly 2** | Muchos datos o mucho tráfico: usa varios núcleos y gasta menos memoria | Guarda **cada minuto** y al apagarse, no cada segundo: en un corte de luz podrías perder hasta un minuto. Pide 256 MB por hilo (desde `--mem 256m`). Sin las políticas `volatile-*` |

**Cambiar de motor copia los datos.** Cada motor guarda en un formato de archivo que los
otros no leen, así que andamio:

1. levanta el motor nuevo aparte, con su propio volumen;
2. pausa las escrituras en el actual (las lecturas siguen) y copia todas las claves, por tipo
   y con su vencimiento: textos, hashes, listas, sets, sets ordenados y streams con sus grupos;
3. apaga el actual y deja el nuevo con el nombre `redis`.

Las escrituras esperan unos segundos; las apps con ioredis o BullMQ las reenvían solas al
reconectarse. Si algo falla antes del paso 3, el motor actual sigue como estaba. El volumen del
anterior queda, y volver es otro cambio de motor.

Lo que **no** viaja: los mensajes de un stream entregados y todavía sin confirmar, y las claves
de tipos de módulos (si hay alguna, andamio no cambia de motor y te dice cuáles).

Con cualquier motor, andamio comprueba al final que pida clave: un motor que no pudiera leer
sus usuarios quedaría abierto, y eso hace fallar el cambio en vez de pasar en silencio.

## MariaDB (MySQL)

Para apps que usan MySQL: Laravel, WordPress, PHP en general, o Node con `mysql2`. Es
**MariaDB 11.8**, compatible con MySQL, con el mismo modelo que PostgreSQL: un servidor para todas
las apps, y cada una con su base y su usuario, que no ve las demás bases, no puede crear otras ni
leer archivos del servidor.

```bash
andamio app create miapp --repo yo/miapp --mysql
```

La app recibe:

| Variable | Valor |
|---|---|
| `MYSQL_URL` | `mysql://miapp:…@mariadb:3306/miapp` |
| `DB_CONNECTION`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` | Las de Laravel, listas (solo si la app no tiene también `--db`) |

No recibe `DATABASE_URL`: esa es la de PostgreSQL. Con Prisma o Drizzle, apunta a `MYSQL_URL`
(`url = env("MYSQL_URL")`).

- **Solo corre si alguna app la usa.** La primera app con `--mysql` la enciende (unos 150 MB de
  RAM, 512 MB como máximo); mientras ninguna la use, no gasta nada.
- **Respaldo diario:** un dump completo, coherente y sin bloquear tablas, junto al de PostgreSQL.
- **Al borrar una app** (`andamio app destroy`), su base se respalda en `/srv/andamio/archive/`
  antes de borrarla, como la de PostgreSQL.
- Sin puerto público, como PostgreSQL y Redis.
- **En el panel:** **Nueva app** la marca sola si el código la declara (`DB_CONNECTION=mysql`,
  `mysql2`, Prisma con `provider = "mysql"`, `mysqlclient`, `go-sql-driver/mysql`…); nunca por el
  lenguaje, porque Laravel también puede usar PostgreSQL. **Servicios** muestra su memoria,
  conexiones y el tamaño de cada base, y cambia su configuración:

  ```bash
  andamio servicios mariadb --mem 1g --cpus 1 --max-connections 150
  ```

- **Consola SQL de solo lectura**, como la de PostgreSQL: `andamio app sql miapp` (con las dos
  bases, `--mysql` elige MariaDB), o **Base de datos** en el panel. Entra con un usuario aparte que
  solo puede leer, solo desde dentro del servidor de MariaDB, con 5 s por consulta.
- Al borrar la última app que la usa, se apaga sola (su volumen queda).

## Limitar una app

```bash
andamio app set miapp --db-connections 20    # cuántas conexiones puede abrir (0 = sin límite)
andamio app set miapp --db-timeout 30s       # cuánto puede durar una consulta (0 = sin límite)
```

- **Conexiones:** una app con un error que abre conexiones sin cerrarlas (o con varios
  grupos de conexiones a la vez) no deja sin base a las demás: llega a su límite y se queda ahí.
- **Tiempo por consulta:** una consulta colgada se corta en vez de bloquear la base. Vale para
  conexiones nuevas, así que andamio reinicia la app al cambiarlo.

Valen para su base, sea PostgreSQL o MariaDB. Se guardan en su `app.yml` (`db_connections`,
`db_timeout`) y se aplican sin redesplegar. En el
panel, en los **Ajustes** de la app, sección **Límites de la base**.

## Lo que no se hace

PostgreSQL y Redis **no tienen puerto público**, a propósito. Para consultar la base de una app
desde tu máquina está la consola SQL (`andamio app sql miapp`, o **Base de datos** en el
panel), que entra con un usuario de solo lectura; o tu VPN.
