<!--
  Restaurar una app desde un respaldo, en dos pasos (como borrar): 1) eliges la app y lees qué
  se reemplaza, qué se guarda antes y qué no se toca; 2) escribes su nombre. Corre el mismo
  `andamio app restore <app> <respaldo>`: comprueba el respaldo en una base temporal antes de
  tocar nada y guarda lo de ahora en /srv/andamio/archive/.
-->
<script lang="ts">
  import { tick } from "svelte";
  import { untrack } from "svelte";
  import type { App, Snapshot } from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { open = $bindable(false), snapshot, apps, preset = "", ondone }: {
    open?: boolean; snapshot: Snapshot | null; apps: App[]; preset?: string; ondone: () => void;
  } = $props();

  // Solo las que tienen algo que restaurar: base o carpetas persistentes.
  const restorable = $derived(apps.filter((a) => a.db || a.mysql || a.volumes.length));
  let step = $state<1 | 2>(1);
  let app = $state("");
  let typed = $state("");
  let input: HTMLInputElement | undefined = $state();
  const chosen = $derived(restorable.find((a) => a.name === app) ?? null);
  const ready = $derived(chosen !== null && typed === app && !job.locked);
  const when = $derived(snapshot?.time ? new Intl.DateTimeFormat(undefined, { dateStyle: "long", timeStyle: "short" }).format(snapshot.time * 1000) : "");

  // Cada vez que se abre: desde el paso 1, con la app que venía elegida (si hay).
  $effect(() => {
    if (!open) return;
    untrack(() => {
      step = 1;
      typed = "";
      app = restorable.some((a) => a.name === preset) ? preset : restorable.length === 1 ? restorable[0]!.name : "";
    });
  });

  function next() {
    step = 2;
    void tick().then(() => input?.focus());
  }
  function restore(e: SubmitEvent) {
    e.preventDefault();
    if (!ready || !snapshot) return;
    job.arm({ action: "restore", app, snapshot: snapshot.short, confirm: typed, understood: true }, () => ondone());
    void job.run();
    open = false;
  }
</script>

<Modal bind:open id="restore" danger alert={t().restoreAlert} wide dirty={typed.length > 0}>
  {#snippet heading()}{t().restoreTitle} <code>{snapshot?.short ?? ""}</code>{/snippet}
  {#if step === 1}
    <div class="m-body">
      <p class="lead">{t().restoreLead(when)}</p>
      {#if restorable.length}
        <fieldset>
          <legend>{t().restoreWhich}</legend>
          <div class="apps">
            {#each restorable as a (a.name)}
              <label class:on={app === a.name}>
                <input type="radio" name="restore-app" value={a.name} bind:group={app} />
                <span class="nm">{a.name}</span>
                <span class="what">{[a.db && "PostgreSQL", a.volumes.length && t().foldersN(a.volumes.length)].filter(Boolean).join(" · ")}</span>
              </label>
            {/each}
          </div>
        </fieldset>
      {:else}
        <p class="m-note">{t().restoreNone}</p>
      {/if}
      {#if chosen}
        <div class="m-cols">
          <div>
            <h3>{t().restoreSwap}</h3>
            <ul class="m-list swap">
              {#if chosen.db}<li>{t().restoreDb}</li>{/if}
              {#if chosen.mysql}<li>{t().restoreDbMysql}</li>{/if}
              {#if chosen.volumes.length}<li>{t().restoreFolders(chosen.volumes.join(", "))}</li>{/if}
            </ul>
            <h3 class="sp">{t().restoreSaved}</h3>
            <ul class="m-list saved"><li>{t().restoreSavedWhere}</li></ul>
          </div>
          <div>
            <h3>{t().deleteKeep}</h3>
            <ul class="m-list kept">
              {#if chosen.redis}<li>{t().restoreKeepRedis}</li>{/if}
              <li>{t().restoreKeepCode}</li>
              <li>{t().restoreKeepSecrets}</li>
            </ul>
          </div>
        </div>
        <p class="m-note">{t().restoreStops}</p>
      {/if}
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (open = false)}>{t().cancel}</button>
      <button type="button" class="btn red" onclick={next} disabled={!chosen}>{chosen ? t().understandRestore(chosen.name) : t().pickApp}</button>
    </div>
  {:else}
    <form class="m-body" onsubmit={restore} autocomplete="off">
      <label for="restore-name">{t().typeNamePre} <code>{app}</code> {t().typeNamePost}</label>
      <input id="restore-name" bind:this={input} bind:value={typed} class="mono name" spellcheck="false" autocomplete="off"
        aria-invalid={typed && typed !== app ? "true" : undefined} />
      <div class="foot">
        <button type="button" class="btn quiet" onclick={() => (step = 1)}>{t().backStep}</button>
        <button type="submit" class="btn red solid" disabled={!ready}>{t().restoreGo(app)}</button>
      </div>
    </form>
  {/if}
</Modal>

<style>
  .lead { margin: 0; font-size: 14.5px; }
  fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
  legend { font-size: 13px; color: var(--muted); margin-bottom: var(--space-2); padding: 0; }
  .apps { display: grid; gap: var(--space-2); }
  .apps label {
    display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3);
    border: 1px solid var(--line); border-radius: 8px; cursor: pointer; transition: border-color 150ms var(--ease), background-color 150ms var(--ease);
  }
  .apps label.on { border-color: var(--accent); background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .apps input { accent-color: var(--accent); margin: 0; }
  .nm { font-weight: 600; }
  .what { color: var(--muted); font-size: 13px; margin-left: auto; }
  h3.sp { margin-top: var(--space-3) !important; }
  .foot { display: flex; justify-content: flex-end; gap: var(--space-2); padding-top: var(--space-2); }
  label[for] { font-size: 14px; }
  .name {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line);
    border-radius: 8px; padding: 9px 12px; width: 100%;
  }
  .name:focus-visible { outline: 3px solid color-mix(in oklch, var(--bad) 28%, transparent); outline-offset: 0; border-color: var(--bad); }
  .btn.red { color: var(--bad-text); border-color: color-mix(in oklch, var(--bad) 45%, var(--line)); }
  .btn.red:hover:not(:disabled) { background: color-mix(in oklch, var(--bad) 8%, var(--surface)); border-color: var(--bad); }
  .btn.red.solid { background: var(--bad); color: oklch(0.985 0.005 25); border-color: var(--bad); }
  .btn.red.solid:hover:not(:disabled) { background: color-mix(in oklch, var(--bad) 86%, var(--ink)); }
</style>
