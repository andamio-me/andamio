# 0010. VPN WireGuard, paneles privados y endurecimiento

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Decisión
- **WireGuard en el host** (`wg0`, `10.8.0.0/24`, puerto 51820/udp). Clientes con
  `scripts/wg-add-client.sh`: `pc` (10.8.0.2), `celular` (10.8.0.3).
  Split tunnel: `AllowedIPs = 10.8.0.0/24, 203.0.113.10/32`.
- **Middleware `vpn-only@file`** (Traefik, `stacks/proxy/dynamic/`): permite VPN,
  contenedores (172.16.0.0/12) y el propio VPS. Aplicado a Grafana y Uptime Kuma.
- **`security-headers@file`** en todo el entrypoint `websecure`: HSTS, frameDeny,
  nosniff, Referrer-Policy, Permissions-Policy, sin `Server`. Calificación A.
- **Traefik sin root**: usuario 65532, `cap_drop: ALL`,
  `net.ipv4.ip_unprivileged_port_start=0` (solo en su namespace de red).

## Auditoría externa (2026-10-06)
- nmap TCP completo: solo 80, 443 y 2222 abiertos; 65 532 filtrados.
- 51820/udp: `open|filtered` (WireGuard no responde sin llave válida).
- Ningún contenedor `privileged`. Root por necesidad: cAdvisor, Alloy, socket-proxy.

## Pendientes conocidos
- **Backups a prueba de borrado**: con root en el VPS se pueden borrar los backups de
  B2. Object Lock o una llave sin permiso de borrado chocan con `restic forget/prune`
  y los bloqueos de restic. Requiere diseño y pruebas.
- **Secretos cifrados en el repo** (sops + age). Hoy: `.env` con `chmod 600`,
  respaldados cifrados en B2.
- Si cambias el estado de la VPN, las sesiones SSH abiertas se cortan (cambia la IP de origen).
