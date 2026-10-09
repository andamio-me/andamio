# 0006. Traefik como reverse proxy, DuckDNS y HTTP-01

- **Estado:** Aceptada
- **Fecha:** 2026-10-06

## Contexto
La plataforma necesita un único punto de entrada con TLS automático, y a futuro
un mini-PaaS que publique apps sin editar archivos de configuración.

## Decisión
- Traefik v3 en Docker, único servicio con puertos publicados (80, 443).
- Descubrimiento por labels (`traefik.enable=true`, `exposedByDefault: false`).
- Acceso al socket de Docker solo a través de `docker-socket-proxy`
  (solo lectura de contenedores), en una red interna exclusiva.
- Dashboard en `127.0.0.1:8080`, accesible solo por túnel SSH.
- Dominio DuckDNS (`midominio.duckdns.org`, todos sus subdominios resuelven al VPS).
- Certificados por subdominio con Let's Encrypt, desafío HTTP-01.
- El dominio base va en la variable `DOMAIN` del `.env` de cada stack.

## Alternativas
- Nginx en el host: ya conocido, pero cada app requiere editar archivos y recargar.
- Caddy: simple, pero el descubrimiento por labels no es nativo.
- Dominio propio + Cloudflare: necesario para wildcard (DNS-01). Se migrará después.

## Consecuencias
- Publicar una app = 4 labels. Certificados automáticos.
- Migrar de dominio = cambiar `DOMAIN` en cada stack y, para wildcard, agregar
  un resolver DNS-01 con Cloudflare en `traefik.yml`.
- `traefik.yml` es configuración estática: los cambios requieren reiniciar Traefik.
- Hosts desconocidos (acceso por IP) reciben 404.
