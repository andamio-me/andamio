# Convenciones de los stacks

Todo servicio del homelab cumple estas reglas. Plantilla: `stacks/_template/compose.yaml`.

| Regla | Cómo | Por qué |
|---|---|---|
| Imagen con versión fija | `image: postgres:18.6-alpine`, nunca `:latest` | Reproducible; actualizar es una decisión |
| Sin puertos publicados | Sin `ports:`. Solo Traefik publica 80/443 | Docker se salta UFW |
| Excepción local | `127.0.0.1:PUERTO:PUERTO` | Acceso por túnel SSH, nunca expuesto |
| Redes explícitas | `proxy`, `data`, `monitoring` (externas) | Nunca la red `bridge` por defecto |
| Límites obligatorios | `mem_limit`, `memswap_limit` = `mem_limit`, `cpus`, `pids_limit` | Un contenedor no tumba el servidor; sin swap por contenedor |
| Reinicio | `restart: unless-stopped` | Vuelve solo tras reinicios del host |
| Healthcheck | Siempre que la imagen lo permita | Docker y el monitoreo saben si está sano |
| Sin privilegios | `security_opt: no-new-privileges:true`; usuario no root si la imagen lo soporta | Contener un posible escape |
| Datos | Volumen con nombre | Gestionado por Docker; backups en Fase 5 |
| Configuración | Bind mount de solo lectura (`:ro`) desde el repo | Versionada en git |
| Secretos | `.env` junto al compose, `chmod 600`, fuera de git | Nunca en la imagen ni en el repo |
| Nombres | `container_name` = nombre del servicio | Fácil de encontrar en logs y métricas |

Las redes se crean una sola vez con `scripts/create-networks.sh`.
