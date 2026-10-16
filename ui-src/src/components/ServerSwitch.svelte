<!--
  El servidor de este panel, arriba. Con más de una copia de andamio (andamio use), un menú para
  abrir el panel de otra: su propio proceso y su clave, en otra pestaña. Este sigue abierto.
-->
<script lang="ts">
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";

  let { domain, server }: { domain: string; server: string } = $props();

  let copies = $state<api.Copy[]>([]);
  let open = $state(false);
  let busy = $state("");
  let error = $state("");
  let root: HTMLElement | undefined = $state();
  let toggle: HTMLButtonElement | undefined = $state();
  const esc = (e: KeyboardEvent) => {
    if (e.key === "Escape" && open) {
      open = false;
      toggle?.focus();
    }
  };

  onMount(() => {
    api.copies().then((r) => (copies = r.copies)).catch(() => {});
    const away = (e: MouseEvent) => { if (open && root && !root.contains(e.target as Node)) open = false; };
    document.addEventListener("click", away);
    return () => document.removeEventListener("click", away);
  });

  async function go(c: api.Copy) {
    error = "";
    busy = c.path;
    const w = window.open("", "_blank");
    try {
      const { url } = await api.switchTo(c.path);
      if (w) { w.opener = null; w.location.href = url; } else location.href = url;
      open = false;
    } catch (e) {
      w?.close();
      error = String((e as Error).message);
    } finally {
      busy = "";
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="sw" bind:this={root} onkeydown={esc}>
  {#if copies.length > 1}
    <button type="button" class="cur" bind:this={toggle} aria-expanded={open} aria-controls="server-list"
      aria-label={t().serversOf(domain)} onclick={() => (open = !open)}>
      <span>{domain}</span><span class="sep" aria-hidden="true">·</span><span>{server}</span>
      <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    {#if open}
      <div class="menu" id="server-list">
        <div class="ttl" aria-hidden="true">{t().servers}</div>
        {#each copies as c (c.path)}
          <button type="button" class:on={c.current} aria-current={c.current ? "true" : undefined} disabled={c.current || busy !== ""} onclick={() => go(c)}>
            <span class="ck" aria-hidden="true">{c.current ? "✓" : ""}</span>
            <span class="dom">{c.domain}</span>
            <span class="muted">{c.current ? t().thisPanel : busy === c.path ? t().opening : t().openInTab}</span>
          </button>
        {/each}
        {#if error}<p class="err">{error}</p>{/if}
      </div>
    {/if}
  {:else}
    <span class="where"><span>{domain}</span><span class="sep" aria-hidden="true">·</span><span>{server}</span></span>
  {/if}
</div>

<style>
  .sw { position: relative; }
  .where, .cur { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 13.5px; }
  .cur { background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 4px 8px; margin-left: -8px; cursor: pointer; font-family: var(--sans); }
  .cur:hover, .cur[aria-expanded="true"] { border-color: var(--line); color: var(--ink); }
  .sep { opacity: 0.6; }
  .menu {
    position: absolute; top: calc(100% + 6px); left: -8px; z-index: 30; min-width: 280px; padding: var(--space-2);
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 18px 40px -18px oklch(0.15 0.05 262 / 0.45);
  }
  .ttl { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); padding: 4px var(--space-2) 6px; }
  .menu button {
    display: flex; align-items: center; gap: var(--space-2); width: 100%; text-align: left; padding: 8px var(--space-2);
    border: 0; border-radius: 8px; background: transparent; color: var(--ink); font: 14px var(--sans); cursor: pointer;
  }
  .menu button:hover:not(:disabled) { background: var(--sunken); }
  .menu button:disabled { cursor: default; }
  .ck { width: 14px; color: var(--accent); }
  .dom { font-weight: 500; flex: 1; }
  .muted { color: var(--muted); font-size: 12.5px; }
  .err { margin: 6px var(--space-2) 2px; color: var(--bad-text); font-size: 13px; }
</style>
