# 0025. andamio update: parches de upstream sin tocar lo tuyo

- **Estado:** Aceptada
- **Fecha:** 2026-10-09

## Contexto
Cada persona crea su repo desde el template de GitHub. Ese repo nace con un commit propio:
no comparte historial con andamio, así que `git merge` o `git pull` desde upstream no
sirven (historias sin relación, todo choca). Sin un mecanismo, cada instancia se quedaba
congelada en la versión con la que nació, también para los parches de seguridad.

## Decisión
**`bin/andamio update`: fusión de tres vías archivo por archivo** contra el repo público
(URL que el extractor escribe en `bin/andamio`; se puede cambiar con `homelab_upstream` o
`--from`).

- **Lo tuyo no se toca nunca:** `ansible/group_vars`, `ansible/inventory.yml`, `apps/`,
  `host/sops/`, `host/ssh/authorized_keys`, `host/tls/`, `.sops.yaml` y todo `*.sops*`.
- **Base** = la versión de andamio de la que viene el repo. Se guarda en `.andamio/upstream`
  después de cada update. Si no está (la primera vez), se **deduce**: el commit de upstream
  cuyos archivos más coinciden con los locales (hashes de git, sin leer contenidos).
- Por archivo: igual a upstream → nada; sin cambios locales → la versión nueva (incluye
  nuevos, borrados y el bit de ejecución); solo cambios locales → se respetan; cambios de
  los dos → `git merge-file`, con marcas de conflicto si tocan las mismas líneas; borrado
  por un lado y cambiado por el otro → se conserva y se avisa.
- Muestra el log de upstream (marca lo que parece de seguridad) y pide confirmación;
  `--check` solo muestra. Exige el árbol limpio: todo el update queda en `git diff` y se
  deshace con `git reset --hard && git clean -fd`. No hace commit ni toca el servidor.

## Alternativas descartadas
- **`git merge --allow-unrelated-histories`:** la primera vez choca en todos los archivos.
- **Submódulo o paquete aparte para la plataforma:** separa limpio, pero obliga a cada
  persona a entender dos repos, y la plataforma necesita convivir con su configuración en
  el mismo árbol (Ansible, stacks, apps).

## Consecuencias
- Probado con una instancia simulada: base deducida correcta, actualizados, nuevos
  (ejecutables), quitados, combinados, conflicto con marcas, lo propio intacto, y segunda
  corrida "al día".
- Instancias creadas antes de que existiera `update` necesitan copiar `bin/andamio` una vez.
