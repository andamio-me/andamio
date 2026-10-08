# 0005. Endurecimiento de SSH con drop-in propio y cloud-init desactivado

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
`sshd -T` mostró `passwordauthentication yes` aunque `sshd_config` decía `no`.
Causa: `sshd_config.d/50-cloud-init.conf` (creado por cloud-init de Contabo) se
incluye al principio de `sshd_config`, y en sshd gana el PRIMER valor leído.

Además, el user-data de Contabo trae un `bootcmd` que corre en cada arranque e
intenta poner `PermitRootLogin yes`. No tenía efecto porque la línea existía sin
comentar, pero era frágil. Su `pkill -HUP sshd` fallaba (sshd aún no corre al
inicio del arranque) y dejaba `cloud-init.service` en estado failed.

Revisión: 114 intentos fallidos de bots entre 05:28 y 05:54 UTC del 2026-10-05
(antes de mover SSH al 2222). Los únicos logins aceptados con contraseña fueron
del propio administrador durante la configuración inicial.

## Decisión
- `host/ssh/00-homelab-hardening.conf` en `sshd_config.d/`: solo llave pública,
  sin root, solo el usuario `andamio`. El prefijo `00-` garantiza que gane.
- Borrar `sshd_config.d/50-cloud-init.conf`.
- Desactivar cloud-init con `/etc/cloud/cloud-init.disabled`: ya cumplió el
  aprovisionamiento y su `bootcmd` no debe tocar SSH en cada arranque.

## Consecuencias
- Imposible entrar con contraseña: no hay nada que adivinar por fuerza bruta.
- Verificar SIEMPRE con `sudo sshd -T`, nunca solo leyendo `sshd_config`.
- La red sigue configurada por netplan (`50-cloud-init.yaml` ya existe).
- El "reset de contraseña" del panel de Contabo probablemente deje de funcionar.
  Acceso de emergencia: consola VNC.
