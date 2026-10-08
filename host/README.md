# host/

Configuración del sistema operativo (todo lo que vive fuera de Docker).

## Archivos

| Archivo en el repo | Destino en el servidor | Aplicar con |
|---|---|---|
| `ssh/00-homelab-hardening.conf` | `/etc/ssh/sshd_config.d/00-homelab-hardening.conf` | `sudo sshd -t && sudo systemctl reload ssh` (verificar con `sudo sshd -T`) |
| `systemd/ssh.socket.d/override.conf` | `/etc/systemd/system/ssh.socket.d/override.conf` | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` (puerto 2222) |
| `docker/daemon.json` | `/etc/docker/daemon.json` | `sudo dockerd --validate --config-file ...` y `sudo systemctl restart docker` |
| `apt/52homelab-unattended` | `/etc/apt/apt.conf.d/52homelab-unattended` | Se lee en la próxima ejecución de unattended-upgrades |
| `sysctl/99-homelab.conf` | `/etc/sysctl.d/99-homelab.conf` | `sudo sysctl --system` |
| `systemd/cockpit.socket.d/listen.conf` | `/etc/systemd/system/cockpit.socket.d/listen.conf` | `sudo systemctl daemon-reload && sudo systemctl restart cockpit.socket` |
| `systemd/homelab-backup.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now homelab-backup.timer` |
| `systemd/homelab-telegram-bot.service` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now homelab-telegram-bot` |
| `systemd/homelab-daily-summary.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now homelab-daily-summary.timer` |
| `systemd/homelab-container-health.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now homelab-container-health.timer` |
| `polkit/50-homelab-backup.rules` | `/etc/polkit-1/rules.d/` | Se aplica al copiarlo |

## Secretos (fuera del repo, en el gestor de contraseñas)

| Archivo | Contenido |
|---|---|
| `/etc/restic/password` | Contraseña del repositorio restic |
| `/etc/restic/env` | Credenciales de B2 y `KUMA_PUSH_URL` |
| `/etc/homelab/telegram.env` | `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` |
| `/srv/homelab/infra/stacks/*/.env` | Contraseñas de cada stack |

## Cambios sin archivo propio

~~~bash
# Comando `system` y paquetes usados por los scripts
sudo apt install -y restic jq
sudo ln -sf /srv/homelab/infra/scripts/system-status.sh /usr/local/bin/system

# SSH: quitar el archivo de cloud-init que activaba contraseñas
sudo rm /etc/ssh/sshd_config.d/50-cloud-init.conf

# cloud-init: desactivado tras el aprovisionamiento (ver ADR 0005)
sudo touch /etc/cloud/cloud-init.disabled

# Zona horaria
sudo timedatectl set-timezone UTC

# Swap de 4 GB
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo systemctl daemon-reload && sudo findmnt --verify

# Servicios innecesarios en un VPS
sudo systemctl disable --now ModemManager udisks2 fwupd fwupd-refresh.timer multipathd multipathd.socket
sudo systemctl mask ModemManager udisks2 fwupd multipathd multipathd.socket
sudo systemctl disable --now NetworkManager NetworkManager-wait-online NetworkManager-dispatcher wpa_supplicant
sudo systemctl mask NetworkManager wpa_supplicant
sudo apt purge -y snapd

# Raíz del homelab
sudo mkdir -p /srv/homelab/{infra,apps}
sudo chown -R andamio:andamio /srv/homelab && chmod 750 /srv/homelab
~~~

La red la maneja systemd-networkd (netplan sin `renderer`). NetworkManager no
gestionaba ninguna interfaz.

## Verificar que el servidor coincide con el repo

~~~bash
# Los hashes deben coincidir con los de los archivos del repo
sudo sha256sum /etc/ssh/sshd_config.d/00-homelab-hardening.conf \
  /etc/docker/daemon.json /etc/apt/apt.conf.d/52homelab-unattended \
  /etc/sysctl.d/99-homelab.conf /etc/systemd/system/cockpit.socket.d/listen.conf

# Configuración SSH efectiva
sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|authenticationmethods|allowusers) '
~~~
