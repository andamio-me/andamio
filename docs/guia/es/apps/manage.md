---
title: Administrar una app
description: Listar, ver detalles, cambiar recursos, tareas programadas, ver logs, apagar, volver atrás, aplicar cambios y borrar.
---

## Ver tus apps

```bash
andamio app list
```

```
APP          URL                                ACCESO  ESTADO
blog         https://blog.tudominio.com         public  Up 3 hours (healthy)
panel        https://panel.tudominio.com        vpn     Up 2 days (healthy)
```

## Ver una app

```bash
andamio app info miapp
```

```
  miapp  ● corriendo, arrancó hace 2 h  v 8e71e29
  URL       https://miapp.tudominio.com  (pública)
  Repo      tu-usuario/miapp
  Puerto    3000   salud /healthz
  RAM       256m   usa 74 MiB
  CPU       0.5   usa 0.30%
  Datos     PostgreSQL
  Secretos  ANTHROPIC_API_KEY
```

Lo que dice su `app.yml` y cómo está ahora en el servidor. De los secretos, solo los nombres.

## Cambiar RAM, CPU, puerto o acceso

```bash
andamio app set miapp --mem 512m             # o varios a la vez: --mem 512m --cpus 1
andamio app set miapp --port 8080 --health /healthz
andamio app set miapp --public               # o --vpn: solo desde tu VPN
```

Te muestra el cambio (`resources.mem: 256m → 512m`), pregunta y lo aplica: un reinicio con la
misma imagen, sin deploy. Si cambias el puerto, tu app tiene que escuchar en el nuevo; si para
eso cambiaste el código, haz `git push` (eso despliega).

## Logs en vivo

```bash
andamio app logs miapp
```

## Apagar y encender

```bash
andamio app stop miapp     # la apaga sin borrar nada: datos, base, secretos y dominio quedan
andamio app start miapp    # la vuelve a encender
```

Una app detenida sigue detenida aunque vuelvas a aplicar el servidor, y un `git push` no la
despliega hasta que hagas `start`. Libera su memoria y su CPU.

## Volver atrás

```bash
andamio app rollback miapp
```

Vuelve al deploy exitoso anterior.

## Aplicar cambios

```bash
andamio app apply miapp
```

Aplica en el servidor lo que esté pendiente de esa app (variables guardadas con `--later`,
cambios a mano en `app.yml`), con un solo reinicio. Corre solo las tareas de esa app: tarda
segundos.

## Carpetas persistentes

Un contenedor nuevo arranca vacío en cada deploy: lo que tu app guarde en disco (subidas,
una base SQLite) se pierde. Para lo que debe durar, una carpeta persistente:

```bash
andamio app volume add miapp /data       # o al crearla: --volume /data
andamio app volume list miapp
andamio app volume rm miapp /data        # deja de montarla; los archivos quedan en el servidor
```

- Vive en el servidor en `/srv/andamio/data/apps/miapp/`, y **entra al backup diario**.
- andamio se la da al usuario con el que corre tu imagen: tu app puede escribir aunque corra
  sin root.
- La web y el worker de la app ven la misma carpeta.
- `app destroy` la archiva (en `/srv/andamio/archive/`) antes de borrarla.

:::tip
Para datos con muchas escrituras o varios procesos a la vez, mejor `--db` (PostgreSQL): una
base SQLite en una carpeta persistente funciona, pero el backup copia el archivo tal cual.
:::

## Tareas programadas

Algo que corra solo cada cierto tiempo: limpiar datos viejos, mandar un reporte, sincronizar.

```bash
andamio app cron add miapp "0 3 * * *" "python limpiar.py"         # cada día a las 3:00
andamio app cron add miapp "*/15 * * * *" "node sync.js" --name sync # cada 15 minutos
andamio app cron list miapp       # horario, próxima vez y cómo salió la última
andamio app cron run miapp sync   # correrla ya y ver su salida (para probarla)
andamio app cron rm miapp sync
```

- El horario es el de cron: `minuto hora día mes día-de-la-semana`. Sirven `*/15`, `1-5`,
  `0,30` y los atajos `@hourly`, `@daily`, `@weekly`, `@monthly`.
- **En tu hora**, no la del servidor (UTC): la primera vez andamio toma la zona de tu máquina
  y te la confirma (`andamio_timezone` en tu configuración).
- Corre con **lo mismo que tu app**: su imagen, sus secretos, su base, sus carpetas y sus
  límites de RAM y CPU, en un contenedor aparte que se borra al terminar. No recibe tráfico.
- **Si falla, te avisa al celular** (con [`andamio alertas`](/es/docs/server/monitoring/#alertas-al-celular)),
  con las últimas líneas de su salida: una vez, y otra cuando vuelva a andar. Si pasa de una
  hora, se corta.
- Si el servidor estaba apagado a esa hora, corre al encender. Si todavía sigue corriendo
  cuando le toca otra vez, no se duplica. Una app detenida no corre sus tareas.
- Sin `--name`, el nombre sale del comando (`python limpiar.py` → `limpiar`).

:::note
El comando corre tal cual dentro de la imagen. Si usa `&&`, `|`, `>` o `$VARIABLE`, pasa por
`sh -c`: las imágenes distroless (como la que andamio genera para Go) no traen `sh`, así que
ahí usa un comando simple (`/server limpiar`).
:::

## Borrarla

```bash
andamio app destroy miapp
```

Te pide escribir su nombre para confirmar, y antes de borrar respalda su base y archiva sus
carpetas persistentes. Quita su contenedor, su configuración, su llave de deploy, su base,
su usuario de Redis y sus carpetas.

El repo de la app y sus imágenes en GHCR quedan en GitHub: bórralos tú si ya no los quieres.

## Recursos

Por defecto cada app tiene 256 MB de RAM y media CPU. Para cambiarlo, en
`apps/miapp/app.yml`:

```yaml
resources:
  mem: 512m
  cpus: 1
  pids: 200
```

Y `andamio app apply miapp`.
