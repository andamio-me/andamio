# 0016. Dominio propio: ejemplo.com con DNS en Cloudflare

- **Estado:** Aceptada (reemplaza el dominio DuckDNS de la ADR 0006)
- **Fecha:** 2026-10-07

## Decisión
- **Dominio `ejemplo.com`**, registrado en Namecheap (GitHub Student Pack: gratis hasta
  2027-10-07; renovación automática apagada a propósito, se decide entonces).
- **DNS en Cloudflare (plan Free)**, nameservers `thea`/`tim.ns.cloudflare.com`.
  Registros: `A @` y `A *` → 203.0.113.10 en **DNS only** (sin proxy: el allowlist
  `vpn-only` y la ruta de WireGuard dependen de la IP real del VPS). **Sin AAAA**: la
  VPN enruta solo la IPv4 del VPS. SPF `-all` y DMARC `reject`: el dominio no envía
  correo y nadie puede suplantarlo.
- **Certificado comodín `*.ejemplo.com`** por DNS-01 (resolver `cf` de Traefik), con un
  token de Cloudflare `Zone:DNS:Edit` + `Zone:Zone:Read`, solo para `ejemplo.com` y solo
  desde la IP del VPS. Cifrado en `stacks/proxy/secrets.sops.env`. El comodín es el
  certificado por defecto: las apps nuevas tienen HTTPS sin pedir uno propio.
- **El dominio anterior redirige**: todo `*.midominio.duckdns.org` responde 302 al mismo
  subdominio de `ejemplo.com` con la misma ruta (`stacks/proxy/dynamic/dominio-anterior.yml`,
  certificados HTTP-01 del resolver `le`).

## Consecuencias
- `DOMAIN=ejemplo.com` en todos los stacks y apps (secretos sops), en `bin/andamio-app` y
  en `ansible/apps.yml`. El aviso de backups (KUMA_PUSH_URL) apunta a `status.ejemplo.com`.
- Pendiente: pasar la redirección a 301 cuando todo esté probado, actualizar los
  monitores de Uptime Kuma y activar DNSSEC en Cloudflare.
