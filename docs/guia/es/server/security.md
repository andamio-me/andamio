---
title: Seguridad
description: Lo que andamio deja hecho en tu servidor, cómo revisarlo y sus límites.
---

## Lo que queda hecho

Sin que lo pidas, `andamio servidor` deja:

- **Tu propio usuario**, con sudo y contraseña. Root no puede entrar, y su contraseña (la que
  manda el proveedor) queda bloqueada, también para la consola web.
- **SSH solo con llave**, en un puerto distinto del 22, con pocos intentos por conexión y
  sin reenvíos que un servidor no usa.
- **Firewall UFW:** entra solo tu puerto SSH, HTTP/HTTPS y la VPN.
- **Protegido desde el primer minuto:** las contraseñas de SSH y el firewall se apagan y se
  encienden apenas se crea tu usuario, no al final; el VPS no queda expuesto ni si algo
  falla a mitad de camino.
- **fail2ban:** la IP que insiste contra SSH queda bloqueada (1 hora, y más si reincide).
- **Parches de seguridad automáticos**, el kernel con parámetros de red endurecidos, y fuera
  snapd y los servicios que no se usan.
- **Docker** con logs rotados; el socket solo a través de un proxy de solo lectura. Un
  puerto publicado queda en `127.0.0.1` salvo que digas otra cosa, y ningún contenedor puede
  ganar privilegios con `sudo` o `su`.
- **Traefik** con HTTPS automático, cabeceras de seguridad y un límite de peticiones por IP
  (100 por segundo, 300 de golpe: `andamio_rate_average` y `andamio_rate_burst`).
- **VPN WireGuard:** lo privado responde solo a través de ella.

Y cada app nueva:

- su propio usuario y base en PostgreSQL, y su usuario de Redis limitado a sus claves: una
  app no puede leer las tablas ni las claves de otra;
- una llave de deploy que solo puede ejecutar el deploy de esa app (no abre una terminal);
- secretos cifrados con sops y age, con la llave **solo en tu máquina**;
- imágenes revisadas (secretos filtrados, tests, vulnerabilidades) antes de llegar a tu
  servidor.

## `andamio estado`

```bash
andamio estado
```

Un chequeo de seguridad y salud. **No cambia nada.**

- **Desde el servidor:** SSH (solo llave, sin root, tu puerto, fail2ban), firewall, parches
  automáticos y pendientes, disco, reloj, último backup, certificados, contenedores con
  problemas, aislamiento (contenedores privilegiados, el socket de Docker, puertos
  publicados que se saltan el firewall) y la VPN.
- **Desde internet**, desde tu máquina: si responde algún puerto que no debería (Docker
  puede saltarse UFW: solo una prueba desde afuera dice la verdad), que el `22` esté
  cerrado, y el certificado y la redirección HTTP → HTTPS como los ve un visitante.

```
  ✓ SSH           Solo llaves (sin contraseñas)
  ✓ Firewall      UFW activo, entrada denegada por defecto
  ! Parches       12 actualizaciones de seguridad pendientes
    → llegan cada noche; para aplicarlas ya: sudo apt upgrade en el servidor
  ✓ Internet      El puerto 22 está cerrado (SSH solo en el tuyo)

14 bien · 1 aviso · 0 problemas
```

Cada problema trae su arreglo. Sale con código 1 si hay problemas, así que sirve en scripts.

## Lo que no protege

- **Un solo servidor.** Sin alta disponibilidad: si el VPS desaparece, se reconstruye desde
  tu repo y tus [backups](/es/docs/server/backups/).
- **Los nombres de tus apps.** En el modo HTTPS `http`, cada nombre (también los privados)
  aparece en los registros públicos de certificados. Usa el modo `cloudflare` si te importa.
- **Tu cuenta de GitHub.** Quien la controle puede subir código que se despliega. Protégela
  con 2FA.
- **Puertos que publiques tú.** Un `-p 0.0.0.0:...` de Docker se salta el firewall (sin la
  IP queda local). `andamio estado` lo detecta.
- **La red entre apps.** Las apps comparten la red del proxy; lo que las aísla son los
  usuarios de base y de Redis.
