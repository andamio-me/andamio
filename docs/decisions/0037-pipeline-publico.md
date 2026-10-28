# 0037. Pipeline público para las apps, con secretos explícitos

- **Estado:** Aceptada
- **Fecha:** 2026-10-27

## Contexto
Cada app despliega llamando al workflow reutilizable `app-build.yml`. Hasta ahora vivía en la copia
privada de cada usuario y la app lo llamaba con `secrets: inherit`. Eso tiene dos límites:

- GitHub no deja que un repo **público** use un workflow de un repo **privado**: `app create`
  tenía que rechazar las apps públicas.
- `secrets: inherit` solo pasa secretos entre repos del **mismo dueño**. Si la app llama al
  workflow del repo público de andamio (otro dueño), no le llegan la llave de deploy ni los
  secretos de build: el build anda, pero el deploy falla siempre.

## Decisión
- La plantilla pública vive en la organización `andamio-me` (`andamio-me/andamio`), y sus
  versiones del pipeline se publican como tags `app-build-vN`.
- Config `andamio_pipeline` (dueño/repo): de ahí sale el pipeline de las apps. `andamio setup`
  la escribe con el repo público. Sin ella, el de la propia copia (como antes).
- La versión se fija por SHA: la del último tag `app-build-v*`, consultado con `git ls-remote`
  (sin token: el repo es público). `andamio app ci-update` mueve las apps a la última.
- La app pasa sus secretos explícitos en un solo paquete:
  `secrets: { ANDAMIO_SECRETS: ${{ toJSON(secrets) }} }`. El workflow saca de ahí la llave de
  deploy (`deploy_key`) y los de `build_secrets`. Si no llega (apps viejas con `inherit`), usa
  `secrets` como antes.
- `forge ci-repin` convierte `secrets: inherit` al formato nuevo al cambiar de versión;
  `forge ci-snippet --inherit` queda para regenerar el archivo de una app fijada a una versión vieja.
- `app create` solo rechaza una app pública si el pipeline vive en un repo privado.

## Consecuencias
- Cualquier usuario, con apps públicas o privadas, usa el mismo pipeline público; las mejoras le
  llegan con `andamio app ci-update`, nunca solas.
- La app le entrega todos sus secretos de Actions al workflow público. Es lo mismo que con
  `inherit`, y el workflow está fijado por SHA: un cambio en el repo público no lo alcanza hasta que
  el usuario actualiza.
- Las versiones `app-build-v11` y anteriores no conocen `ANDAMIO_SECRETS`: a una app fijada ahí no
  se le genera el formato nuevo hasta que actualice.
- Publicar una versión del pipeline = tag `app-build-vN` en `andamio-me/andamio` (tras sincronizar
  la plantilla).
