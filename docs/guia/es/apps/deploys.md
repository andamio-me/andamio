---
title: Despliegues
description: Qué pasa, en orden, cada vez que haces git push a main.
---

Cada `git push` a `main` del repo de tu app la despliega. Así:

```
git push ─► GitHub Actions ─► gitleaks ─► etapa "test" ─► build ─► Trivy ─► GHCR
                                                                           │
tu VPS ◄── SSH con una llave que solo puede correr "deploy <esta app>" ◄───┘
  └─ baja la imagen ─► migraciones ─► versión nueva junto a la vieja ─► chequeo de salud
                                       └─ sana: apaga la vieja   └─ falla: sigue la vieja
```

## Paso a paso

1. **Secretos.** gitleaks busca claves y tokens que se colaron en el código. Si encuentra
   uno, no sigue.
2. **Tests.** Construye la etapa `test` de tu Dockerfile, si existe, en el lenguaje que sea.
   Si falla, no se despliega nada.
3. **Imagen y escaneo.** Construye la imagen y Trivy la revisa contra vulnerabilidades
   conocidas. Una imagen vulnerable nunca llega al registro.
4. **Publicación.** La imagen se sube a GHCR (el registro de GitHub), privada.
5. **Llave propia.** El pipeline entra a tu servidor con una llave que solo puede ejecutar
   el deploy de esa app. No abre una terminal.
6. **Migraciones.** Si tu app las define (`migrate` en `app.yml`), corren antes de cambiar
   lo que está en producción.
7. **Versión nueva al lado.** Arranca junto a la actual y tiene que pasar su chequeo de
   salud: tu ruta `--health`, o el `HEALTHCHECK` de la imagen, o 10 s sin reiniciarse.
8. **El cambio.** Recién ahí se apaga la anterior. Si algo falló, sigue la anterior y el
   pipeline te dice por qué: ver [Cuando algo falla](/es/docs/apps/failures/).
9. **Limpieza.** En el servidor quedan solo la imagen nueva y la anterior; las demás se
   borran para no llenar el disco (siguen en GHCR: `andamio app rollback` las vuelve a bajar).

Las imágenes se construyen en GitHub Actions, nunca en tu VPS: por eso alcanza un servidor
chico.

## Secretos de build

Algunos secretos solo hacen falta **para construir** la imagen, no para correrla: el token
de un paquete npm privado, el de Sentry para subir source maps. Esos van en los *Secrets*
del repo de tu app en GitHub, y se nombran en su workflow:

```yaml
# .github/workflows/andamio.yml
    with:
      build_secrets: NPM_TOKEN SENTRY_AUTH_TOKEN
    secrets:
      ANDAMIO_SECRETS: ${{ toJSON(secrets) }}   # ya viene así
```

Y en tu Dockerfile:

```dockerfile
RUN --mount=type=secret,id=NPM_TOKEN NPM_TOKEN=$(cat /run/secrets/NPM_TOKEN) npm ci
```

BuildKit monta cada uno solo durante ese `RUN`: nunca queda en una capa de la imagen. Los
secretos que tu app lee **mientras corre** van con
[`andamio app secret`](/es/docs/apps/secrets/).

## Si Trivy frena tu imagen

Las imágenes base oficiales suelen traer su gestor de paquetes (`npm`, `pip`, `setuptools`),
con sus propias vulnerabilidades, y en producción no se usa. Quítalo de la etapa final:

```dockerfile
RUN pip uninstall -y pip setuptools
# o
RUN rm -rf /usr/local/lib/node_modules/npm
```

Si los hallazgos están en tus dependencias, actualízalas. Los Dockerfiles que genera
andamio ya vienen así.

## Poner al día el pipeline de tus apps

El pipeline de cada app está fijado a una versión de andamio (un SHA en su
`.github/workflows/andamio.yml`): así una actualización de andamio nunca cambia cómo se
despliega una app sin aviso. Para traer las mejoras del pipeline (por ejemplo, las pistas de
error) a tus apps ya creadas:

```bash
andamio app ci-update          # todas
andamio app ci-update miapp    # una
```

Por defecto no despliega: las mejoras se usan en el próximo `git push` de cada app. Si
respondes que sí, despliega cada una en el momento.

## Ver los logs

```bash
andamio app logs miapp
```

Los logs en vivo del contenedor que está en producción.
