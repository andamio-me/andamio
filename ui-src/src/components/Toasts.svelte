<!--
  Los avisos (notices): arriba a la derecha, bajo la barra, para no tapar la terminal. Un deploy
  que sale bien se va solo; uno que falla se queda hasta que lo cierres.
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import { notices } from "../lib/notices.svelte";
</script>

<div class="stack" aria-live="polite" aria-relevant="additions">
  {#each notices.toasts as n (n.id)}
    <div class={`toast ${n.tone}`} role="status" onmouseenter={() => notices.pause(n.id)} onmouseleave={() => notices.resume(n.id)}
      onfocusin={() => notices.pause(n.id)} onfocusout={() => notices.resume(n.id)}>
      <span class="icon" aria-hidden="true">
        {#if n.tone === "ok"}
          <svg viewBox="0 0 16 16" width="14" height="14"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {:else}
          <svg viewBox="0 0 16 16" width="14" height="14"><path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
        {/if}
      </span>
      <div class="text">
        <strong>{n.title}</strong>
        {#if n.detail}<span class="detail">{n.detail}</span>{/if}
        {#if n.link}
          <a href={n.link.href} target={n.link.external ? "_blank" : undefined} rel={n.link.external ? "noopener noreferrer" : undefined}
            onclick={() => notices.dismiss(n.id)}>{n.link.text}</a>
        {/if}
      </div>
      <button type="button" class="x" onclick={() => notices.dismiss(n.id)} aria-label={t().close}>
        <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
      </button>
    </div>
  {/each}
</div>

<style>
  .stack {
    position: fixed; z-index: 40; top: 64px; right: var(--space-4);
    display: grid; gap: var(--space-2); width: min(360px, calc(100vw - 2 * var(--space-4)));
    pointer-events: none;
  }
  .toast {
    pointer-events: auto; display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-3); align-items: start;
    padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4); border-radius: 12px;
    background: var(--surface); border: 1px solid var(--line);
    box-shadow: 0 18px 40px -18px oklch(0.15 0.05 262 / 0.45);
  }
  @media (prefers-reduced-motion: no-preference) {
    .toast { animation: slide 220ms var(--ease); }
  }
  @keyframes slide { from { opacity: 0; transform: translateY(-6px); } }
  .icon { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; margin-top: 1px; }
  .ok .icon { color: var(--ok-text); background: color-mix(in oklch, var(--ok) 14%, var(--surface)); }
  .bad .icon { color: var(--bad-text); background: color-mix(in oklch, var(--bad) 14%, var(--surface)); }
  .bad { border-color: color-mix(in oklch, var(--bad) 40%, var(--line)); }
  .text { display: grid; gap: 2px; min-width: 0; font-size: 14px; }
  .detail { color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
  .text a { font-size: 13px; font-weight: 500; justify-self: start; margin-top: 2px; }
  .x {
    width: 26px; height: 26px; display: grid; place-items: center; border: 0; border-radius: 6px;
    background: transparent; color: var(--muted); cursor: pointer;
  }
  .x:hover { background: var(--sunken); color: var(--ink); }
</style>
