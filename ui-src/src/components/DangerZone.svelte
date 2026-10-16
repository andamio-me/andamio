<!--
  Zona de peligro, al pie del detalle: restaurar desde un respaldo y "Borrar esta app". El borrado
  se confirma en una ventana (como GitHub), en dos pasos: 1) qué se borra y qué no, y "Entiendo";
  2) escribir el nombre exacto. Es la misma ventana que las demás (Modal): el fondo no se mueve y,
  con algo escrito, un clic afuera no la cierra. Corre el mismo `andamio app destroy`, que
  respalda la base antes de borrarla; mientras corre, la página queda bloqueada.
-->
<script lang="ts">
  import { tick } from "svelte";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { app, repo, protectedApp = false, restorable = false }: {
    app: string; repo: string; protectedApp?: boolean; restorable?: boolean;
  } = $props();

  let isOpen = $state(false);
  let step = $state<1 | 2>(1);
  let typed = $state("");
  let input: HTMLInputElement | undefined = $state();
  let firstBtn: HTMLButtonElement | undefined = $state();
  const ready = $derived(typed === app && !job.locked);

  function open() {
    step = 1;
    typed = "";
    isOpen = true;
    void tick().then(() => firstBtn?.focus());
  }
  function next() {
    step = 2;
    void tick().then(() => input?.focus());
  }
  function destroy(e: SubmitEvent) {
    e.preventDefault();
    if (!ready) return;
    if (!job.arm({ action: "destroy", app, confirm: typed, understood: true }, (ok) => { if (ok) location.hash = "#/"; })) return;
    void job.run();   // confirmado dos veces: corre directo, con su salida en la terminal
    isOpen = false;
  }
</script>

<section class="sec" aria-labelledby="danger-title">
  <div class="shead"><div><h2 id="danger-title" class="red-title">{t().danger}</h2></div></div>
  <div class="zone">
    {#if restorable}
      <div class="row">
        <div>
          <strong>{t().restoreFromBackup}</strong>
          <p>{t().restoreFromBackupDesc}</p>
        </div>
        <a class="btn small" href={`#/backups/${app}`}>{t().chooseBackup}</a>
      </div>
    {/if}
    <div class="row">
      <div>
        <strong>{t().deleteApp}</strong>
        <p>{protectedApp ? t().dashboardProtected : t().deleteDesc}</p>
      </div>
      <button type="button" class="btn small red" onclick={open} disabled={protectedApp || job.locked}>{t().deleteApp}</button>
    </div>
  </div>
</section>

<Modal bind:open={isOpen} id="del" danger alert={t().deleteAlert} dirty={typed.length > 0}>
  {#snippet heading()}{t().deleteTitle} <code>{app}</code>{/snippet}
  {#if step === 1}
    <div class="m-body">
      <div class="m-cols">
        <div>
          <h3>{t().deleteWhat}</h3>
          <ul class="m-list gone">
            <li>{t().deleteShort1}</li><li>{t().deleteShort2}</li><li>{t().deleteShort3}</li><li>{t().deleteShort4}</li>
          </ul>
        </div>
        <div>
          <h3>{t().deleteKeep}</h3>
          <ul class="m-list kept"><li>{t().keep1(repo)}</li><li>{t().keep2}</li></ul>
        </div>
      </div>
      <p class="m-note">{t().deleteBackupNote}</p>
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (isOpen = false)}>{t().cancel}</button>
      <button type="button" class="btn red" bind:this={firstBtn} onclick={next}>{t().understandDelete(app)}</button>
    </div>
  {:else}
    <form class="m-body" onsubmit={destroy} autocomplete="off">
      <label for="del-name">{t().typeNamePre} <code>{app}</code> {t().typeNamePost}</label>
      <input id="del-name" bind:this={input} bind:value={typed} class="mono name" spellcheck="false" autocomplete="off"
        aria-invalid={typed && typed !== app ? "true" : undefined} />
      <div class="foot">
        <button type="button" class="btn quiet" onclick={() => (step = 1)}>{t().backStep}</button>
        <button type="submit" class="btn red solid" disabled={!ready}>{t().deleteApp}</button>
      </div>
    </form>
  {/if}
</Modal>

<style>
  .sec h2.red-title { color: var(--bad-text); }
  .zone { border: 1px solid color-mix(in oklch, var(--bad) 40%, var(--line)); border-radius: 12px; background: var(--surface); }
  .row {
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-3);
    padding: var(--space-4);
  }
  .row + .row { border-top: 1px solid color-mix(in oklch, var(--bad) 20%, var(--line)); }
  .row p { margin: 2px 0 0; font-size: 13.5px; color: var(--muted); }
  .btn.red { color: var(--bad-text); border-color: color-mix(in oklch, var(--bad) 45%, var(--line)); }
  .btn.red:hover:not(:disabled) { background: color-mix(in oklch, var(--bad) 8%, var(--surface)); border-color: var(--bad); }
  .btn.red.solid { background: var(--bad); color: oklch(0.985 0.005 25); border-color: var(--bad); }
  .btn.red.solid:hover:not(:disabled) { background: color-mix(in oklch, var(--bad) 86%, var(--ink)); }
  .foot { display: flex; justify-content: flex-end; gap: var(--space-2); padding-top: var(--space-2); }
  label[for] { font-size: 14px; }
  .name {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line);
    border-radius: 8px; padding: 9px 12px; width: 100%;
  }
  .name:focus-visible { outline: 3px solid color-mix(in oklch, var(--bad) 28%, transparent); outline-offset: 0; border-color: var(--bad); }
</style>
