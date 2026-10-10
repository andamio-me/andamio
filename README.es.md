<p align="center">
  <img src="docs/assets/logo.svg" width="96" height="96" alt="andamio">
</p>

<h1 align="center">andamio</h1>

<p align="center">
  <b>Un PaaS seguro por defecto para un solo VPS.</b><br>
  Toma el servidor que acabas de comprar, lo endurece y despliega tus apps en él,<br>
  cada una aislada, con cada cambio pasando por git.
</p>

<p align="center"><a href="README.md">English</a></p>

> **Estado: alpha.** andamio mueve un servidor real en producción (apps, sincronización de
> archivos, monitoreo, backups) y la instalación guiada se probó de punta a punta en un VPS
> nuevo. Las funciones más recientes todavía se están probando en máquinas limpias: espera
> asperezas. La CLI habla español e inglés.

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
- Tu máquina: **Linux** (Ubuntu/Debian), **macOS**, o **Windows con WSL**
  ([instalar WSL](https://learn.microsoft.com/es-es/windows/wsl/install): `wsl --install` en
  PowerShell, y luego trabajas dentro de Ubuntu). `andamio setup` instala todo lo demás.

## Inicio rápido

```bash
# 1. Baja andamio (público, sin cuenta) y deja tu máquina lista, una vez: instala git,
#    gh, sops, age, ansible y sus colecciones (preguntando antes; sops se verifica contra
#    su checksum), configura tu identidad de git, inicia sesión en GitHub con una llave
#    SSH, y crea TU copia privada de andamio desde este template, y la clona.
curl -fsSL https://raw.githubusercontent.com/Geovani29/andamio/main/install.sh | sh
#    (¿prefieres leerlo antes? es corto; lo mismo a mano es
#     git clone https://github.com/Geovani29/andamio.git ~/andamio && ~/andamio/bin/andamio setup)

# 2. En tu copia: responde unas preguntas. Crea tu configuración, una llave de cifrado
#    (age) y los secretos de la plataforma, todo cifrado. No toca ningún servidor.
cd ~/mi-andamio
andamio init

# 3. Sube tu configuración cifrada
git add -A && git commit -m "andamio: mi servidor" && git push

# 4. Prepara el servidor: verifica su huella SSH, instala tu llave (sirve tanto si tu
#    proveedor te dio una llave como una contraseña de root), crea tu usuario, lo
#    endurece, arma la VPN y levanta la plataforma. Se puede repetir: retoma donde quedó.
andamio servidor
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

`andamio help` muestra todos los comandos, en el orden en que se usan.

`andamio` funciona en cualquier carpeta (el `setup` lo instala en `~/.local/bin`): dentro
de tu copia usa esa, y afuera, la última que usaste. ¿Varios servidores, cada uno con su
copia? `andamio use` las lista y `andamio use <carpeta o dominio>` elige cuál usar fuera de
sus carpetas.

## Despliega tu primera app

Tu app, en cualquier lenguaje, necesita un `Dockerfile`. **Si no lo tiene**, `app create`
detecta Node (npm, pnpm, yarn), Python (requirements.txt o pyproject.toml), Go o un sitio
estático y te propone uno listo para el pipeline: etapa `test` si hay tests, imagen final
mínima sin npm ni pip (para que Trivy no la bloquee) y usuario sin root. Confirmas el
comando de arranque y lo revisas antes de que se suba nada. Opcionalmente:

- una etapa llamada **`test`**: el CI la construye antes de desplegar; si falla, no se
  despliega nada;
- una **ruta de salud** HTTP (p. ej. `/healthz`) que responda 200 cuando la app está lista.

```bash
andamio app create miapp --repo <tú>/miapp --health /healthz
```

Registra la app (llave de deploy, variables del CI, base y usuario de Redis si los pides) y
te ofrece subir al repo de tu app lo que le falta: el Dockerfile (si se generó) y
`.github/workflows/andamio.yml`. Ese push arranca el primer deploy y lo ves ahí mismo:
tests, escaneo, build, deploy. Desde ahí, cada `git push` a `main` despliega.

Tu app queda en `https://miapp.ejemplo.com` (por la VPN, salvo que uses `--public`).

#### Dónde quedan tus apps

El dominio que le diste a `andamio init` es el **dominio de tu servidor**; cada app es un
subdominio suyo, con el nombre de la app (o `--host`):

| Dominio del servidor | `app create blog` | `--host api` | `--host @` |
|---|---|---|---|
| `ejemplo.com` | `blog.ejemplo.com` | `api.ejemplo.com` | `ejemplo.com` |
| `lab.ejemplo.com` | `blog.lab.ejemplo.com` | `api.lab.ejemplo.com` | `lab.ejemplo.com` |

Por eso creas dos registros DNS una sola vez: `ejemplo.com` y `*.ejemplo.com`. El `*` hace
que cualquier app futura apunte a tu servidor sin volver a tocar el DNS. El dominio del
servidor puede ser a su vez un subdominio (`lab.ejemplo.com`) si `ejemplo.com` ya se usa en
otro lado. Para un dominio fuera del de tu servidor (`api.suempresa.com`) o un nombre de más niveles
(`v2.api.ejemplo.com`), usa `--domain` (o después `app domain add`).

Opciones útiles: `--port` (por defecto, el `EXPOSE` del Dockerfile), `--public` (accesible
desde internet), `--db` (PostgreSQL), `--redis`, `--host <sub>` o `--host @` (dominio raíz),
`--mem 512m`.

```bash
andamio app stop miapp      # apagarla sin borrar nada (datos, base, secretos, dominio)
andamio app start miapp     # volver a encenderla
andamio app destroy miapp   # borrarla del todo: pide escribir su nombre y respalda su base antes
```

Una app detenida sigue detenida aunque vuelvas a aplicar el servidor, y un `git push` no la
despliega hasta que hagas `start`.

### Solo el backend (frontend en Vercel u otro lado)

```bash
andamio app create api --repo <tú>/backend --db --redis --public --host api \
  --cors https://miapp.vercel.app --domain api.suempresa.com
```

- `--public`: los navegadores y los servidores de Vercel tienen que poder llegar (sin él,
  solo por la VPN).
- PostgreSQL y Redis son propios de la app y **nunca se exponen a Internet**: solo tu backend
  llega a ellos. Tu frontend habla con el backend, no con la base.
- `--cors`: Traefik responde CORS solo para esos orígenes (nunca `*`); los demás sitios no
  reciben `Access-Control-Allow-Origin` y el navegador los bloquea. Repítelo para varios.
- `--domain`: un dominio propio además de `api.tudominio`, con su certificado de Let's
  Encrypt (apunta antes su registro A al servidor). Se puede repetir.

Después: `andamio app cors add|rm|list api <origen>` y `andamio app domain add|rm|list api <dominio>`.

### Secretos

Dos tipos, dos lugares:

**De ejecución** (tu app los lee mientras corre: claves de API, SMTP, Stripe...):

```bash
andamio app secret set miapp ANTHROPIC_API_KEY   # pide el valor, oculto
cat clave.txt | andamio app secret set miapp ANTHROPIC_API_KEY   # o desde un pipe
andamio app secret list miapp                    # solo nombres, nunca valores
andamio app secret rm miapp ANTHROPIC_API_KEY
```

El valor nunca va en la línea de comandos (ni queda en el historial de tu terminal). Se
guarda cifrado con sops en `apps/miapp/secrets.sops.env`, se hace commit (el mensaje lleva
solo el nombre) y se aplica: la app se reinicia con la variable nueva. Si ya existía, su
valor se reemplaza (`✓ actualizado`). Si el último deploy había fallado (típico: le faltaba
esa variable), te ofrece reintentarlo ahí mismo. `DOMAIN`, `DATABASE_URL`, `REDIS_URL` y
`TAG` los pone andamio y no se cambian a mano.

Para varias de una vez, guárdalas sin aplicar y aplica al final (una contraseña, un reinicio):

```bash
andamio app secret set miapp STRIPE_KEY --later
andamio app secret set miapp SMTP_PASSWORD --later
andamio app apply miapp
```

¿Por qué no GitHub Secrets para estos? Solo existen dentro del CI: llevarlos al servidor
obligaría a que la llave de deploy transporte secretos, y son de solo escritura, así que un
servidor reconstruido no tendría de dónde sacarlos. Con sops viven cifrados en tu repo y
`andamio servidor` los repone.

**De build** (solo para construir la imagen: el token de un paquete npm privado, el de
Sentry para subir source maps...): déjalos en GitHub Secrets y nómbralos en el `ci.yml` de
tu app:

```yaml
    with:
      build_secrets: NPM_TOKEN SENTRY_AUTH_TOKEN
    secrets: inherit
```

```dockerfile
RUN --mount=type=secret,id=NPM_TOKEN NPM_TOKEN=$(cat /run/secrets/NPM_TOKEN) npm ci
```

BuildKit monta cada uno solo durante ese `RUN`: nunca queda en una capa de la imagen.

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
| `andamio_tls` | `http` (por defecto: un certificado de Let's Encrypt por app, con cualquier DNS), `cloudflare` (un certificado comodín; necesita la zona en Cloudflare y un token de API) o `custom` (tu propio certificado, ver abajo) |
| `andamio_forge` | `github` (por defecto). Todo lo que andamio necesita de ella pasa por `bin/forge`; agregar GitLab es implementar ese archivo y su pipeline |
| `andamio_monitoring` | `auto` (por defecto), `minimo` (~115 MiB: métricas) o `completo` (~670 MiB: + logs, Grafana con alertas, Uptime Kuma). Bajar a `minimo` apaga lo que sobra; sus datos quedan por si vuelves |
| `andamio_backups` | `false` (por defecto). Lo activa `andamio backups`: ver abajo |
| `andamio_telegram` | `false` (por defecto) o `true`, con el token del bot y el chat en `host/sops/telegram-env.sops` |

### Actualizaciones

```bash
andamio update --check   # qué cambiaría
andamio update           # aplicar; luego: git diff, commit, push, andamio servidor
```

Trae las mejoras y los parches de seguridad de andamio sin tocar lo tuyo: tu configuración,
tus apps, tus secretos, tu certificado y el inventario. Un repo creado desde un template no
comparte historial con él, así que trabaja archivo por archivo con una fusión de tres vías
(lo tuyo, la versión de la que vienes, la nueva): lo que nunca tocaste se actualiza, lo que
solo cambiaste tú se respeta, y si cambiaron los dos lo combina, con marcas de conflicto
como las de git donde tu cambio y el de andamio tocan las mismas líneas. Exige el árbol
limpio, así que toda la actualización se ve en `git diff` y se puede deshacer.

### Chequeo de seguridad

```bash
andamio estado
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
andamio backups
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
andamio certificado fullchain.pem privada.key   # lo valida y lo guarda (la llave, cifrada con sops)
andamio certificado                             # muestra el actual y cuándo vence
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
- [x] CLI en inglés y español (`ANDAMIO_LANG=es` para español; si no, sigue a `LANG`)
- [ ] Nombres de las tareas de Ansible en inglés (hoy están en español)
- [x] Backups guiados (`andamio backups`)
- [ ] Alertas por Telegram guiadas (`andamio telegram`)
- [ ] Entornos de preview por pull request

## Licencia

[MIT](LICENSE) © 2026 Geovani Pérez Guerra
