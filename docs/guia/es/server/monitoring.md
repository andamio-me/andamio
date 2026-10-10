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

## Dónde verlo

Con el nivel `completo`, por la VPN:

- **Grafana** en `grafana.tudominio.com`: paneles del servidor, de cada contenedor y de los
  logs, y alertas (disco lleno, contenedor caído, certificado por vencer).
- **Uptime Kuma** en `status.tudominio.com`: revisa cada minuto que tus sitios respondan.

## Alertas por Telegram

Con `andamio_telegram: true` y el token del bot y tu chat en `host/sops/telegram-env.sops`:
avisos de deploys fallidos y del backup, un resumen diario del servidor, y un bot que
responde `/system`. Las alertas de Grafana también llegan ahí, con el nivel `completo`.
