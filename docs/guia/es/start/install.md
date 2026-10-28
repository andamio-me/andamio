---
title: Instalar
description: Deja tu máquina lista y crea tu copia privada de andamio.
---

## 1. El instalador

En tu máquina (Linux, macOS o la terminal de Ubuntu en WSL):

```bash
curl -fsSL https://raw.githubusercontent.com/andamio-me/andamio/main/install.sh | sh
```

Es corto: léelo antes si prefieres. Hace lo mismo que esto, a mano:

```bash
git clone https://github.com/andamio-me/andamio.git ~/andamio
~/andamio/bin/andamio setup
```

## 2. `andamio setup`

Lo primero que pregunta es qué quieres hacer:

- **Solo blindar mi VPS.** Instala lo justo (git, ssh y Ansible), crea tu copia de andamio
  **solo en tu máquina** (por ejemplo `~/mi-andamio`) y sigue directo con
  [`andamio seguridad`](/es/docs/start/server/#solo-blindar-el-vps-andamio-seguridad). Sin
  cuenta de GitHub ni repos. Si un día quieres la plataforma, corre `andamio setup` dentro
  de tu copia: la conecta con GitHub (un repo privado nuevo, con lo que ya hiciste) y sigues
  con `andamio init`.
- **andamio completo.** Lo de abajo.

Corre una vez y pregunta antes de instalar cada cosa:

1. Instala **git, gh, sops, age y Ansible** con sus colecciones. sops se verifica contra su
   checksum.
2. Configura tu identidad de git.
3. Inicia sesión en GitHub (`gh auth login`) con una llave SSH, y fija las llaves oficiales
   de GitHub para que nadie pueda hacerse pasar por él.
4. Crea **tu copia privada de andamio** desde la plantilla, en tu cuenta, y la clona
   (por ejemplo en `~/mi-andamio`).
5. Instala el comando `andamio` en `~/.local/bin`, para usarlo desde cualquier carpeta.

:::note
Tu copia es **privada** y es tuya: ahí va a vivir la configuración de tu servidor, sus
secretos cifrados y tus apps. El repo público de andamio es solo la plantilla.
:::

## 3. `andamio init`

Dentro de tu copia:

```bash
cd ~/mi-andamio
andamio init
```

Preguntas guiadas, una por una, validadas al instante:

- el dominio de tu servidor y tu correo (para los avisos de Let's Encrypt);
- la IP del VPS y el puerto SSH que vas a usar (no el 22);
- el nombre del usuario de Linux que andamio crea para ti en el servidor;
- el modo de HTTPS: `http` (Let's Encrypt, por defecto), `cloudflare` (comodín por DNS) o
  `custom` (tu propio certificado);
- el nivel de monitoreo: `auto`, `minimo` o `completo`.

Crea tu configuración en `ansible/group_vars/all.yml`, una llave de cifrado (age) que vive
**solo en tu máquina** y los secretos de la plataforma, cifrados. No toca ningún servidor.

Al final te muestra los puertos que tienes que abrir en el firewall de tu proveedor.
Súbelo:

```bash
git add -A && git commit -m "andamio: mi servidor" && git push
```

:::caution[Tu llave age]
`~/.config/sops/age/keys.txt` es la única llave que descifra tus secretos. Guárdala en un
gestor de contraseñas: sin ella no puedes reconstruir tu servidor.
:::

Sigue con [Tu servidor](/es/docs/start/server/).
