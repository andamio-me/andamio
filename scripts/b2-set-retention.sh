#!/usr/bin/env bash
# Cambia la retención por defecto de Object Lock de un bucket de B2 a GOVERNANCE.
# La web de Backblaze solo ofrece "compliance" (nadie puede levantarlo, ni la master
# key); governance protege igual de las llaves de las apps pero deja una salida con
# la master key. Solo afecta lo que se suba de ahí en adelante.
# Se corre en tu WSL (pide la master key; no la guarda).
#
# Uso: scripts/b2-set-retention.sh <bucket> [días=30]
set -euo pipefail

BUCKET=${1:?uso: b2-set-retention.sh <bucket> [días]}
DAYS=${2:-30}
[[ $DAYS =~ ^[0-9]+$ ]] || { echo "Días inválidos"; exit 1; }

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

curl -fsS -H "Authorization: $token" "$api/b2api/v3/b2_update_bucket" -d "{
  \"accountId\": \"$account\",
  \"bucketId\": \"$bucket_id\",
  \"defaultRetention\": {\"mode\": \"governance\", \"period\": {\"duration\": $DAYS, \"unit\": \"days\"}}
}" | json '"Retención por defecto de " + d["bucketName"] + ": " + str(d["fileLockConfiguration"]["value"]["defaultRetention"])'
