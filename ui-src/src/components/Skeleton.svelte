<!--
  Mientras carga (el servidor tarda unos segundos por SSH): la forma de lo que va a aparecer, para
  que nada salte al llegar. "detail" = el detalle de una app; "rows" = una tabla.
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  let { kind = "rows", rows = 3 }: { kind?: "detail" | "rows"; rows?: number } = $props();
</script>

<div class="sk" role="status" aria-label={t().loading} aria-busy="true">
  {#if kind === "detail"}
    <div class="bar w20 short"></div>
    <div class="head"><div class="bar w40 tall"></div><div class="bar w15"></div></div>
    <div class="cols">
      {#each [0, 1] as c (c)}
        <div class="col">
          <div class="bar w25 short"></div>
          {#each [0, 1, 2, 3, 4] as r (r)}<div class="kv"><div class="bar w30"></div><div class="bar w50"></div></div>{/each}
        </div>
      {/each}
    </div>
    <div class="bar w25 short gap"></div>
    <div class="block"></div>
  {:else}
    <div class="box list">
      {#each Array(rows) as _, i (i)}<div class="row"><div class="bar w20"></div><div class="bar w40"></div><div class="bar w15"></div></div>{/each}
    </div>
  {/if}
</div>

<style>
  .sk { display: grid; gap: var(--space-4); }
  .bar { height: 12px; border-radius: 6px; background: color-mix(in oklch, var(--ink) 9%, var(--canvas)); }
  .bar.tall { height: 30px; border-radius: 8px; }
  .bar.short { height: 10px; }
  .w15 { width: 15%; } .w20 { width: 20%; } .w25 { width: 25%; } .w30 { width: 30%; } .w40 { width: 40%; } .w50 { width: 50%; }
  .head { display: flex; align-items: center; gap: var(--space-5); padding-bottom: var(--space-5); border-bottom: 1px solid var(--line); }
  .cols { display: grid; grid-template-columns: 1.2fr 1fr; gap: var(--space-7); }
  .col { display: grid; gap: var(--space-3); }
  .kv { display: grid; grid-template-columns: 112px 1fr; gap: var(--space-4); align-items: center; }
  .gap { margin-top: var(--space-5); }
  .block { height: 160px; border-radius: 12px; background: color-mix(in oklch, var(--ink) 6%, var(--canvas)); }
  .list { padding: 0; }
  .row { display: flex; gap: var(--space-5); padding: var(--space-4); border-bottom: 1px solid var(--line); }
  .row:last-child { border-bottom: 0; }
  @media (prefers-reduced-motion: no-preference) {
    .bar, .block { animation: shimmer 1.4s ease-in-out infinite; }
  }
  @keyframes shimmer { 50% { opacity: 0.55; } }
  @media (max-width: 820px) { .cols { grid-template-columns: 1fr; } }
</style>
