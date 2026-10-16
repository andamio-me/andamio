<!--
  Un menú "⋯" para acciones secundarias (Reiniciar, Apagar…): abre con clic o con las flechas, se
  cierra con Esc, al elegir o al hacer clic afuera. Cada ítem: etiqueta, pista y si es peligroso.
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  type Item = { label: string; hint?: string; danger?: boolean; disabled?: boolean; run: () => void };
  let { items, label = "" }: { items: Item[]; label?: string } = $props();

  let open = $state(false);
  let root: HTMLDivElement | undefined = $state();
  let btn: HTMLButtonElement | undefined = $state();

  function focusItem(i: number) {
    const els = root?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)');
    if (els?.length) els[(i + els.length) % els.length]!.focus();
  }
  function toggle() {
    open = !open;
    if (open) queueMicrotask(() => focusItem(0));
  }
  function onKey(e: KeyboardEvent) {
    if (!open) {
      if (e.key === "ArrowDown") { e.preventDefault(); open = true; queueMicrotask(() => focusItem(0)); }
      return;
    }
    const els = [...(root?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)') ?? [])];
    const i = els.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "Escape") { e.preventDefault(); open = false; btn?.focus(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); focusItem(i + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); focusItem(i - 1); }
  }
  $effect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!root?.contains(e.target as Node)) open = false; };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  });
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="more" bind:this={root} onkeydown={onKey}>
  <button type="button" class="btn icon" bind:this={btn} aria-haspopup="menu" aria-expanded={open} aria-label={label || t().moreActions}
    title={label || t().moreActions} onclick={toggle}>
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><circle cx="3.5" cy="8" r="1.3" /><circle cx="8" cy="8" r="1.3" /><circle cx="12.5" cy="8" r="1.3" /></svg>
  </button>
  {#if open}
    <div class="menu" role="menu">
      {#each items as it (it.label)}
        <button type="button" role="menuitem" class:danger={it.danger} disabled={it.disabled}
          onclick={() => { open = false; it.run(); }}>
          <span class="ml">{it.label}</span>
          {#if it.hint}<span class="mh">{it.hint}</span>{/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .more { position: relative; }
  .icon { width: 38px; padding: 0; display: inline-grid; place-items: center; }
  .icon svg { fill: currentColor; }
  .menu {
    position: absolute; right: 0; top: calc(100% + 6px); z-index: 30; min-width: 240px; padding: 4px;
    background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
    box-shadow: 0 18px 40px -22px oklch(0.1 0.02 262 / 0.55);
  }
  .menu button {
    display: grid; gap: 2px; width: 100%; text-align: left; border: 0; background: transparent; padding: 8px 12px;
    border-radius: 7px; cursor: pointer; color: var(--ink); font: 14px var(--sans);
  }
  .menu button:hover:not(:disabled), .menu button:focus-visible { background: var(--sunken); outline: none; }
  .menu button:disabled { opacity: 0.5; cursor: not-allowed; }
  .menu .danger .ml { color: var(--bad-text); }
  .mh { font-size: 12.5px; color: var(--muted); }
</style>
