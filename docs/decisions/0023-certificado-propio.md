# 0023. Certificado propio (andamio_tls: custom)

- **Estado:** Aceptada
- **Fecha:** 2026-10-09

## Contexto
andamio solo emitía certificados con Let's Encrypt (`http` por HTTP-01, `cloudflare` por
DNS-01). Hay quien ya tiene uno: de una CA comercial (exigencia de una empresa, validación
OV/EV) o un Origin Certificate de Cloudflare (15 años, gratis, muy común en VPS detrás del
proxy de Cloudflare).

## Decisión
**Un solo mecanismo para ambos: un archivo.**
- `bin/andamio certificado <cert> <llave>` (o `custom` en `init`) valida con openssl antes de
  guardar: que la llave corresponda, que no haya vencido, que cubra `dominio` y `*.dominio`,
  que traiga la cadena de intermedios. Lo que no impide usarlo se avisa y se confirma.
- El certificado va en claro en `host/tls/cert.pem` (es público). La llave, cifrada con sops
  en `host/sops/tls-key.sops`, como los demás secretos del host; andamio no hace copias en
  claro y pide borrar la original.
- Ansible los copia a `/etc/andamio/tls` (0700, del usuario de Traefik), montado en Traefik
  como `/certs`. `dynamic/tls.yml` lo declara y lo hace el certificado por defecto. El
  entrypoint `websecure` queda con `tls: {}` y sin resolvers de ACME.
- Traefik no vigila los archivos del certificado: si cambian, Ansible lo reinicia.
- Vencimiento: una alerta de Grafana para **todos** los certificados que sirve Traefik
  (`traefik_tls_certs_not_after` < 20 días). También detecta una renovación de Let's Encrypt
  que lleva 10 días fallando.

## Alternativas descartadas
- **Mezclar por app** (certificado propio para lo público, Let's Encrypt para lo privado):
  resolvería el caso Origin + paneles por VPN, pero exige etiquetas por router en cada stack
  y la elección de certificado de Traefik entre exacto y comodín es sutil. Para quien tiene
  el dominio en Cloudflare, el modo `cloudflare` ya cubre ambos; se documenta.
- **Pegar el certificado en la terminal:** la llave quedaría en el historial o en la
  pantalla. Se pide la ruta del archivo (también rutas de Windows desde WSL).

## Consecuencias
- Origin Certificate: los paneles privados muestran error de certificado (no pasan por el
  proxy). `andamio` lo advierte y recomienda `cloudflare`.
- La renovación es manual: mismo comando, commit y `hl aplicar andamio`.
