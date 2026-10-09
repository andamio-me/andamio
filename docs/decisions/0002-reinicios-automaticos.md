# 0002. Reinicios automáticos para parches del kernel

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
unattended-upgrades instala parches de seguridad a diario, pero los del kernel
solo se aplican al reiniciar. Sin reinicio, el kernel en memoria sigue vulnerable.

## Decisión
Reinicio automático a las 08:00 UTC (03:00 Colombia) cuando exista
`/var/run/reboot-required`. Se limpian kernels y dependencias sin uso.
Configuración: `host/apt/52andamio-unattended`.

## Alternativas
- Reiniciar a mano: depende de acordarse; el kernel queda sin parchear.
- Livepatch (Ubuntu Pro): sin reinicios, pero requiere cuenta y no cubre todo.

## Consecuencias
- ~1 minuto de caída unas pocas veces al mes, de madrugada.
- Todos los servicios deben volver solos tras un reinicio (systemd enabled,
  contenedores con `restart: unless-stopped`).
