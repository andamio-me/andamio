---
title: Varios servidores
description: Una copia de andamio por servidor, y el comando andamio en cualquier carpeta.
---

Cada servidor tiene **su propia copia** de andamio: un repo con su configuración, sus
secretos y sus apps. Para un segundo servidor (producción y pruebas, o dos clientes), corre
`andamio setup` otra vez con otro nombre de copia y sigue igual.

## Qué copia usa `andamio`

El comando `andamio` funciona en cualquier carpeta:

- **Dentro de la carpeta de una copia** (o de cualquier subcarpeta), usa esa.
- **Afuera**, usa la que elegiste con `andamio use`.

```bash
andamio use
```

```
Tus copias de andamio (● = la que usa `andamio` fuera de sus carpetas):
  ● /home/tu/mi-andamio        tudominio.com  (203.0.113.10)
    /home/tu/andamio-pruebas   pruebas.tudominio.com  (203.0.113.20)
```

```bash
andamio use pruebas.tudominio.com    # o la carpeta
```

Cada copia se anota sola la primera vez que la usas.

:::tip
Si un comando de apps no encuentra la app, te dice a qué servidor apunta esa copia y qué
apps tiene: casi siempre es que estás en la carpeta de otra copia.
:::

## Tu contraseña de sudo

Cada servidor tiene la suya, y andamio las recuerda por separado (15 minutos sin uso por defecto, solo
en memoria). `andamio olvidar` las borra todas.
