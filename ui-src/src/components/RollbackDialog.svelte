<!--
  Volver a un deploy anterior: muestra la versión de ahora y a cuál vuelve, y corre el mismo
  `andamio app rollback <app> <commit>` (el deploy sin caída de siempre: si esa versión no queda
  sana, sigue la actual).
-->
<script lang="ts">
  import type { Deploy } from "../lib/api";
  import { ago, since } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { open = $bindable(false), app, current, target, ondone }: {
    open?: boolean; app: string; current: string; target: Deploy | null; ondone: () => void;
  } = $props();

  function go() {
    if (!target?.full) return;
    job.arm({ action: "rollback", app, sha: target.full }, () => ondone());
    void job.run();
    open = false;
  }
</script>

<Modal bind:open id="rollback" alert={t().rollbackAlert}>
  {#snippet heading()}{t().rollbackTitle} <code>{app}</code>{/snippet}
  {#if target}
    <div class="m-body">
      <div class="swap">
        <div class="ver">
          <span class="lbl">{t().nowRunning}</span>
          <code>{current || "?"}</code>
        </div>
        <svg viewBox="0 0 24 16" width="24" height="16" aria-hidden="true"><path d="M2 8h18M15 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
        <div class="ver to">
          <span class="lbl">{t().goesBackTo}</span>
          <code>{target.sha}</code>
        </div>
      </div>
      <p class="title">{target.title} <span class="muted">· {ago(since(target.created))}</span></p>
      <ul class="m-list kept">
        <li>{t().rollbackSafe}</li>
        <li>{t().rollbackData}</li>
      </ul>
      <p class="m-note">{t().rollbackPush}</p>
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (open = false)}>{t().cancel}</button>
      <button type="button" class="btn primary" onclick={go} disabled={job.locked || !target.full}>{t().rollbackGo(target.sha)}</button>
    </div>
  {/if}
</Modal>

<style>
  .swap { display: flex; align-items: center; gap: var(--space-4); color: var(--muted); }
  .ver { display: grid; gap: 2px; }
  .ver code { font-size: 16px; color: var(--ink); }
  .ver.to code { color: var(--accent); font-weight: 600; }
  .lbl { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }
  .title { margin: 0; font-size: 14.5px; }
  .muted { color: var(--muted); }
</style>
