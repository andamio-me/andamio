<!--
  Las últimas corridas programadas de una tarea (hasta 5, las guarda el servidor): cuándo, cuánto
  tardó, cómo terminó y su salida (las que fallaron, abiertas). Las corridas a mano no se guardan:
  su salida se ve en la terminal.
-->
<script lang="ts">
  import Skeleton from "./Skeleton.svelte";
  import * as api from "../lib/api";
  import { ago } from "../lib/format";
  import { t } from "../lib/i18n.svelte";

  let { app, task }: { app: string; task: string } = $props();

  let runs = $state<api.CronRun[] | null>(null);
  let error = $state("");
  $effect(() => {
    const a = app, k = task;
    api.cronRuns(a, k).then((r) => (runs = r.runs)).catch((e) => { runs = []; error = String(e.message); });
  });
  const fmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
</script>

<div class="runs">
  {#if runs === null}
    <Skeleton rows={2} />
  {:else if error}
    <p class="muted">{error}</p>
  {:else if !runs.length}
    <p class="muted">{t().noRuns}</p>
  {:else}
    {#each runs as r (r.start)}
      <details open={r.rc !== 0}>
        <summary>
          <span class={`dot ${r.rc === 0 ? "ok" : "bad"}`}></span>
          <span class="st">{r.rc === 0 ? t().okShort : t().code(r.rc)}</span>
          <span>{fmt.format(r.start * 1000)}</span>
          <span class="muted">· {ago(Date.now() / 1000 - r.start)} · {r.secs} s</span>
        </summary>
        <pre>{r.output || t().noOutput}</pre>
      </details>
    {/each}
  {/if}
</div>

<style>
  .runs { display: grid; gap: var(--space-2); padding: var(--space-2) 0 0; }
  .muted { color: var(--muted); font-size: 13.5px; margin: 0; }
  details { border: 1px solid var(--line); border-radius: 8px; background: var(--canvas); }
  summary { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); cursor: pointer; font-size: 13.5px; }
  .st { font-weight: 600; }
  pre {
    margin: 0; padding: var(--space-3) var(--space-4); border-top: 1px solid var(--line); max-height: 260px; overflow: auto;
    background: var(--term); color: var(--term-ink); font: 12.5px/1.6 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere;
    border-radius: 0 0 8px 8px;
  }
</style>
