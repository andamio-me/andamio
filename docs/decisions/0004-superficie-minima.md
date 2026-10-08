# 0004. Superficie de ataque mínima

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
La auditoría inicial encontró servicios innecesarios en un VPS (ModemManager,
wpa_supplicant, udisks2, fwupd, multipathd, NetworkManager sin interfaces, snapd)
y Cockpit escuchando en todas las interfaces, protegido solo por UFW.

## Decisión
- Bloquear (`mask`) los servicios innecesarios y desinstalar snapd.
- Cockpit solo en `127.0.0.1:9090`; acceso por túnel SSH.
- UFW: solo el puerto 2222 (SSH). Cada puerto abierto debe tener un motivo.
- Se conservan `getty@tty1` y `serial-getty@ttyS0` (acceso de emergencia por VNC).

## Consecuencias
- Menos código corriendo que pueda tener vulnerabilidades.
- Defensa en profundidad: Cockpit no queda expuesto aunque falle el firewall.
- Para revertir un servicio: `systemctl unmask` + `enable --now`.
