# 0029. Seguridad desde el primer minuto y `andamio seguridad`

- **Estado:** Aceptada (probada en dos VMs nuevas de Azure y en el servidor principal)
- **Fecha:** 2026-10-15

## Contexto
La idea de andamio es que un VPS recién comprado no quede expuesto ni un rato. Una revisión
del endurecimiento encontró huecos:

- `bootstrap.yml` movía SSH a tu puerto, pero las contraseñas (también la de root) y el
  firewall seguían como venían hasta `site.yml`. Si `site.yml` fallaba o se corría tarde, los
  bots tenían SSH con contraseña y sin firewall.
- fail2ban estaba en el servidor principal, pero puesto a mano: ningún rol lo instalaba.
- sshd no limitaba intentos ni conexiones a medio abrir; Docker publicaba en todas las
  interfaces si un compose lo pedía (y Docker se salta UFW); Traefik no tenía límite de
  peticiones; la contraseña de root del proveedor seguía sirviendo en su consola web.
- Para blindar había que pasar por todo: cuenta de GitHub, repo privado, sops, age, dominio.
  Mucho para quien solo quiere su VPS a salvo.

## Decisión
- **bootstrap.yml** comprueba primero que tu usuario nuevo entra con su llave y, apenas pasa,
  apaga contraseñas y root, bloquea la contraseña de root y activa UFW, **antes** de mover
  SSH. El 22 queda abierto solo hasta que el rol firewall lo cierra.
- **Rol `fail2ban`** (también en `andamio servidor`): 3 intentos en 10 min, 1 h de bloqueo que
  crece si reincide (hasta 1 semana), modo agresivo, nunca la VPN.
- **sshd:** `MaxAuthTries 4` (no 3: un agente con varias llaves gasta uno por llave),
  `LoginGraceTime 20`, `MaxStartups 10:30:60`, sin X11, sin reenviar el agente, solo túneles
  hacia el servidor (`AllowTcpForwarding local`: el panel los usa).
- **Docker** seguro por defecto: `"ip": "127.0.0.1"` (un puerto publicado sin IP queda local;
  Traefik declara 80/443 en `0.0.0.0` y `[::]`) y `"no-new-privileges": true` para todos.
- **Traefik:** `rate-limit` por IP en todas las apps públicas (`andamio_rate_average` 100/s,
  `andamio_rate_burst` 300). Antes que las cabeceras: lo que se pasa no llega a la app.
- **sysctl** de red y kernel explícitos (no depender de la imagen del proveedor).
- **`andamio seguridad`:** solo el blindaje, sin plataforma ni cuentas. Pregunta la IP, el
  proveedor y su usuario, y tu usuario (distinto, validado al instante) y el puerto. Además de
  lo de arriba:
  - antes de mover SSH, **prueba que el puerto nuevo llega** (rechazo = llega; sin respuesta =
    lo bloquea el firewall del proveedor, y se detiene diciendo dónde abrirlo);
  - **verifica desde afuera** que root y los demás usuarios con contraseña reciben un rechazo
    y que el 22 ya no responde (antes de instalar fail2ban, que bloquearía tu IP por esto);
  - aplica los **parches pendientes** de la imagen y, si piden reinicio, ofrece reiniciar ya
    (un VPS recién blindado no tiene nada corriendo);
  - el **alias SSH** se elige (sugiere uno que diga cuál servidor es) y nunca reusa el de otro
    servidor de `~/.ssh/config`.
- **`andamio setup`** pregunta primero "solo blindar" o "completo". Solo blindar instala lo
  justo (git, ssh, Ansible), crea la copia **solo local** (sin origin) y sigue con
  `andamio seguridad`. Para la plataforma después, `andamio setup` desde esa copia crea un
  repo privado vacío y la sube tal cual; `andamio init` completa la configuración sin volver
  a preguntar IP, usuario ni puerto.

## Consecuencias
- Un VPS nuevo nunca tiene SSH con contraseña ni el firewall apagado, ni si algo falla a mitad.
- La llave SSH pasa a ser la única entrada: andamio lo avisa al crearla y dice cómo
  respaldarla (gestor de contraseñas, segunda llave) y cómo recuperar el acceso (consola del
  proveedor + tu usuario con sudo).
- Un contenedor que de verdad necesite escalar privilegios tiene que pedirlo
  (`security_opt: [no-new-privileges:false]`); en el servidor principal ninguno lo necesitó.
- fail2ban no se prueba desde tu PC (bloquearía tu IP): desde otra red, como Azure Cloud Shell.
