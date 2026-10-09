# 0024. Capa forge: andamio no habla directo con GitHub

- **Estado:** Aceptada
- **Fecha:** 2026-10-09

## Contexto
Hay quien tiene sus repos en GitLab (u otra forja). andamio llamaba a `gh` en unos 20
lugares repartidos en `bin/andamio`, `bin/andamio-app` y una tarea de Ansible, y tenía `ghcr.io`
fijo en la ruta de las imágenes y en el login del servidor. Soportar otra forja así
significaba tocar todo, con riesgo de romper a quien ya usa GitHub.

## Decisión
**Todo lo que andamio necesita de la forja pasa por `bin/forge`**: unas 20 operaciones
chicas (¿quién soy?, ¿existe el repo?, crear desde plantilla, deploy key de solo lectura,
secreto y variables de CI, llaves de host SSH, permitir reusar el pipeline, el archivo de
CI de una app, registro de imágenes y validar su token). Un subcomando por operación, con
salida simple, para que lo usen igual Python, bash y Ansible.

- `andamio_forge` (por defecto `github`) elige la implementación; `andamio_registry` (por
  defecto `ghcr.io`) el registro de imágenes. Las configuraciones existentes no cambian.
- Hoy hay una sola implementación: GitHub con `gh`. Una forja nueva = una clase con los
  mismos métodos + su pipeline (para GitLab, un `.gitlab-ci.yml` equivalente a
  `app-build.yml`). Nada más de andamio cambia.
- Los tokens van por stdin, nunca como argumento.

## Consecuencias
- Al pasar las variables de CI por forge apareció un bug viejo: se comparaba el puerto
  como número contra el texto que guarda GitHub y se reescribía en cada corrida. Corregido.
- GitLab sigue en la hoja de ruta: falta su clase y su pipeline.
