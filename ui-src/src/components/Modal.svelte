<!--
  Una ventana (como la de borrar una app): <dialog> nativo, atrapa el foco, Esc o un clic fuera
  la cierran. `open` se puede atar (bind:open). Con `alert`, una franja de aviso bajo el título
  (roja si `danger`).
-->
<script lang="ts">
  import type { Snippet } from "svelte";
  import { t } from "../lib/i18n.svelte";

  // dirty: ya escribiste algo. Entonces un clic afuera o Esc no la cierran (perderías lo escrito):
  // se cierra con sus botones o con la ✕.
  let { open = $bindable(false), id, danger = false, alert = "", heading, children, wide = false, dirty = false }: {
    open?: boolean; id: string; danger?: boolean; alert?: string; heading: Snippet; children: Snippet; wide?: boolean; dirty?: boolean;
  } = $props();

  let dialog: HTMLDialogElement | undefined = $state();

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });
  const backdrop = (e: MouseEvent) => { if (e.target === dialog && !dirty) open = false; };
  const cancel = (e: Event) => { if (dirty) e.preventDefault(); };
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dialog} class:wide onclick={backdrop} oncancel={cancel} onclose={() => (open = false)} aria-labelledby={`${id}-title`}>
  {#if open}
    <div class="card">
      <header>
        <h2 id={`${id}-title`}>{@render heading()}</h2>
        <button type="button" class="x" onclick={() => (open = false)} aria-label={t().close}>
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
        </button>
      </header>
      {#if alert}
        <p class="alert" class:danger role={danger ? "alert" : undefined}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M8 1.5l7 12.5H1z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" /><path d="M8 6v3.5M8 11.6v.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
          {alert}
        </p>
      {/if}
      {@render children()}
    </div>
  {/if}
</dialog>

<style>
  dialog {
    padding: 0; border: 0; background: transparent; color: var(--ink);
    width: min(540px, calc(100vw - 2 * var(--space-4))); max-width: none;
  }
  dialog.wide { width: min(640px, calc(100vw - 2 * var(--space-4))); }
  dialog::backdrop { background: oklch(0.14 0.02 262 / 0.55); }
  @supports (backdrop-filter: blur(2px)) { dialog::backdrop { backdrop-filter: blur(2px); } }
  @media (prefers-reduced-motion: no-preference) {
    dialog[open] .card { animation: pop 180ms var(--ease); }
    dialog[open]::backdrop { animation: fade 180ms var(--ease); }
  }
  @keyframes pop { from { opacity: 0; transform: translateY(8px) scale(0.98); } }
  @keyframes fade { from { opacity: 0; } }
  .card {
    background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
    box-shadow: 0 32px 64px -24px oklch(0.15 0.05 262 / 0.6);
  }
  header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding: var(--space-4) var(--space-4) var(--space-3) var(--space-5); }
  .card header h2 { margin: 0; font-size: 17px; font-weight: 650; letter-spacing: -0.01em; text-transform: none; color: var(--ink); }
  .card header h2 :global(code) { font-size: 15px; }
  .x {
    width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: 8px;
    background: transparent; color: var(--muted); cursor: pointer; flex: none;
  }
  .x:hover { background: var(--sunken); color: var(--ink); }
  .alert {
    display: flex; align-items: center; gap: var(--space-2); margin: 0; padding: var(--space-3) var(--space-5);
    background: color-mix(in oklch, var(--warn) 10%, var(--surface)); color: color-mix(in oklch, var(--warn) 80%, var(--ink));
    border-top: 1px solid color-mix(in oklch, var(--warn) 25%, var(--line)); border-bottom: 1px solid color-mix(in oklch, var(--warn) 25%, var(--line));
    font-size: 14px; font-weight: 500;
  }
  .alert.danger {
    background: color-mix(in oklch, var(--bad) 10%, var(--surface)); color: var(--bad-text);
    border-color: color-mix(in oklch, var(--bad) 25%, var(--line));
  }
  /* Lo de adentro (cuerpo y pie) usa estas clases. */
  .card :global(.m-body) { display: grid; gap: var(--space-3); padding: var(--space-4) var(--space-5); }
  .card :global(.m-foot) { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: var(--space-2); padding: 0 var(--space-5) var(--space-5); }
  .card :global(.m-note) { margin: 0; font-size: 13px; color: var(--muted); }
  .card :global(.m-cols) { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
  .card :global(.m-cols h3) { margin: 0 0 var(--space-2); font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }
  .card :global(.m-list) { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: 14px; }
  .card :global(.m-list li) { display: flex; gap: 8px; align-items: baseline; }
  .card :global(.m-list.swap li::before) { content: "↺"; color: var(--warn-text); font-size: 13px; }
  .card :global(.m-list.gone li::before) { content: "✕"; color: var(--bad-text); font-size: 12px; }
  .card :global(.m-list.kept li::before) { content: "✓"; color: var(--ok-text); font-size: 12px; }
  .card :global(.m-list.saved li::before) { content: "⤓"; color: var(--accent); font-size: 13px; }
  @media (max-width: 520px) { .card :global(.m-cols) { grid-template-columns: 1fr; } }
</style>
