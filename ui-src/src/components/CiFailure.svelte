<!--
  "Ver por qué" de un deploy que falló, sin ir a GitHub: el paso que falló, la causa y las pistas
  💡 que deja el servidor (si el deploy llegó hasta él) y las últimas líneas del log, alrededor del
  error. El link a GitHub sigue ahí para ver todo.
-->
<script lang="ts">
  import Skeleton from "./Skeleton.svelte";
  import { tick } from "svelte";
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import Modal from "./Modal.svelte";

  let { open = $bindable(false), app, run }: { open?: boolean; app: string; run: api.Deploy | null } = $props();

  let data = $state<api.CiFailure | null>(null);
  let error = $state("");
  let logBox: HTMLElement | undefined = $state();

  $effect(() => {
    if (!open || !run) return;
    const r = run;
    data = null;
    error = "";
    api.ciFailure(app, r.id).then(async (d) => {
      if (d.error) error = d.error;
      else data = d;
      await tick();
      if (logBox) logBox.scrollTop = logBox.scrollHeight;   // el error está al final
    }).catch((e) => (error = String(e.message)));
  });
</script>

<Modal bind:open id="cifail" danger alert={t().ciFailAlert} wide>
  {#snippet heading()}{t().ciFailTitle} <code>{run?.sha ?? ""}</code>{/snippet}
  <div class="m-body">
    {#if run}<p class="title">{run.title}</p>{/if}
    {#if error}
      <p class="err">{error}</p>
    {:else if !data}
      <Skeleton rows={4} />
    {:else}
      {#if data.rejected}
        <p>{t().ciRejected}</p>
      {/if}
      {#each data.failed as f, i (i)}
        <p class="step"><span class="dot bad"></span><strong>{f.job}</strong>{#if f.steps.length} → {f.steps.join(", ")}{/if}</p>
      {/each}
      {#if data.cause}<p class="cause">{data.cause}</p>{/if}
      {#if data.hints.length}
        <ul class="hints">
          {#each data.hints as h, i (i)}<li><span aria-hidden="true">💡</span> {h}</li>{/each}
        </ul>
      {/if}
      {#if data.log.length}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <pre bind:this={logBox} tabindex="0" aria-label={t().ciLog}>{data.log.join("\n")}</pre>
      {/if}
    {/if}
  </div>
  <div class="m-foot">
    {#if data?.url || run?.url}<a class="btn quiet" href={data?.url || run?.url} target="_blank" rel="noopener noreferrer">{t().seeOnGithub}</a>{/if}
    <button type="button" class="btn" onclick={() => (open = false)}>{t().close}</button>
  </div>
</Modal>

<style>
  .title { margin: 0; font-weight: 500; }
  .err { margin: 0; color: var(--bad-text); }
  .step { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 14px; }
  .cause { margin: 0; padding: var(--space-2) var(--space-3); border-radius: 8px; background: color-mix(in oklch, var(--bad) 8%, var(--surface)); color: var(--bad-text); font-weight: 500; }
  .hints { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .hints li { padding: var(--space-2) var(--space-3); border-radius: 8px; background: color-mix(in oklch, var(--warn) 10%, var(--surface)); font-size: 14px; }
  pre {
    margin: 0; max-height: 340px; overflow: auto; padding: var(--space-3) var(--space-4); border-radius: 10px;
    background: var(--term); color: var(--term-ink); font: 12px/1.6 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere;
  }
</style>
