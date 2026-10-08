# 0022. Apps de cualquier lenguaje

- **Estado:** Aceptada
- **Fecha:** 2026-10-08

## Contexto
Para que otras personas usen andamio (ver la visión: VPS seguro primero, luego
deploys seguros y aislados), sus apps no pueden tener que ser Node. La etapa de
deploy asumía Node en cinco lugares: el CI corría pnpm, construía la etapa `runtime`,
"sana" era el HEALTHCHECK de la imagen (con wget), el latido del worker usaba `sh`,
`date` y `stat`, y las migraciones exigían una imagen aparte.

## Decisión
**Convención única: la app solo necesita un Dockerfile.** Todo lo demás es opcional y
se declara en `app.yml`:
- **Revisión (app-build-v6):** gitleaks siempre. Si el Dockerfile tiene una etapa
  `test`, el CI la construye y si falla no se despliega: los tests corren con las
  herramientas del lenguaje de la app sin que el CI lo conozca. El flujo pnpm (lint,
  tipos, test) solo si hay `pnpm-lock.yaml`.
- **Etapa a desplegar:** la última del Dockerfile (`target` en el ci.yml si no).
- **Salud (`deploy-app.sh`):** `health: /ruta` en app.yml viaja como label
  `andamio.health`; el deploy la consulta por HTTP **desde el host**, a la IP del
  contenedor y al puerto de Traefik, así que la imagen no necesita curl ni wget. Sin
  `health`, vale el HEALTHCHECK de la imagen; sin ninguno, "sana" = 10 s corriendo sin
  reiniciarse.
- **Worker:** el latido es opcional (`heartbeat: true`).
- **Migraciones:** `migrate: true` (imagen aparte) o `migrate: { command: ... }` con la
  misma imagen de la app.
- **`homelab app create --repo dueño/nombre --port N --health /ruta`** registra un repo
  existente (no crea uno desde la plantilla de Node) e imprime el `ci.yml` a agregar.

## Prueba
`hello-python` (tu-usuario/hello-python): Python solo con librería estándar, imagen
Alpine sin HEALTHCHECK y sin curl/wget/pip, tests con unittest en la etapa `test`.
Registrada con `app create --repo`, desplegada con un push: tests en el CI, Trivy,
salud por `/healthz` desde fuera, en línea por VPN. Las tres apps de Node siguieron
desplegando igual con v6 (`target: runtime`).

## Hallazgos
- **Trivy frena casi cualquier imagen base oficial** por el gestor de paquetes que trae
  (npm en node, pip/setuptools en python), que en producción no se usa. Receta: quitarlo
  de la etapa final. El CI lo sugiere cuando Trivy corta (`::error`).
- **El token de Telegram estaba en la línea de comandos** de `curl` (visible con `ps`
  para cualquier usuario del servidor). Ahora va por un config de curl en un descriptor
  (`-K <(printf ...)`); token rotado.

## Consecuencias
- Una app nueva de cualquier lenguaje necesita: Dockerfile, `app create --repo` y el
  `ci.yml` que imprime. Los tests son responsabilidad de su etapa `test`.
- La plantilla de Node sigue siendo el camino corto para apps nuevas en Next.js.
