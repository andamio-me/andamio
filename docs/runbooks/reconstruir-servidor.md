# Runbook: reconstruir el servidor desde cero

Para cuando el VPS se pierde o se cambia de proveedor. Todo se ejecuta desde WSL,
en `~/mi-andamio/ansible`, salvo donde dice "en el servidor".

Requisitos: la llave age en `~/.config/sops/age/keys.txt` de tu WSL (copia en el
gestor de contraseñas). Todos los demás secretos salen del repo cifrado o de restic.

## 1. VPS nuevo
- Ubuntu 24.04, con tu llave pública (`mi-vps-contabo`) para root.
- Si cambió la IP, actualizarla en `~/.ssh/config` (alias `andamio`) y en DuckDNS.
- Borrar la huella vieja: `ssh-keygen -R "[IP]:2222"` y `ssh-keygen -R IP`.

## 2. Bootstrap (crea andamio y mueve SSH al 2222)
~~~bash
ansible-playbook bootstrap.yml -e ansible_user=root -e ansible_port=22
ansible servers -m ping      # ya por el 2222 como andamio
~~~
La última tarea corta la conexión: es lo esperado. La contraseña de sudo que pide
es la nueva de andamio; guárdala en el gestor.

## 3. Sistema base
~~~bash
ansible-playbook site.yml -K --tags base,ssh,firewall,docker
~~~

## 4. Restaurar secretos y datos
Credenciales de restic y Telegram desde el repo cifrado (WSL):
~~~bash
ansible-playbook site.yml -K --tags secretos
~~~
Luego, en el servidor:
~~~bash
sudo bash -c 'set -a; . /etc/restic/env; set +a; restic restore latest --tag andamio --target /'
sudo systemctl restart ssh
~~~
Restaura `/srv/andamio` (repo + `.env`), `/etc/ssh` (misma huella que antes),
`/etc/wireguard`, `/etc/andamio`, `~andamio/.ssh` (deploy key del repo),
`~andamio/.docker/config.json` (login de GHCR) y los dumps en `/var/backups/andamio`.

## 5. Todo lo demás
~~~bash
ansible-playbook site.yml -K
~~~
Si algo falta, el playbook se detiene y dice qué. Al terminar, los stacks están
arriba con volúmenes vacíos.

## 6. Datos
PostgreSQL, Redis y Uptime Kuma: pasos 3 y 4 de `restaurar-backup.md`, usando
`/var/backups/andamio` en vez de `/tmp/restore/var/backups/andamio`.

## 7. Si cambió la IP
| Dónde | Qué |
|---|---|
| `.github/workflows/app-build.yml` | `VPS_HOST` y `VPS_KNOWN_HOSTS`; nuevo tag `app-build-vN` y actualizar el SHA en cada app |
| `stacks/proxy/dynamic/middlewares.yml` | IP del VPS en `vpn-only` |
| `scripts/wg-add-client.sh` | `Endpoint` y `AllowedIPs` |
| Clientes WireGuard (pc, celular) | `Endpoint` y `AllowedIPs` en cada `.conf` |

## 8. Verificar
~~~bash
ansible-playbook site.yml -K      # debe dar changed=0
~~~
Después: dashboard con VPN, un deploy de prueba y `sudo systemctl start andamio-backup`.
