# andamio

**Un PaaS seguro por defecto para un solo VPS.** Toma el servidor que acabas de comprar,
lo endurece y despliega tus apps en él, cada una aislada, con cada cambio pasando por git.

[English](README.md)

> **Estado: alpha.** andamio mueve un servidor real en producción (apps, sincronización de
> archivos, monitoreo, backups). La instalación guiada desde un VPS nuevo
> (`andamio servidor`) está escrita pero **todavía no se probó de punta a punta en una
> máquina limpia**. Espera asperezas.

---

## Por qué andamio

Tener tu propio servidor tiene dos etapas, y la mayoría de las herramientas solo cubre la
segunda:

1. **"Compré un VPS, ¿y ahora?"** Suele venir con root, una contraseña y todos los puertos
   abiertos. andamio lo endurece: un usuario propio, SSH solo con llave y en otro puerto,
   root sin acceso, firewall, parches de seguridad automáticos, una VPN para lo privado y
   HTTPS.
2. **"Quiero publicar mis apps."** En ese servidor ya seguro, cada app tiene sus propios
   usuarios de base de datos y de Redis; una llave de deploy que puede desplegar *esa app
   y nada más*; y un pipeline que corre tus tests y busca vulnerabilidades y secretos
   filtrados **antes** de que algo llegue al servidor.

| | andamio | Coolify / Dokploy | Dokku | Kamal |
|---|---|---|---|---|
| Endurece el servidor (SSH, firewall, parches, VPN) | ✅ | lo haces tú | lo haces tú | lo haces tú |
| Panel web | no (git + CLI) | sí | no | no |
| Dónde se construyen las imágenes | GitHub Actions | en tu VPS | en tu VPS | tu máquina o CI |

Lo que andamio suma, incluido de serie: tests, escaneo de secretos y de vulnerabilidades
antes de publicar cualquier imagen; mínimo privilegio por app; y backups que se pueden
volver imborrables desde el servidor, con un simulacro de restauración.

andamio no intenta ser el panel más fácil. Es el PaaS que puedes **entender completo**: sin
estado escondido, el servidor entero se reconstruye desde tu repo y cada decisión de diseño
está escrita.

## Qué obtienes

**Etapa 1: un servidor endurecido** (sin cuentas en otros servicios)
- Usuario de operación propio; SSH solo con llave, en el puerto que elijas; root sin acceso.
- Firewall UFW: solo SSH, HTTP/HTTPS y el puerto de la VPN.
- Parches de seguridad automáticos; sin snapd ni servicios innecesarios.
- Docker con logs rotados; el socket de Docker solo es accesible a través de un proxy de
  solo lectura.
- Traefik con HTTPS automático (Let's Encrypt) y cabeceras de seguridad.
- VPN WireGuard, generada para ti, con la configuración de tu primer cliente lista para
  importar. Las herramientas de administración (Grafana, la página de estado, tus apps
  privadas) responden **solo** a través de ella.
- Monitoreo según tu RAM: métricas siempre; logs, paneles, alertas y monitor de
  disponibilidad si el servidor tiene 3 GB o más.

**Etapa 2: deploys aislados y verificados**
- Cualquier lenguaje. Tu app necesita un `Dockerfile`: ese es el contrato.
- Se construye en GitHub Actions, nunca en tu VPS (por eso alcanza un servidor de 1-2 GB).
- Antes de publicar una imagen: escaneo de secretos (gitleaks), tus tests (una etapa
  `test` en tu Dockerfile) y escaneo de vulnerabilidades (Trivy). Una imagen vulnerable
  nunca llega al registro.
- Deploys sin caída: la versión nueva arranca junto a la anterior y tiene que pasar su
  chequeo de salud antes de apagar la vieja. Volver atrás es un comando.
- Por app: su propio usuario y base de PostgreSQL, su propio usuario de Redis (ACL,
  limitado a sus claves) y una llave de deploy que solo puede desplegar esa app.

**Opcional y guiado** (necesitan una cuenta en algún servicio)
- Backups cifrados y deduplicados con restic a cualquier destino (S3, B2, SFTP, ...). Con
  Backblaze B2 se pueden volver **imborrables desde el servidor**, y un simulacro verifica
  que de verdad se restauran.
- Alertas por Telegram, un resumen diario y un pequeño bot de operación.
- Un certificado comodín vía DNS de Cloudflare (evita que los nombres de tus apps
  privadas aparezcan en los registros públicos de certificados).

## Requisitos

- Un VPS con **Ubuntu 24.04**, 1 GB de RAM como mínimo (2 GB o más es cómodo) y su IP pública.
- Un **dominio** con dos registros DNS `A` apuntando a esa IP: `ejemplo.com` y `*.ejemplo.com`.
- Una cuenta de **GitHub** (ahí viven tus apps, y sus imágenes en GHCR).
- En tu máquina (Linux, macOS o WSL): `git`, `gh` (con sesión iniciada), `ssh`, `sops`,
  `age`, `ansible` y `python3-yaml`. `andamio init` los revisa y te dice cómo instalar lo
  que falte.

## Inicio rápido

```bash
# 1. Crea tu copia (privada) de este repo: "Use this template" en GitHub, y luego
git clone git@github.com:<tú>/<tu-andamio>.git && cd <tu-andamio>

# 2. Responde unas preguntas. Crea tu configuración, una llave de cifrado (age) y los
#    secretos de la plataforma, todo cifrado. No toca ningún servidor.
bin/andamio init

# 3. Sube tu configuración cifrada
git add -A && git commit -m "andamio: mi servidor" && git push

# 4. Prepara el servidor: verifica su huella SSH, instala tu llave (sirve tanto si tu
#    proveedor te dio una llave como una contraseña de root), crea tu usuario, lo
#    endurece, arma la VPN y levanta la plataforma. Se puede repetir: retoma donde quedó.
bin/andamio servidor
```

### Antes de `andamio servidor`: dos comprobaciones en tu proveedor

1. **Su firewall.** Azure, AWS, Oracle y Google Cloud (y algunos Hetzner o DigitalOcean)
   filtran el tráfico antes de que llegue a tu VPS. Abre la entrada **TCP**
   `<tu puerto SSH>`, `80` y `443`, y **UDP** `51820`, y deja el `22` abierto hasta que
   termine `andamio servidor`. Si no, al mover SSH a tu puerto quedas fuera.
   `andamio init` te muestra los puertos exactos al final.
2. **La huella del servidor.** `andamio servidor` te la muestra antes de la primera
   conexión. Compruébala desde *dentro* del servidor por un camino que no sea la red: la
   consola web de tu VPS (Hetzner, DigitalOcean, Vultr, Linode, Contabo), *Ejecutar
   comando* en Azure o *Session Manager* en AWS. Corre ahí
   `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`: tiene que coincidir.

Después importa `~/andamio-vpn/mi-pc.conf` en la app de WireGuard (o muéstralo como QR
para el celular con `qrencode -t ansiutf8 < ~/andamio-vpn/mi-pc.conf`).

## Despliega tu primera app

Tu app, en cualquier lenguaje, necesita un `Dockerfile`. Opcionalmente:

- una etapa llamada **`test`**: el CI la construye antes de desplegar; si falla, no se
  despliega nada;
- una **ruta de salud** HTTP (p. ej. `/healthz`) que responda 200 cuando la app está lista.

```bash
# Registra un repo existente: crea su llave de deploy, las variables del CI, un usuario de
# base y de Redis si los pides, e imprime el workflow de CI que agregas a tu repo.
bin/homelab app create miapp --repo <tú>/miapp --port 8000 --health /healthz

# Agrega a tu app el .github/workflows/ci.yml que imprimió, y luego
git push   # tests, escaneos, build y deploy
```

Tu app queda en `https://miapp.ejemplo.com` (por la VPN, salvo que uses `--public`).

Opciones útiles: `--public` (accesible desde internet), `--db` (PostgreSQL), `--redis`,
`--host <sub>` o `--host @` (dominio raíz), `--mem 512m`.

### `apps/<app>/app.yml`

| Clave | Significado |
|---|---|
| `port` | Puerto en el que escucha tu app dentro del contenedor |
| `health` | Ruta HTTP que se consulta desde el host antes de que una versión nueva reciba tráfico. Sin ella, se usa el `HEALTHCHECK` de la imagen; sin ninguno, "sana" = 10 s corriendo sin reiniciarse |
| `access` | `vpn` (por defecto) o `public` |
| `db`, `redis` | Tu propia base y usuario de PostgreSQL, y tu usuario de Redis |
| `migrate` | `{ command: "python manage.py migrate" }` corre con la imagen de tu app antes de cada deploy |
| `worker` | `{ command: "...", heartbeat: false }`: un segundo proceso con la misma imagen |
| `resources` | Límites de `mem`, `cpus` y `pids` |

### Si Trivy frena tu imagen

Las imágenes base oficiales suelen traer su gestor de paquetes (`npm`, `pip`,
`setuptools`), que trae sus propias vulnerabilidades y no se usa en producción. Quítalo de
la etapa final, por ejemplo `RUN pip uninstall -y pip setuptools` o
`RUN rm -rf /usr/local/lib/node_modules/npm`. Si los hallazgos están en tus dependencias,
actualízalas.

## Módulos opcionales

Todo en `ansible/group_vars/all.yml`:

| Opción | Valores |
|---|---|
| `homelab_tls` | `http` (por defecto: un certificado de Let's Encrypt por app, con cualquier DNS), `cloudflare` (un certificado comodín; necesita la zona en Cloudflare y un token de API) o `custom` (tu propio certificado, ver abajo) |
| `homelab_forge` | `github` (por defecto). Todo lo que andamio necesita de ella pasa por `bin/forge`; agregar GitLab es implementar ese archivo y su pipeline |
| `homelab_monitoring` | `auto` (por defecto), `minimo` (~115 MiB: métricas) o `completo` (~670 MiB: + logs, Grafana con alertas, Uptime Kuma) |
| `homelab_backups` | `false` (por defecto). Lo activa `bin/andamio backups`: ver abajo |
| `homelab_telegram` | `false` (por defecto) o `true`, con el token del bot y el chat en `host/sops/telegram-env.sops` |

### Chequeo de seguridad

```bash
bin/andamio estado
```

No cambia nada. En el servidor: SSH (solo llave, sin root, tu puerto), firewall, parches de
seguridad automáticos y reinicios pendientes, disco, reloj, último backup, certificados,
contenedores con problemas, aislamiento (contenedores privilegiados, el socket de Docker,
puertos publicados saltándose el firewall) y la VPN. **Desde Internet**, desde tu máquina:
si responde algún puerto que no debería (Docker puede saltarse UFW: solo una prueba desde
afuera dice la verdad), que el 22 esté cerrado, y el certificado y la redirección
HTTP→HTTPS como los ve un visitante. Cada problema trae su arreglo; código de salida 1 si
hay problemas.

### Backups

```bash
bin/andamio backups
```

Pregunta dónde guardarlos (Backblaze B2 o cualquier almacenamiento compatible con S3:
AWS, Cloudflare R2, Wasabi, MinIO), prueba el destino desde tu servidor, hace el primer
backup en el momento y después una prueba de restauración: carga el dump en un PostgreSQL
temporal y lo compara con producción, sin tocarla. Desde ahí, cada noche a las 03:30 UTC.

- restic cifra todo en el servidor antes de subirlo: el proveedor nunca ve tus datos. La
  contraseña del repositorio es aleatoria y vive cifrada en tu repo (sops).
- Con B2, andamio puede crear la llave del servidor **sin permiso de borrar**, limitada a
  un bucket (necesita tu master key una vez y no la guarda). Quien tome el servidor no
  puede borrar tus backups.
- Se guardan 7 diarios, 4 semanales y 6 mensuales.

### Tu propio certificado

Con un certificado de una CA comercial, o un Origin Certificate de Cloudflare, elige
`custom` en `andamio init`, o cámbialo después:

```bash
bin/andamio certificado fullchain.pem privada.key   # lo valida y lo guarda (la llave, cifrada con sops)
bin/andamio certificado                             # muestra el actual y cuándo vence
```

Revisa que la llave corresponda, que cubra `tudominio` y `*.tudominio`, que traiga la
cadena de intermedios y cuánto le queda. Nadie lo renueva por ti: Grafana avisa 20 días
antes de que venza cualquier certificado (también los de Let's Encrypt, por si la
renovación falla). Renovar es el mismo comando con los archivos nuevos.

Un Origin Certificate de Cloudflare solo es válido a través del proxy de Cloudflare. Tus
paneles privados (por la VPN) no pasan por ahí, así que los navegadores lo rechazarán en
ellos. Si tu dominio ya está en Cloudflare, el modo `cloudflare` es gratis, se renueva solo
y sirve para ambos.

## El modelo de seguridad, con honestidad

Lo que protege:
- **La superficie del servidor:** solo están abiertos SSH (llave, puerto propio),
  HTTP/HTTPS y la VPN. andamio solo publica el 80/443 (Traefik); lo interno escucha en
  localhost o en redes internas de Docker. (Ojo: un puerto que publiques tú con `-p` se
  salta UFW.)
- **Los datos de cada app frente a las demás:** usuarios de base y de Redis separados; una
  app no puede leer las tablas ni las claves de otra. Las apps sí comparten la red del proxy.
- **El camino del deploy:** el CI solo puede pedirle al servidor que despliegue una app
  (un comando forzado por llave), y solo imágenes que pasaron los escaneos.
- **Los secretos:** cifrados en el repo con sops + age; la llave nunca vive en el servidor.

Lo que no:
- **Un solo servidor.** Sin alta disponibilidad: si el VPS desaparece, se reconstruye
  desde el repo y tus backups (hay una guía y un simulacro de restauración).
- En el modo TLS `http`, el nombre de cada app, también las privadas, aparece en los
  registros públicos de transparencia de certificados. Usa el modo `cloudflare` si te
  importa.
- Una cuenta de GitHub comprometida puede subir código que se despliega. Protégela con 2FA.

## Cómo funciona un deploy

```
git push ─► GitHub Actions ─► gitleaks ─► etapa "test" del Dockerfile ─► build ─► Trivy ─► GHCR
                                                                                       │
VPS ◄── SSH con una llave que solo puede correr "deploy <esta app>" ◄──────────────────┘
 └─ baja la imagen ─► migraciones ─► versión nueva junto a la vieja ─► chequeo de salud
                                       └─ sana: apaga la vieja   └─ falla: sigue la vieja y avisa
```

## Decisiones de diseño

Cada decisión importante está escrita, con su contexto, las alternativas y las
consecuencias, en [`docs/decisions/`](docs/decisions/). Algunas que marcaron el proyecto:
backups inmutables (0014), un mini-PaaS declarativo (0015), controles de calidad y
seguridad en el CI (0021) y apps de cualquier lenguaje (0022).

## Hoja de ruta

- [x] Prueba de punta a punta en un VPS nuevo (Azure, 1 vCPU y 1 GB)
- [ ] La misma prueba en más proveedores (Hetzner, DigitalOcean, Oracle, AWS)
- [ ] GitLab además de GitHub (repos, registro de imágenes y pipeline)
- [ ] CLI en inglés
- [x] Backups guiados (`andamio backups`)
- [ ] Alertas por Telegram guiadas (`andamio telegram`)
- [ ] Entornos de preview por pull request

## Licencia

[MIT](LICENSE) © 2026 Geovani Pérez Guerra
