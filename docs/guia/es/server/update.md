---
title: Actualizar
description: Trae las mejoras y los parches de andamio sin tocar lo tuyo.
---

```bash
andamio update --check   # qué cambiaría, sin tocar nada
andamio update           # aplicarlo
```

Trae las mejoras y los parches de seguridad de andamio **sin tocar lo tuyo**: tu
configuración, tus apps, tus secretos, tu certificado y el inventario.

## Cómo funciona

Tu copia nació de la plantilla, así que no comparte historial de git con ella. Por eso
`update` trabaja **archivo por archivo**, con una fusión de tres vías: lo tuyo, la versión
de andamio de la que vienes y la nueva.

- Lo que nunca tocaste se actualiza.
- Lo que solo cambiaste tú se respeta.
- Si cambiaron los dos, lo combina. Si chocan en las mismas líneas, deja marcas de
  conflicto como las de git (`<<<<<<<` y `>>>>>>>`) para que elijas.

## Al terminar

Exige el árbol limpio antes de empezar. Si no hubo conflictos, te ofrece subirlo en un solo
commit:

```
¿Lo subo ya? (commit y push; `git revert HEAD` lo deshace)
 › Sí, con el mensaje «andamio: actualización a 9606291a»
   Sí, escribo yo el mensaje
   No, primero lo reviso (git diff)
```

Y te dice si hace falta aplicar algo en el servidor:

- **Cambió lo que corre en el servidor** (Ansible, scripts, stacks): aplícalo con
  `andamio servidor`.
- **Solo cambió andamio en tu máquina**: no hay nada que aplicar.

Para deshacer una actualización entera: `git revert HEAD`.
