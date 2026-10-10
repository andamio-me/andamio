---
title: Administrar una app
description: Listar, ver logs, apagar, volver atrás, aplicar cambios y borrar.
---

## Ver tus apps

```bash
andamio app list
```

```
APP          URL                                ACCESO  ESTADO
blog         https://blog.tudominio.com         public  Up 3 hours (healthy)
panel        https://panel.tudominio.com        vpn     Up 2 days (healthy)
```

## Logs en vivo

```bash
andamio app logs miapp
```

## Apagar y encender

```bash
andamio app stop miapp     # la apaga sin borrar nada: datos, base, secretos y dominio quedan
andamio app start miapp    # la vuelve a encender
```

Una app detenida sigue detenida aunque vuelvas a aplicar el servidor, y un `git push` no la
despliega hasta que hagas `start`. Libera su memoria y su CPU.

## Volver atrás

```bash
andamio app rollback miapp
```

Vuelve al deploy exitoso anterior.

## Aplicar cambios

```bash
andamio app apply miapp
```

Aplica en el servidor lo que esté pendiente de esa app (variables guardadas con `--later`,
cambios a mano en `app.yml`), con un solo reinicio. Corre solo las tareas de esa app: tarda
segundos.

## Borrarla

```bash
andamio app destroy miapp
```

Te pide escribir su nombre para confirmar, y antes de borrar respalda su base. Quita su
contenedor, su configuración, su llave de deploy, su base y su usuario de Redis.

El repo de la app y sus imágenes en GHCR quedan en GitHub: bórralos tú si ya no los quieres.

## Recursos

Por defecto cada app tiene 256 MB de RAM y media CPU. Para cambiarlo, en
`apps/miapp/app.yml`:

```yaml
resources:
  mem: 512m
  cpus: 1
  pids: 200
```

Y `andamio app apply miapp`.
