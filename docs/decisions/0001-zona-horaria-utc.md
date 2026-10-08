# 0001. Servidor en UTC

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
Contabo entrega el servidor en `Europe/Berlin`, que tiene horario de verano.
Con DST, una tarea de cron puede no ejecutarse o ejecutarse dos veces al año.

## Decisión
El servidor usa `UTC`.

## Alternativas
- `Europe/Berlin`: horario de verano, sin relación con mi ubicación.
- `America/Bogota`: coincide con mi hora, pero no es estándar en servidores.

## Consecuencias
- Sin saltos de hora. Logs comparables entre sistemas.
- Las horas de cron y timers se escriben en UTC (Colombia = UTC − 5).
- Grafana y Uptime Kuma muestran la hora local del navegador.
