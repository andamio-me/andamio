# 0012. Servidor reproducible con Ansible

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Decisión
- **Ansible desde WSL** (pipx, sin agente en el servidor). Un playbook `site.yml`
  con seis roles: `base`, `ssh`, `firewall`, `docker`, `wireguard`, `homelab`.
  `bootstrap.yml` solo para el primer acceso a un VPS nuevo.
- **`host/` sigue siendo la fuente de verdad.** Los roles copian esos archivos;
  no hay plantillas con una segunda copia de la configuración.
- **Los secretos no se generan ni se versionan.** El playbook comprueba que
  existan y se detiene diciendo cuál falta. Se restauran desde restic; las
  credenciales de restic viven solo en el gestor de contraseñas.
- **La contraseña de sudo se escribe en cada ejecución** (`-K`), no se guarda.
- **Siempre `--check --diff` antes de aplicar** en el servidor en producción.

## Al adoptarlo se encontraron
- El puerto 2222 venía de un override de `ssh.socket` que no estaba en el repo:
  reconstruir habría dejado SSH en el 22, bloqueado por UFW.
- Las llaves autorizadas no estaban en el repo (y había una línea de plantilla
  `LLAVE_PUBLICA`, inválida).
- El backup no cubría `/etc/ssh`, `/etc/wireguard`, `/etc/homelab`, la deploy key
  ni el login de GHCR.

## Consecuencias
- Aplicado al servidor actual: `changed=0` en la segunda ejecución (idempotente).
- La reconstrucción completa (`docs/runbooks/reconstruir-servidor.md`) aún no se
  ha probado en un VPS desechable. Hasta entonces, `bootstrap.yml` no está probado.
- Editar el repo desde Windows (`\\wsl.localhost`) puede quitar el bit de
  ejecución: revisar `git diff` antes de cada commit.
