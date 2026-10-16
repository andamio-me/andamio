---
title: Front y back en un repo
description: Varias apps en un mismo repo (frontend/, backend/), cada una con su carpeta, su deploy y su llave.
---

Si tu repo tiene el front y el back juntos (un monorepo), cada carpeta se despliega como
una app aparte:

```text
mi-proyecto/
├── frontend/     → app web
├── backend/      → app api
└── packages/     (código compartido, opcional)
```

```bash
andamio app create web --repo tu-usuario/mi-proyecto --dir frontend --host miapp --public
andamio app create api --repo tu-usuario/mi-proyecto --dir backend --host miapp --path /api \
  --public --db --health /api/health
```

El front queda en `https://miapp.tudominio.com` y el back en `https://miapp.tudominio.com/api`:
**el mismo dominio, sin CORS** y con las cookies funcionando sin trucos. Si prefieres el back
en su propio subdominio, usa `--host api` sin `--path` (y `--cors` para el front).

## Qué hace `--dir`

- **Su Dockerfile** está en esa carpeta. Si no tiene, andamio le propone uno (como con una
  app en la raíz) y la revisión previa mira esa carpeta.
- **Su propio pipeline**: `.github/workflows/andamio-<app>.yml`. Solo corre cuando cambia algo
  de su carpeta: un cambio en el front no redespliega el back.
- **Su propia imagen** (`ghcr.io/tu-usuario/<app>`) y **su propia llave de deploy**
  (`DEPLOY_SSH_KEY_<APP>` en el repo). Cada llave solo puede desplegar su app.
- Rollback, **Desplegar ahora**, reintentar y la lista de deploys del panel ven solo las
  corridas de esa app.

## Código compartido

Si las dos apps usan una carpeta común (`packages/`) o el lockfile de la raíz (pnpm o npm
workspaces), la imagen se construye desde la raíz y con el Dockerfile de la carpeta:

```bash
andamio app create api --repo tu-usuario/mi-proyecto --dir backend --context . --watch packages/
```

| Opción | Qué hace |
|---|---|
| `--context .` | Construye desde la raíz del repo (el Dockerfile sigue siendo `backend/Dockerfile`; sus `COPY` son relativos a la raíz). También redespliega si cambian los manifiestos de la raíz: `package.json`, los lockfiles, `pnpm-workspace.yaml` |
| `--watch packages/` | Además de su carpeta, un cambio ahí también la despliega. Una carpeta (`packages/`), un archivo (`tsconfig.base.json`) o un patrón (`config/*.yml`). Se repite para varias |

## Cambiarlo después

```bash
andamio app source api                          # de dónde sale: repo, carpeta, rutas
andamio app source api --watch-add packages/    # otra ruta que dispara su deploy
andamio app source api --watch-rm packages/
andamio app source api --context .              # construir desde la raíz (- para volver a su carpeta)
andamio app source api --dir services/api       # se mudó de carpeta
```

Reescribe su pipeline en el repo de la app y lo guarda en `app.yml`; no toca el servidor. Cambiar
la carpeta o desde dónde se construye despliega; agregar o quitar rutas, no. En el panel:
**Ajustes → Código**.

## Rutas

Con `--path /api`, Traefik le manda a esa app todo lo que empiece con `/api` y el resto
al front. La ruta **no se quita**: tu back recibe `/api/users`, así que sus rutas llevan el
prefijo (lo normal en Express, FastAPI, Django y compañía).

Dos apps no pueden tener el mismo host y la misma ruta.

## En el panel

En **Nueva app**, al elegir un repo con varias carpetas, el panel te las muestra y eliges cuál:

- Primero las que el repo declara como parte de su monorepo (workspaces de pnpm, npm o yarn,
  `lerna.json`, `go.work`), y después las que tienen Dockerfile o un proyecto, hasta 3 niveles.
- Cada una dice qué es: **front** (Next.js, Vite, Astro…), **API** (Express, NestJS, FastAPI,
  Django…), **worker** (Celery…) o **sitio**.
- Las **librerías** (paquetes que solo exportan código, como `packages/ui`) van aparte, en
  "Ver N librerías": no se despliegan solas.
- Las carpetas dentro de una app (`frontend/public`, `backend/src`) no salen: son parte de ella.
- Con muchas carpetas aparece un buscador, y **Otra carpeta** revisa cualquier ruta que escribas.

Desde la terminal, si el repo tiene varias apps y la raíz no es una, `andamio app create` te
dice cuáles son y te pide `--dir`.

Si otra app ya sale de ese repo, el panel te propone usar su misma dirección con la ruta `/api`.
En el menú, las apps de un mismo repo aparecen juntas, con su carpeta al lado.
