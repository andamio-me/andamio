<!--
  Historial: los cambios de tu copia (sus commits), del más nuevo al más viejo, por día. Los de
  configuración de una app muestran sus líneas y se pueden deshacer (andamio app revert): una
  ventana muestra qué vuelve atrás y corre el comando en la terminal. Con `app`, solo los de esa
  app (y sin el encabezado de página: va dentro del detalle).
-->
<script lang="ts">
  import PageHead from "./PageHead.svelte";
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { ago } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import Skeleton from "./Skeleton.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { app = "", embedded = false, limit = 0 }: { app?: string; embedded?: boolean; limit?: number } = $props();

  let changes = $state<api.Change[] | null>(null);
  let error = $state("");
  let onlyApps = $state(true);
  let undoing = $state<api.Change | null>(null);
  let undoOpen = $state(false);

  async function load() {
    try {
      changes = (await api.history(app)).changes;
    } catch (e) {
      error = String((e as Error).message);
    }
  }
  onMount(() => void load());

  const now = () => Date.now() / 1000;
  const shown = $derived.by(() => {
    const list = (changes ?? []).filter((c) => !onlyApps || app || c.kind !== "platform");
    return limit ? list.slice(0, limit) : list;
  });
  const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" });
  const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
  const day = (at: number) => dayFmt.format(at * 1000);
  const kindLabel = (k: api.Change["kind"]) => t().changeKind[k];
  // "feat(apps): web: resources.mem=512m" → "resources.mem=512m": el prefijo ya lo dice la etiqueta.
  const clean = (c: api.Change) => c.subject.replace(/^[a-z]+(\([^)]*\))?:\s*/, "").replace(new RegExp(`^${c.apps[0] ?? "\\0"}:\\s*`), "");

  function undo() {
    if (!undoing) return;
    job.arm({ action: "revert", app: undoing.apps[0]!, commit: undoing.sha }, () => void load());
    void job.run();
    undoOpen = false;
  }
</script>

{#if !embedded}
  <PageHead title={app ? t().historyOf(app) : t().history} desc={t().historyDesc}>
    {#snippet actions()}
      {#if !app}
        <label class="check"><input type="checkbox" bind:checked={onlyApps} /> {t().onlyAppChanges}</label>
      {/if}
    {/snippet}
  </PageHead>
{/if}

{#if error}
  <p class="box empty">{error}</p>
{:else if !changes}
  <div class="pad"><Skeleton rows={4} /></div>
{:else if !shown.length}
  <p class="box empty">{t().noChanges}</p>
{:else}
  <ol class="days" class:embedded>
    {#each shown as c, i (c.sha)}
      {#if !embedded && (i === 0 || day(shown[i - 1]!.at) !== day(c.at))}
        <li class="day">{day(c.at)}</li>
      {/if}
      <li class="change">
        <div class="top">
          <span class={`kind ${c.kind}`}>{kindLabel(c.kind)}</span>
          {#each c.apps as a (a)}{#if !app}<a class="app" href={`#/app/${a}`}>{a}</a>{/if}{/each}
          <span class="subject">{clean(c)}</span>
          <span class="meta"><code>{c.short}</code> · <span title={new Date(c.at * 1000).toLocaleString()}>{embedded ? ago(now() - c.at) : timeFmt.format(c.at * 1000)}</span></span>
          {#if c.revertible}
            <button type="button" class="btn small quiet" disabled={job.locked} onclick={() => { undoing = c; undoOpen = true; }}>{t().undo}</button>
          {/if}
        </div>
        {#if c.lines.length}
          <pre class="diff">{#each c.lines as l, k (k)}<span class:add={l.startsWith("+")} class:del={l.startsWith("-")}>{l}
</span>{/each}</pre>
        {/if}
      </li>
    {/each}
  </ol>
  {#if embedded && changes.length > shown.length}
    <a class="more" href={`#/history/${app}`}>{t().seeAllChanges}</a>
  {/if}
{/if}

<Modal bind:open={undoOpen} id="undo" alert={t().undoAlert}>
  {#snippet heading()}{t().undoTitle} <code>{undoing?.short ?? ""}</code>{/snippet}
  {#if undoing}
    <div class="m-body">
      <p class="lead"><strong>{undoing.apps[0]}</strong>: {clean(undoing)} <span class="muted">· {ago(now() - undoing.at)}</span></p>
      <p class="m-note">{t().undoExplain}</p>
      <pre class="diff">{#each undoing.lines as l, k (k)}<span class:add={l.startsWith("-")} class:del={l.startsWith("+")}>{l.startsWith("+") ? "-" : "+"}{l.slice(1)}
</span>{/each}</pre>
      <p class="m-note">{t().undoNote}</p>
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (undoOpen = false)}>{t().cancel}</button>
      <button type="button" class="btn primary" onclick={undo} disabled={job.locked}>{t().undoGo}</button>
    </div>
  {/if}
</Modal>

<style>
  .check { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
  .check input { accent-color: var(--accent); margin: 0; }
  .muted { color: var(--muted); }
  .pad { padding: var(--space-6) 0; }
  .empty { margin: 0; padding: var(--space-3) var(--space-4); color: var(--muted); }
  .days { list-style: none; margin: 0; padding: 0; }
  .day { font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; padding: var(--space-5) 0 var(--space-2); }
  .day:first-child { padding-top: var(--space-2); }
  .change { padding: var(--space-3) var(--space-4); border: 1px solid var(--line); border-radius: 10px; background: var(--surface); margin-bottom: var(--space-2); }
  .embedded .change { margin-bottom: 0; border-radius: 0; border-bottom-width: 0; }
  .embedded .change:first-child { border-radius: 12px 12px 0 0; }
  .embedded .change:last-child { border-radius: 0 0 12px 12px; border-bottom-width: 1px; }
  .embedded .change:only-child { border-radius: 12px; }
  .top { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); }
  .kind { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: var(--sunken); color: var(--muted); white-space: nowrap; }
  .kind.config { background: color-mix(in oklch, var(--accent) 12%, var(--surface)); color: var(--accent); }
  .kind.create { background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .kind.destroy { background: color-mix(in oklch, var(--bad) 12%, var(--surface)); color: var(--bad-text); }
  .kind.secrets { background: color-mix(in oklch, var(--warn) 14%, var(--surface)); color: var(--warn-text); }
  .app { font-weight: 600; color: var(--ink); }
  .subject { flex: 1; min-width: 200px; }
  .meta { color: var(--muted); font-size: 13px; white-space: nowrap; }
  .diff {
    margin: var(--space-2) 0 0; padding: var(--space-2) var(--space-3); border-radius: 8px; background: var(--sunken);
    font: 12.5px/1.6 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; color: var(--muted);
  }
  .diff .add { color: var(--ok-text); }
  .diff .del { color: var(--bad-text); }
  .more { display: inline-block; margin-top: var(--space-2); font-size: 14px; }
  .lead { margin: 0; }
</style>
