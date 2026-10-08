#!/usr/bin/env bash
# Crea una llave de B2 limitada a UN bucket y la guarda cifrada (sops) en un
# secrets.sops.env, sin mostrarla. Antes revisa la configuración del bucket.
# Se corre en tu WSL, nunca en el VPS (pide la master key; no la guarda).
#
# Uso: scripts/b2-create-app-key.sh <bucket> <nombre-llave> <capacidades> <archivo.sops.env>
# Ej.: scripts/b2-create-app-key.sh mi-bucket nextcloud-nube \
#        listBuckets,readBuckets,listFiles,readFiles,writeFiles,deleteFiles stacks/nextcloud/secrets.sops.env
#
# Llave de bucket único creada por la API v3 (ver b2-create-restic-key.sh y ADR 0014).
# Variables que agrega: OBJECTSTORE_S3_KEY y OBJECTSTORE_S3_SECRET.
set -euo pipefail

BUCKET=${1:?uso: b2-create-app-key.sh <bucket> <nombre> <capacidades> <archivo.sops.env>}
NAME=${2:?falta el nombre de la llave}
CAPS=${3:?faltan las capacidades}
SOPS_FILE=${4:?falta el archivo .sops.env}
cd "$(dirname "$0")/.."
[ -f "$SOPS_FILE" ] || { echo "No existe $SOPS_FILE"; exit 1; }

read -rsp "Master keyID: " KID; echo
read -rsp "Master applicationKey: " KEY; echo

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
auth=$(curl -fsS -u "$KID:$KEY" https://api.backblazeb2.com/b2api/v3/b2_authorize_account)
unset KEY
api=$(json 'd["apiInfo"]["storageApi"]["apiUrl"]' <<< "$auth")
token=$(json 'd["authorizationToken"]' <<< "$auth")
account=$(json 'd["accountId"]' <<< "$auth")

bucket=$(curl -fsS -H "Authorization: $token" "$api/b2api/v3/b2_list_buckets" \
  -d "{\"accountId\":\"$account\",\"bucketName\":\"$BUCKET\"}" | json 'd["buckets"][0]')

echo "== Bucket $BUCKET"
python3 - "$bucket" <<'PY'
import ast, sys
b = ast.literal_eval(sys.argv[1])
lock = b.get("fileLockConfiguration", {}).get("value") or {}
ret = (lock.get("defaultRetention") or {})
period = ret.get("period") or {}
enc = (b.get("defaultServerSideEncryption", {}).get("value") or {}).get("mode")
rules = b.get("lifecycleRules") or []
ok = lambda c: "OK " if c else "FALTA"
print(f"  [{ok(b.get('bucketType') == 'allPrivate')}] privado: {b.get('bucketType')}")
print(f"  [{ok(enc == 'SSE-B2')}] cifrado por defecto: {enc}")
print(f"  [{ok(lock.get('isFileLockEnabled'))}] Object Lock: {lock.get('isFileLockEnabled')}")
print(f"  [{ok(ret.get('mode') == 'governance' and period.get('duration') == 30)}] retención: {ret.get('mode')} {period.get('duration')} {period.get('unit')}")
print(f"  [{ok(any(r.get('daysFromHidingToDeleting') == 30 for r in rules))}] ciclo de vida: {rules}")
PY
read -rp "¿Crear la llave '$NAME' para este bucket? [s/N] " ok; [[ $ok =~ ^[sS]$ ]] || { echo "Cancelado"; exit 1; }

caps_json=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1].split(',')))" "$CAPS")
bucket_id=$(json 'd["bucketId"]' <<< "$(python3 -c 'import ast,json,sys; print(json.dumps(ast.literal_eval(sys.argv[1])))' "$bucket")")
key=$(curl -fsS -H "Authorization: $token" "$api/b2api/v3/b2_create_key" \
  -d "{\"accountId\":\"$account\",\"keyName\":\"$NAME\",\"bucketId\":\"$bucket_id\",\"capabilities\":$caps_json}")

umask 077; tmp=$(mktemp); trap 'shred -u "$tmp" 2>/dev/null || true' EXIT
sops decrypt "$SOPS_FILE" | grep -vE '^OBJECTSTORE_S3_(KEY|SECRET)=' > "$tmp"
json '"OBJECTSTORE_S3_KEY=" + d["applicationKeyId"]' <<< "$key" >> "$tmp"
json '"OBJECTSTORE_S3_SECRET=" + d["applicationKey"]' <<< "$key" >> "$tmp"
sops encrypt --input-type dotenv --output-type dotenv --filename-override "$SOPS_FILE" "$tmp" > "$SOPS_FILE.new"
mv "$SOPS_FILE.new" "$SOPS_FILE"

echo "✓ Llave '$NAME' creada ($(json '",".join(d["capabilities"])' <<< "$key")) y guardada cifrada en $SOPS_FILE"
