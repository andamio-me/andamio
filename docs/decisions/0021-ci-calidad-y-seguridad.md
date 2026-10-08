# 0021. Calidad y seguridad en el CI

- **Estado:** Aceptada
- **Fecha:** 2026-10-08

## Contexto
El pipeline de las apps revisaba lint y tipos, construía y desplegaba. No corría
tests, no revisaba vulnerabilidades de las imágenes ni secretos, y homelab-infra
(scripts y Ansible) no tenía CI.

## Decisión
**Apps (`app-build-v4`):**
- `pnpm test` en la revisión, si la app lo define. short: 35 tests (Vitest) de la
  lógica que importa: validar destinos (sin `javascript:` ni dominios sin punto),
  alfabeto de códigos, reintento ante códigos repetidos, navegador/dispositivo/bot
  y origen sin ruta.
- gitleaks sobre todo el historial antes de construir.
- La imagen se construye **sin publicar**, Trivy la revisa y solo si pasa se sube a
  GHCR: corta con CRITICAL o HIGH que tengan arreglo. La de migraciones se revisa
  solo como informe (corre una vez, en la red interna).
- Trivy fijado por digest y gitleaks por checksum: un tag se puede mover.

**homelab-infra (`infra-ci`):** shellcheck (nivel warning) en scripts, ansible-lint
con las colecciones de `ansible/requirements.yml`, y gitleaks sobre todo el historial.

**Dependabot** en los cinco repos: npm, actions e imagen base en las apps; actions e
imágenes de los stacks en homelab-infra. Un PR semanal agrupado, `cooldown` de 7 días
y sin saltos de versión mayor automáticos. Mezclar un PR de stacks no despliega: se
aplica con `./hl aplicar`.

## Hallazgos al activarlo
- Las 4 imágenes tenían las mismas 7 vulnerabilidades HIGH (brace-expansion, tar,
  undici, ip-address), todas del **npm que trae `node:24-alpine`**, que en producción
  no se usa. La imagen final ya no incluye npm ni corepack: 0 HIGH/CRITICAL.
- gitleaks: ningún secreto en el historial de los 5 repos.
- shellcheck: 0 avisos. ansible-lint: 17 corregidos (`become` explícito junto a
  `become_user`, `changed_when` en comandos que siempre cambian algo, `noqa` en dos
  `run_once` de una herramienta con estrategia lineal). Se omiten `name[template]` y
  `name[casing]` por convención de nombres en español (ver `ansible/.ansible-lint`).

- Al publicar v4, dashboard y andamio se desplegaron a la vez y andamio falló: dos
  `git pull` simultáneos en `/srv/homelab/infra` ("Cannot fast-forward to multiple
  branches"). Producción siguió con la versión anterior. `deploy-app.sh` ahora hace el
  pull con `flock` y explícito (`origin main`).
- Dependabot de las apps no puede leer homelab-infra (privado) para revisar el workflow
  reutilizable: las apps no llevan el ecosistema github-actions; esas actions las
  revisa el Dependabot de homelab-infra.

## Consecuencias
- Un deploy puede frenarse por una vulnerabilidad nueva en una dependencia: es lo
  buscado. Se corrige actualizando (o con el PR de Dependabot) y se vuelve a empujar.
- Repos privados: sin GitHub Advanced Security no hay panel de "code scanning"; los
  resultados quedan en el log del CI.
