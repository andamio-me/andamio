# 0003. Rotación de logs de Docker y live-restore

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
Por defecto, el driver `json-file` de Docker guarda los logs sin límite de tamaño
y puede llenar el disco. Reiniciar el daemon detiene todos los contenedores.

## Decisión
`/etc/docker/daemon.json` con `json-file`, `max-size: 10m`, `max-file: 3`
(máximo 30 MB por contenedor) y `live-restore: true`.

## Consecuencias
- El disco no se llena por logs.
- Los logs locales son un buffer corto. La retención a largo plazo será Loki (Fase 6).
- Actualizar o reiniciar Docker no detiene los contenedores.
- Solo aplica a contenedores creados después del cambio.
