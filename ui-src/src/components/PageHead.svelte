<!--
  El encabezado de una página de la plataforma (Respaldos, Historial, Ajustes, Nueva app): título,
  una línea de qué es y, a la derecha, sus acciones. El mismo ritmo que el de una app (título
  grande, línea abajo). Sin "volver": el sidebar siempre está.
-->
<script lang="ts">
  import type { Snippet } from "svelte";

  let { title, desc = "", actions }: { title: string; desc?: string; actions?: Snippet } = $props();
</script>

<header class="phead">
  <div class="ptext">
    <h1>{title}</h1>
    {#if desc}<p class="pdesc">{desc}</p>{/if}
  </div>
  {#if actions}<div class="pacts">{@render actions()}</div>{/if}
</header>

<style>
  .phead {
    display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: var(--space-3) var(--space-5);
    padding-bottom: var(--space-5); border-bottom: 1px solid var(--line); margin-bottom: var(--space-5);
  }
  .ptext { min-width: 0; }
  h1 { margin: 0; }
  .pdesc { margin: 6px 0 0; max-width: 64ch; color: var(--muted); font-size: 15px; line-height: 1.5; }
  .pacts { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
</style>
