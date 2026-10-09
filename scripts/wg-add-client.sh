#!/usr/bin/env bash
# Crea un cliente WireGuard. Uso: sudo wg-add-client.sh <nombre> <último octeto 2-254>
set -euo pipefail
# ANDAMIO_SERVER_IP: de andamio.env (Ansible, group_vars/all.yml) o del entorno (en un
# servidor nuevo, el rol wireguard crea el primer cliente antes de que exista andamio.env).
# shellcheck source=/dev/null
[ -f /etc/andamio/andamio.env ] && . /etc/andamio/andamio.env
: "${ANDAMIO_SERVER_IP:?falta ANDAMIO_SERVER_IP (/etc/andamio/andamio.env)}"

NAME=${1:?uso: wg-add-client.sh <nombre> <ip 2-254>}
OCT=${2:?uso: wg-add-client.sh <nombre> <ip 2-254>}
[[ $NAME =~ ^[a-z0-9-]+$ ]] || { echo "Nombre inválido"; exit 1; }
[[ $OCT =~ ^[0-9]+$ ]] && (( OCT >= 2 && OCT <= 254 )) || { echo "IP inválida"; exit 1; }

DIR=/etc/wireguard/clients
install -d -m 700 "$DIR"
[ -e "$DIR/$NAME.conf" ] && { echo "Ya existe el cliente $NAME"; exit 1; }
grep -q "AllowedIPs = 10.8.0.$OCT/32" /etc/wireguard/wg0.conf && { echo "La IP 10.8.0.$OCT ya está en uso"; exit 1; }

umask 077
PRIV=$(wg genkey); PUB=$(printf '%s' "$PRIV" | wg pubkey); PSK=$(wg genpsk)

cat >> /etc/wireguard/wg0.conf << EOF

[Peer]
# $NAME
PublicKey = $PUB
PresharedKey = $PSK
AllowedIPs = 10.8.0.$OCT/32
EOF

cat > "$DIR/$NAME.conf" << EOF
[Interface]
PrivateKey = $PRIV
Address = 10.8.0.$OCT/32

[Peer]
PublicKey = $(cat /etc/wireguard/server.pub)
PresharedKey = $PSK
Endpoint = $ANDAMIO_SERVER_IP:51820
AllowedIPs = 10.8.0.0/24, $ANDAMIO_SERVER_IP/32
PersistentKeepalive = 25
EOF

wg syncconf wg0 <(wg-quick strip wg0)
echo "Cliente '$NAME' creado con IP 10.8.0.$OCT -> $DIR/$NAME.conf"
