<!--
  ntfy desde el panel (lo mismo que `andamio alertas --ntfy`): un tema nuevo en ntfy.sh (gratis,
  sin cuenta, con un nombre largo al azar que nadie adivina) o tu propio servidor ntfy. Se guarda
  en tu configuración, se aplica en el servidor (pide sudo) y después te suscribes y mandas una de
  prueba desde Ajustes.
-->
<script lang="ts">
  import { untrack } from "svelte";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { open = $bindable(false), current = "", ondone }: { open?: boolean; current?: string; ondone: () => void } = $props();

  let mode = $state<"new" | "own">("new");
  let url = $state("");
  $effect(() => {
    if (!open) return;
    untrack(() => { mode = "new"; url = ""; });
  });
  const urlOk = $derived(/^https:\/\/[A-Za-z0-9.-]+(:\d+)?\/[A-Za-z0-9_-]{1,64}$/.test(url.trim()));
  const ready = $derived(mode === "new" || urlOk);

  function activate() {
    if (!ready) return;
    job.arm({ action: "ntfy", ntfy: mode === "new" ? "nuevo" : url.trim() }, () => ondone());
    void job.run();
    open = false;
  }
</script>

<Modal bind:open id="ntfy" dirty={mode === "own" && url.trim().length > 0}>
  {#snippet heading()}{current ? t().ntfyChange : t().ntfySetup}{/snippet}
  <div class="m-body">
    <p class="m-note">{t().ntfyWhat}</p>
    <fieldset>
      <legend class="sr-only">{t().ntfyWhich}</legend>
      <label class="opt" class:on={mode === "new"}>
        <input type="radio" name="ntfy-mode" value="new" bind:group={mode} />
        <span><strong>{t().ntfyNew}</strong><span class="sub">{t().ntfyNewSub}</span></span>
      </label>
      <label class="opt" class:on={mode === "own"}>
        <input type="radio" name="ntfy-mode" value="own" bind:group={mode} />
        <span><strong>{t().ntfyOwn}</strong><span class="sub">{t().ntfyOwnSub}</span></span>
      </label>
    </fieldset>
    {#if mode === "own"}
      <label for="ntfy-url">{t().ntfyUrl}</label>
      <input id="ntfy-url" bind:value={url} class="mono field" placeholder={t().ntfyPlaceholder} spellcheck="false"
        autocomplete="off" aria-invalid={url && !urlOk ? "true" : undefined} />
      {#if url && !urlOk}<p class="err">{t().ntfyBadUrl}</p>{/if}
    {/if}
    <ul class="m-list kept">
      <li>{t().ntfyWill1}</li><li>{t().ntfyWill2}</li>
    </ul>
  </div>
  <div class="m-foot">
    <button type="button" class="btn quiet" onclick={() => (open = false)}>{t().cancel}</button>
    <button type="button" class="btn primary" onclick={activate} disabled={!ready || job.locked}>{t().ntfyActivate}</button>
  </div>
</Modal>

<style>
  fieldset { border: 0; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
  .opt { display: flex; align-items: flex-start; gap: var(--space-3); padding: var(--space-3); border: 1px solid var(--line); border-radius: 10px; cursor: pointer; }
  .opt.on { border-color: var(--accent); background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .opt input { accent-color: var(--accent); margin: 3px 0 0; }
  .opt span { display: grid; gap: 2px; font-size: 14px; }
  .sub { color: var(--muted); font-size: 13px; }
  label[for] { font-size: 14px; font-weight: 500; }
  .field {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line);
    border-radius: 8px; padding: 9px 12px; width: 100%;
  }
  .field:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 22%, transparent); outline-offset: 0; border-color: var(--accent); }
  .err { margin: 0; color: var(--bad-text); font-size: 13px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
