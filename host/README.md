# host/

Configuración del sistema operativo (todo lo que vive fuera de Docker).

## Archivos

| Archivo en el repo | Destino en el servidor | Aplicar con |
|---|---|---|
| `ssh/00-andamio-hardening.conf` | `/etc/ssh/sshd_config.d/00-andamio-hardening.conf` | `sudo sshd -t && sudo systemctl reload ssh` (verificar con `sudo sshd -T`) |
| `systemd/ssh.socket.d/override.conf` | `/etc/systemd/system/ssh.socket.d/override.conf` | `sudo systemctl daemon-reload && sudo systemctl restart ssh.socket` (puerto 2222) |
| `docker/daemon.json` | `/etc/docker/daemon.json` | `sudo dockerd --validate --config-file ...` y `sudo systemctl restart docker` |
| `apt/52andamio-unattended` | `/etc/apt/apt.conf.d/52andamio-unattended` | Se lee en la próxima ejecución de unattended-upgrades |
| `sysctl/99-andamio.conf` | `/etc/sysctl.d/99-andamio.conf` | `sudo sysctl --system` |
| `systemd/cockpit.socket.d/listen.conf` | `/etc/systemd/system/cockpit.socket.d/listen.conf` | `sudo systemctl daemon-reload && sudo systemctl restart cockpit.socket` |
| `systemd/andamio-backup.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now andamio-backup.timer` |
| `systemd/andamio-telegram-bot.service` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now andamio-telegram-bot` |
| `systemd/andamio-daily-summary.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now andamio-daily-summary.timer` |
| `systemd/andamio-container-health.{service,timer}` | `/etc/systemd/system/` | `sudo systemctl daemon-reload && sudo systemctl enable --now andamio-container-health.timer` |
| `polkit/50-andamio-backup.rules` | `/etc/polkit-1/rules.d/` | Se aplica al copiarlo |

## Secretos (fuera del repo, en el gestor de contraseñas)

| Archivo | Contenido |
|---|---|
| `/etc/restic/password` | Contraseña del repositorio restic |
| `/etc/restic/env` | Credenciales de B2 y `KUMA_PUSH_URL` |
| `/etc/andamio/telegram.env` | `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` |
| `/srv/andamio/infra/stacks/*/.env` | Contraseñas de cada stack |

## Cambios sin archivo propio

~~~bash
# Comando `system` y paquetes usados por los scripts
sudo apt install -y restic jq
sudo ln -sf /srv/andamio/infra/scripts/system-status.sh /usr/local/bin/system

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

# Raíz de andamio
sudo mkdir -p /srv/andamio/{infra,apps}
sudo chown -R andamio:andamio /srv/andamio && chmod 750 /srv/andamio
~~~

La red la maneja systemd-networkd (netplan sin `renderer`). NetworkManager no
gestionaba ninguna interfaz.

## Verificar que el servidor coincide con el repo

~~~bash
# Los hashes deben coincidir con los de los archivos del repo
sudo sha256sum /etc/ssh/sshd_config.d/00-andamio-hardening.conf \
  /etc/docker/daemon.json /etc/apt/apt.conf.d/52andamio-unattended \
  /etc/sysctl.d/99-andamio.conf /etc/systemd/system/cockpit.socket.d/listen.conf

# Configuración SSH efectiva
sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|authenticationmethods|allowusers) '
~~~
