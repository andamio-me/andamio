# 0009. Observabilidad: Uptime Kuma, Prometheus, Loki, Grafana y bot de Telegram

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Decisión
- **Uptime Kuma** (`stacks/uptime-kuma`, público con login + 2FA): disponibilidad,
  expiración de certificados y "dead man's switch" del backup (push, 25 h).
- **Prometheus + node-exporter + cAdvisor** (`stacks/monitoring`, red `monitoring`
  internal): métricas del host, por contenedor y de Traefik. Retención 30 días / 5 GB.
- **Loki + Alloy**: logs de todos los contenedores y del journal de systemd. 30 días.
- **Grafana** (público con login): dashboards (1860, 14282, 17346) y alertas
  aprovisionadas desde el repo, enviadas a Telegram.
- **Bot de Telegram** (`homelab-telegram-bot.service`): `/system`, `/containers`,
  `/logs`, `/certs`, `/backup_now`. Long polling (sin puertos), solo el chat del dueño,
  lista blanca de comandos. Resumen diario a las 13:00 UTC.

## Riesgos aceptados
- **cAdvisor monta el socket de containerd** (equivale a root). Sin él no puede
  nombrar los contenedores. Mitigación: sin puertos, solo en la red `monitoring`,
  `no-new-privileges`. Alternativas descartadas: sin métricas por contenedor, o una
  versión vieja sin parches.
- El socket-proxy permite leer `CONTAINERS`, `INFO` y `NETWORKS` (Traefik, cAdvisor, Alloy).
- node-exporter no usa la red del host: sus métricas de red son las de su contenedor.
- Kuma y Grafana son públicos (protegidos por login). Pasarán a la VPN en la Fase 7.

## Notas
- Las alertas usan `container_memory_working_set_bytes`, no `usage` (incluye caché).
- En provisioning, `$` se interpreta como variable de entorno: en las plantillas de
  alertas se usa `.Values` / `.Labels` en lugar de `$values` / `$labels`.
- El bot usa polkit (no sudo) para lanzar el backup: `NoNewPrivileges` bloquea setuid.
