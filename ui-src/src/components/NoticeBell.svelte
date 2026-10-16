<!--
  La campana: los últimos avisos (deploys, acciones, fallas), con hora y link, para no perderte
  uno si no estabas mirando. El número es lo que llegó desde la última vez que la abriste. Desde
  aquí también se piden las notificaciones del sistema (el navegador nunca pregunta solo).
-->
<script lang="ts">
  import { onMount } from "svelte";
  import { ago } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { notices } from "../lib/notices.svelte";

  // up: en el sidebar (abajo): el panel se abre hacia arriba y a la derecha.
  let { up = false }: { up?: boolean } = $props();
  let open = $state(false);
  let root: HTMLElement | undefined = $state();
  let btn: HTMLButtonElement | undefined = $state();

  function toggle() {
    open = !open;
    if (open) notices.markRead();
  }
  onMount(() => {
    const away = (e: MouseEvent) => { if (open && root && !root.contains(e.target as Node)) open = false; };
    document.addEventListener("click", away);
    return () => document.removeEventListener("click", away);
  });
  const esc = (e: KeyboardEvent) => { if (e.key === "Escape" && open) { open = false; btn?.focus(); } };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="bellw" bind:this={root} onkeydown={esc}>
  <button type="button" class="icon" bind:this={btn} aria-expanded={open} aria-controls="notice-list" onclick={toggle}
    aria-label={notices.unread ? t().noticesUnread(notices.unread) : t().notices} title={t().notices}>
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 11V7a4 4 0 018 0v4l1 1.5H3zM6.5 14a1.5 1.5 0 003 0" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" /></svg>
    {#if notices.unread}<span class="count" aria-hidden="true">{notices.unread > 9 ? "9+" : notices.unread}</span>{/if}
  </button>
  {#if open}
    <div class="panel" class:up id="notice-list">
      <div class="top">
        <strong>{t().notices}</strong>
        {#if notices.history.length}<button type="button" class="link" onclick={() => notices.clearHistory()}>{t().clearAll}</button>{/if}
      </div>
      {#if notices.permission === "default"}
        <div class="ask">
          <span>{t().notifyAskHint}</span>
          <button type="button" class="btn small" onclick={() => notices.ask()}>{t().notifyAsk}</button>
        </div>
      {/if}
      {#if notices.history.length}
        <ul>
          {#each notices.history as n, i (i)}
            <li>
              <span class={`dot ${n.tone}`}></span>
              <div class="txt">
                <span class="ttl">{n.title}</span>
                {#if n.detail}<span class="detail">{n.detail}</span>{/if}
                <span class="meta">{ago((Date.now() - n.at) / 1000)}
                  {#if n.link} · <a href={n.link.href} target={n.link.external ? "_blank" : undefined}
                      rel={n.link.external ? "noopener noreferrer" : undefined} onclick={() => (open = false)}>{n.link.text}</a>{/if}
                </span>
              </div>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">{t().noNotices}</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .bellw { position: relative; }
  .icon { position: relative; display: inline-grid; place-items: center; width: 30px; height: 30px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; }
  .icon:hover, .icon[aria-expanded="true"] { background: var(--sunken); color: var(--ink); }
  .count {
    position: absolute; top: 1px; right: 0; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 999px;
    background: var(--accent); color: var(--accent-ink); font: 600 10.5px/16px var(--sans); text-align: center;
  }
  .panel {
    position: absolute; right: 0; top: calc(100% + 8px); z-index: 30; width: min(380px, calc(100vw - 2 * var(--space-4)));
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 18px 40px -18px oklch(0.15 0.05 262 / 0.45);
    max-height: min(70vh, 520px); display: flex; flex-direction: column;
  }
  .panel.up { top: auto; bottom: calc(100% + 8px); right: auto; left: 0; }
  .top { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); }
  .link { border: 0; background: transparent; color: var(--accent); cursor: pointer; font: 13px var(--sans); padding: 4px; }
  .ask { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); font-size: 13px; color: var(--muted); }
  ul { list-style: none; margin: 0; padding: var(--space-2); overflow: auto; }
  li { display: flex; gap: var(--space-3); align-items: baseline; padding: var(--space-2); border-radius: 8px; }
  li:hover { background: var(--sunken); }
  .txt { display: grid; gap: 1px; min-width: 0; }
  .ttl { font-size: 14px; font-weight: 500; }
  .detail { font-size: 12.5px; color: var(--muted); overflow-wrap: anywhere; font-family: var(--mono); }
  .meta { font-size: 12.5px; color: var(--muted); }
  .empty { margin: 0; padding: var(--space-5) var(--space-4); color: var(--muted); font-size: 14px; text-align: center; }
</style>
