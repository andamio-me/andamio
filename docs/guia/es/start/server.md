---
title: Tu servidor
description: andamio servidor endurece tu VPS y levanta la plataforma.
---

```bash
andamio servidor
```

Se puede repetir cuantas veces quieras: retoma donde quedó, y también sirve para volver a
aplicar todo después de un cambio.

## Solo blindar el VPS: `andamio seguridad`

Si por ahora solo quieres el VPS a salvo (o vas a montar la plataforma más tarde):

```bash
andamio seguridad
```

Pregunta tres cosas (la IP, tu usuario y el puerto SSH nuevo) y deja hecho lo mismo que el
blindaje de `andamio servidor`, sin instalar nada más:

1. Crea tu llave SSH si no tienes, y te avisa que va a ser tu única entrada (guárdala).
2. Comprueba la huella del servidor e instala tu llave con la contraseña o el `.pem` que te
   dio el proveedor (una sola vez).
3. **Antes de mover SSH, prueba que el puerto nuevo llega al servidor.** Si el firewall de
   tu proveedor lo bloquea, se detiene y te dice dónde abrirlo: no te quedas afuera.
4. Crea tu usuario y, en el mismo paso, apaga las contraseñas y root y enciende el firewall.
5. Lo comprueba desde afuera: root y los demás usuarios con contraseña reciben un rechazo, y
   el `22` ya no responde.
6. Parches automáticos, sshd estricto, fail2ban, y el chequeo de seguridad del servidor.

Cuando quieras la plataforma: `andamio init` completa lo que falta (dominio, repo, HTTPS) sin
volver a preguntar lo anterior, y después `andamio servidor`.

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
4. **Lo endurece:** SSH solo con llave y en tu puerto, root sin acceso y su contraseña
   bloqueada, firewall UFW (las tres cosas apenas existe tu usuario, antes de seguir),
   fail2ban, parches de seguridad automáticos y fuera los servicios que no se usan.
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
uso, solo en memoria (nunca en disco). En el panel, **Ajustes → Contraseña de sudo** elige
cuánto: 15 min, 1 h, 4 h u 8 h (es una preferencia de tu máquina, en `~/.config/andamio`), y
**Olvidar ahora** la borra. En la terminal, `andamio olvidar` hace lo mismo;
`ANDAMIO_SUDO_MINUTES` manda sobre el ajuste (`0` desactiva el recuerdo).
