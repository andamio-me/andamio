---
title: Variables y secretos
description: Claves de API, contraseñas y cualquier variable de entorno de tu app, cifradas.
---

```bash
andamio app secret set miapp STRIPE_KEY
```

Te pide el valor **oculto** (no se ve al escribir ni queda en el historial de tu terminal).
Sirve igual para algo secreto (una API key) y para algo que no lo es (un ajuste).

## Qué pasa

1. El valor se guarda **cifrado** con sops en `apps/miapp/secrets.sops.env`, en tu copia.
2. Se hace commit y push; el mensaje lleva solo el nombre, nunca el valor.
3. Se aplica en el servidor: tu app se **reinicia** con la variable nueva, en segundos.
   No hace falta un deploy, porque la imagen es la misma.

```
✓ STRIPE_KEY agregado (apps/miapp/secrets.sops.env, cifrado)
✓ miapp ya corre con los cambios (reiniciada, sin deploy: la imagen es la misma)
```

Si ya existía, su valor se **reemplaza** (`✓ STRIPE_KEY actualizado`). Nunca hay dos con el
mismo nombre.

## Si el último deploy falló

Típico: subiste código que lee una variable nueva y te olvidaste de crearla. El deploy falla
(y tu versión anterior sigue en línea). Al crear la variable, andamio te pregunta:

```
El último deploy de miapp falló. ¿Lo reintento ahora, con los cambios? [S/n]
```

Y relanza ese deploy sin que entres a GitHub.

## Varias de una vez

Desde un archivo `.env` (una `CLAVE=valor` por línea; `export` y las comillas se aceptan, las
líneas con `#` se ignoran): se revisan todas antes de tocar nada, se cifran juntas y la app se
reinicia una sola vez. El commit lleva solo los nombres.

```bash
andamio app secret import miapp .env.produccion
```

En el panel: **Variables → Pegar varias**, pegas el `.env` o eliges el archivo, y ves cuáles son
nuevas, cuáles reemplazan y cuáles tienen un problema, con los valores ocultos.

Otra forma: guardarlas una por una sin aplicar y aplicar al final, una sola vez:

```bash
andamio app secret set miapp STRIPE_KEY --later
andamio app secret set miapp SMTP_PASSWORD --later
andamio app apply miapp
```

## Otros comandos

```bash
andamio app secret list miapp                  # solo los nombres, nunca los valores
andamio app secret rm miapp STRIPE_KEY         # quitarla
cat clave.txt | andamio app secret set miapp STRIPE_KEY   # el valor desde un archivo
```

`DOMAIN`, `DATABASE_URL`, `MYSQL_URL`, `REDIS_URL` y `TAG` los pone andamio y no se cambian a mano.

## Por qué no GitHub Secrets

Los Secrets de GitHub solo existen dentro del pipeline: llevarlos a tu servidor obligaría a
que la llave de deploy transporte secretos, y son de solo escritura, así que un servidor
reconstruido no tendría de dónde sacarlos. Con sops viven cifrados en tu repo, la llave para
descifrarlos está **solo en tu máquina**, y `andamio servidor` los repone.

Los Secrets de GitHub sí sirven para los secretos **de build**. Ver
[Despliegues](/es/docs/apps/deploys/#secretos-de-build).
