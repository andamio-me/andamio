# 0026. Tests automáticos de andamio

- **Estado:** Aceptada
- **Fecha:** 2026-10-10

## Contexto
El CI de andamio (0021) revisaba estilo (shellcheck, ansible-lint) y secretos, pero no
comportamiento. Lo más delicado se probaba a mano en un servidor: que `andamio update` no
pise lo tuyo, que el Dockerfile generado construya y arranque, que la revisión previa avise
lo que debe. Para un proyecto abierto, un cambio que rompe algo sin que nadie lo note es el
riesgo principal.

## Decisión
- **pytest**, una sola herramienta. Lo de bash (`andamio app`) se prueba corriendo el
  comando de verdad en una copia de mentira, sin servidor ni cuentas, y sin terminal: cada
  pregunta se responde "no", así que nada sale de la máquina.
- `tools/tests.sh` crea su propio entorno (pytest y PyYAML fijados) en `~/.cache`: no toca
  el Python de nadie, y el CI corre exactamente lo mismo.
- `andamio update` se prueba contra un andamio oficial falso (v1 y v2) y una copia sin
  historial compartido, como una creada desde el template.
- Los Dockerfiles generados se revisan como texto (sin root, `EXPOSE`, sin valores sin
  reemplazar) y, en un job aparte, se **construyen y arrancan** cuatro apps mínimas (Node,
  Python, Go, estático) hasta que responden: es lo que garantiza que funcionan.
- La edición de `app.yml` de `app set` pasó a una función (`andamio _yaml_set`) para
  probarla directo.
- El test del extractor (que nada privado se cuele) se queda en el repo privado; además
  corre los tests públicos dentro de la copia extraída.

## Fuera, por ahora
`alerts.sh` y los playbooks: necesitan Docker en marcha y un servidor. Ansible lo sigue
revisando ansible-lint.

## Consecuencias
- Se probó que los tests detectan fallos reales: romper la edición de `app.yml` o sacar
  tu configuración de lo protegido por `update` los hace fallar.
- El job de Dockerfiles tarda unos 2–4 minutos (baja las imágenes base).
