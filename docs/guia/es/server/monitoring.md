---
title: Monitoreo
description: Métricas siempre; logs, paneles, alertas y chequeo externo si quieres.
---

En tu configuración (`ansible/group_vars/all.yml`):

```yaml
andamio_monitoring: auto
```

| Nivel | Qué corre | RAM |
|---|---|---|
| `minimo` | Prometheus, cAdvisor y node-exporter: métricas del servidor y de cada contenedor | ~115 MiB |
| `completo` | lo anterior, más Loki y Alloy (logs), Grafana (paneles y alertas) y Uptime Kuma (chequeo de tus sitios desde afuera) | ~670 MiB |
| `auto` (por defecto) | `completo` si el servidor tiene 3 GB de RAM o más; si no, `minimo` | |

Para cambiarlo, edita el valor y aplica:

```bash
andamio servidor
```

Bajar a `minimo` apaga lo que sobra. Sus datos (logs, paneles, monitores) quedan: si vuelves
a `completo`, regresan con su historial.

## Alertas al celular

```bash
andamio alertas
```

Con cualquier nivel de monitoreo, también el mínimo, andamio te avisa si:

- un contenedor se cae, se reinicia una y otra vez, o su chequeo de salud falla, por más de
  un minuto (un deploy no dispara nada);
- el disco pasa del 85 %.

Y otro aviso cuando se resuelve. Las apps que detuviste con `andamio app stop` no cuentan.

Los avisos llegan por **ntfy**: una app gratuita (Android, iOS o el navegador) que recibe
notificaciones de un "tema" **sin crear cuenta**. `andamio alertas` inventa un tema largo y
aleatorio, te dice cómo suscribirte (con un código QR) y manda una de prueba desde el
servidor. Si prefieres, usa tu propio servidor ntfy. Con Telegram activado, llegan también
ahí.

`andamio estado` te avisa si nadie te está alertando.

## Dónde verlo

Con el nivel `completo`, por la VPN:

- **Grafana** en `grafana.tudominio.com`: paneles del servidor, de cada contenedor y de los
  logs, y alertas (disco lleno, contenedor caído, certificado por vencer).
- **Uptime Kuma** en `status.tudominio.com`: revisa cada minuto que tus sitios respondan.

## Alertas por Telegram

Con `andamio_telegram: true` y el token del bot y tu chat en `host/sops/telegram-env.sops`:
avisos de deploys fallidos y del backup, un resumen diario del servidor, y un bot que
responde `/system`. Las alertas de Grafana también llegan ahí, con el nivel `completo`.
