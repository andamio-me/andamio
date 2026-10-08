#!/usr/bin/env bash
# Crea la llave de B2 que usa restic en el VPS: un solo bucket y SIN deleteFiles
# (restic oculta en vez de borrar; ADR 0014). Se corre en tu WSL, nunca en el VPS.
#
# Por qué no `b2 key create`: el CLI nuevo crea llaves multi-bucket, que solo
# sirven con b2_authorize_account v4, y restic se autoriza con v3.
#
# Uso: scripts/b2-create-restic-key.sh   (pide la master key; no la guarda)
set -euo pipefail

BUCKET=mis-backups
NAME=restic-vps-sin-borrar
CAPS='["listBuckets","listFiles","readFiles","writeFiles"]'

read -rsp "Master keyID: " KID; echo
read -rsp "Master applicationKey: " KEY; echo

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

auth=$(curl -fsS -u "$KID:$KEY" https://api.backblazeb2.com/b2api/v3/b2_authorize_account)
unset KEY
api=$(json 'd["apiInfo"]["storageApi"]["apiUrl"]' <<< "$auth")
token=$(json 'd["authorizationToken"]' <<< "$auth")
account=$(json 'd["accountId"]' <<< "$auth")

bucket_id=$(curl -fsS -H "Authorization: $token" "$api/b2api/v3/b2_list_buckets" \
  -d "{\"accountId\":\"$account\",\"bucketName\":\"$BUCKET\"}" | json 'd["buckets"][0]["bucketId"]')

key=$(curl -fsS -H "Authorization: $token" "$api/b2api/v3/b2_create_key" \
  -d "{\"accountId\":\"$account\",\"keyName\":\"$NAME\",\"bucketId\":\"$bucket_id\",\"capabilities\":$CAPS}")

echo
echo "Llave creada ($NAME). Cópiala a /etc/restic/env en el VPS:"
json '"B2_ACCOUNT_ID=" + d["applicationKeyId"]' <<< "$key"
json '"B2_ACCOUNT_KEY=" + d["applicationKey"]' <<< "$key"
json '"Permisos: " + ",".join(d["capabilities"])' <<< "$key"
