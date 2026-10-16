<!--
  Un valor de la configuración que se cambia en el lugar: tocarlo lo vuelve campo; Enter lo deja
  pendiente (no corre nada todavía), Esc lo cancela. Si el valor no sirve, lo dice debajo.
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  let {
    id, label, current, shown, pending = $bindable(), hint, check, disabled = false, mono = false, format = (v: string) => v,
  }: {
    id: string; label: string; current: string; shown: string; pending: string | undefined;
    hint: string; check: (v: string) => string | null; disabled?: boolean; mono?: boolean; format?: (v: string) => string;
  } = $props();
  const display = $derived(pending === undefined ? shown : format(pending));

  let editing = $state(false);
  let draft = $state("");
  let error = $state<string | null>(null);
  let input: HTMLInputElement | undefined = $state();

  function open() {
    if (disabled) return;
    draft = pending ?? current;
    error = null;
    editing = true;
    queueMicrotask(() => input?.select());
  }

  function commit() {
    const v = draft.trim();
    error = check(v);
    if (error) return;
    pending = v === current ? undefined : v;
    editing = false;
  }

  function onkey(e: KeyboardEvent) {
    if (e.key === "Enter") { e.preventDefault(); commit(); }
    if (e.key === "Escape") { e.preventDefault(); editing = false; error = null; }
  }
</script>

<dt><label for={id}>{label}</label></dt>
<dd class="field">
  {#if editing}
    <div class="edit">
      <input {id} bind:this={input} bind:value={draft} class:mono onkeydown={onkey} onblur={commit}
        aria-invalid={error ? "true" : undefined} aria-describedby={`${id}-help`} autocomplete="off" spellcheck="false" />
      <span id={`${id}-help`} class:error class="help">{error ?? hint}</span>
    </div>
  {:else}
    <button {id} type="button" class="value" class:pending={pending !== undefined} class:mono onclick={open} {disabled}
      aria-label={`${t().edit(label)}: ${display}`}>
      <span>{display}</span>
      <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" class="pencil"><path d="M10.5 2.5l3 3L6 13H3v-3z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" /></svg>
    </button>
    {#if pending !== undefined}
      <span class="was">{t().was(shown)}</span>
      <button type="button" class="undo" onclick={() => (pending = undefined)} aria-label={`${t().discard}: ${label}`}>×</button>
    {/if}
  {/if}
</dd>

<style>
  .field { display: flex; align-items: center; flex-wrap: wrap; gap: 4px var(--space-2); min-height: 32px; }
  .value {
    display: inline-flex; align-items: center; gap: var(--space-2); margin: -4px -8px; padding: 4px 8px;
    font: inherit; color: var(--ink); background: transparent; border: 1px dashed transparent; border-radius: 6px; cursor: pointer;
    transition: border-color 150ms var(--ease), background-color 150ms var(--ease);
  }
  .value:hover:not(:disabled) { border-color: var(--line); background: var(--surface); }
  .value:disabled { cursor: default; }
  .pencil { color: var(--muted); opacity: 0.45; transition: opacity 150ms var(--ease); }
  .value:hover .pencil, .value:focus-visible .pencil { opacity: 1; }
  .value.pending { color: var(--accent); font-weight: 600; border-color: color-mix(in oklch, var(--accent) 45%, transparent); background: color-mix(in oklch, var(--accent) 7%, transparent); }
  .value.pending .pencil { opacity: 1; color: var(--accent); }
  .mono { font-family: var(--mono); font-size: 0.92em; }
  .was { color: var(--muted); font-size: 13px; }
  .undo {
    width: 24px; height: 24px; display: inline-grid; place-items: center; font: 16px/1 var(--sans);
    color: var(--muted); background: transparent; border: 0; border-radius: 5px; cursor: pointer;
  }
  .undo:hover { color: var(--ink); background: var(--sunken); }
  .edit { display: grid; gap: 4px; width: 100%; max-width: 260px; }
  input {
    font: inherit; color: var(--ink); background: var(--surface); border: 1px solid var(--accent);
    border-radius: 6px; padding: 5px 9px; width: 100%;
  }
  input[aria-invalid="true"] { border-color: var(--bad); }
  input:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 30%, transparent); outline-offset: 0; }
  .help { font-size: 12.5px; color: var(--muted); }
  .help.error { color: var(--bad-text); }
</style>
