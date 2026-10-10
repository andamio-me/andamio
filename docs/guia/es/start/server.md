---
title: Tu servidor
description: andamio servidor endurece tu VPS y levanta la plataforma.
---

```bash
andamio servidor
```

Se puede repetir cuantas veces quieras: retoma donde quedó, y también sirve para volver a
aplicar todo después de un cambio.

## Antes: dos comprobaciones en tu proveedor

1. **Su firewall.** Azure, AWS, Oracle y Google Cloud (y algunos Hetzner o DigitalOcean)
   filtran el tráfico antes de que llegue a tu VPS. Abre la entrada **TCP** de tu puerto SSH,
   `80` y `443`, y **UDP** `51820`. Deja el `22` abierto hasta que termine `andamio
   servidor`: si no, al mover SSH a tu puerto quedas fuera.
2. **La huella del servidor.** `andamio servidor` te la muestra antes de la primera
   conexión. Compruébala desde *dentro* del servidor por un camino que no sea la red: la
   consola web de tu VPS, *Ejecutar comando* en Azure o *Session Manager* en AWS:

   ```bash
   ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   ```

   Tiene que coincidir. Si no coincide, no sigas: alguien puede estar en el medio.

## Qué hace, paso a paso

1. **Entra al servidor** con lo que te dio tu proveedor: contraseña de root o la llave
   `.pem`. Te pregunta cuál es tu proveedor para usar su usuario inicial.
2. **Instala tu llave SSH** y verifica la huella.
3. **Crea tu usuario** de operación y te pide una contraseña de sudo nueva (dos veces).
4. **Lo endurece:** SSH solo con llave y en tu puerto, root sin acceso, firewall UFW,
   parches de seguridad automáticos y fuera los servicios que no se usan.
5. **Instala Docker** (logs rotados; el socket solo a través de un proxy de solo lectura).
6. **Arma la VPN WireGuard** y genera la configuración de tu primer dispositivo.
7. **Prepara la llave** con la que el servidor baja tu copia de andamio (solo lectura,
   solo ese repo).
8. **Levanta la plataforma:** Traefik con HTTPS, PostgreSQL, Redis y el monitoreo.

Al terminar, cierra el `22` en el firewall de tu proveedor.

## La VPN

Tu primer dispositivo queda en `~/andamio-vpn/mi-pc.conf`. Impórtalo en la app de
WireGuard; para el celular, muéstralo como QR:

```bash
qrencode -t ansiutf8 < ~/andamio-vpn/mi-pc.conf
```

Las apps privadas (las que creas sin `--public`) y las herramientas de administración
responden **solo** con la VPN conectada.

## Comprueba que quedó bien

```bash
andamio estado
```

Revisa la seguridad y la salud del servidor desde adentro y desde internet, y te dice cómo
arreglar cada problema. Ver [Seguridad](/es/docs/server/security/).

## Tu contraseña de sudo

Los comandos que cambian el servidor te la piden **una vez** y la recuerdan 15 minutos sin
uso, solo en memoria (nunca en disco). `andamio olvidar` la borra en el momento;
`ANDAMIO_SUDO_MINUTES=0` desactiva el recuerdo.
