# 0015. Mini-PaaS: apps declarativas con un comando

- **Estado:** Aceptada
- **Fecha:** 2026-10-07

## Decisión
- **Cada app es un `apps/<app>/app.yml`** (host, puerto, acceso, redes, db, redis,
  recursos). El repo dice qué apps existen; Ansible hace que el servidor coincida.
- **En el WSL** (`ansible/apps.yml`): completa secretos que falten (nunca cambia uno
  existente), crea la llave de deploy (privada solo en GitHub) y genera `compose.yaml`
  desde una plantilla.
- **En el servidor** (rol `homelab`): `.env` desde sops, usuario y base de PostgreSQL,
  usuario de Redis por ACL, llaves de deploy en `/etc/ssh/deploy_keys/<usuario>`
  (archivo de root, reescrito completo) y el registro `homelab_app_info` para Prometheus.
- **`bin/homelab`** une todo: `app create | list | logs | rollback`.
- **Repo plantilla** `homelab-app-template` (Next.js + Prisma, health, Dockerfile, CI
  sobre `app-build-v2`, tabla `deployments`).
- Sin interfaz web ni detección de lenguaje (Dockerfile siempre) ni varios servidores.

- **Workers** (2026-10-07): `worker:` en app.yml genera un servicio con la misma
  imagen, sin Traefik, salud por latido (`/tmp/heartbeat`), reemplazado por el
  deploy junto con la web. Primer uso: cola de clics de `shortener` (BullMQ).

## Consecuencias
- Agregar una app: un comando y un `git push` (antes, ~10 pasos manuales).
- El dashboard deriva la lista de apps del registro: una app que no corre aparece caída.
- Primera app real: `shortener` (2026-10-07).
- Pendientes: `homelab app destroy`, probar `rollback` y la recarga en caliente de
  usuarios de Redis (`ACL LOAD`) con una segunda app.
