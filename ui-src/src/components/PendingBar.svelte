<!-- Los cambios sin aplicar, con el comando exacto que se va a correr. Aplicar lo lleva a la terminal. -->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  let { count, command, busy, ondiscard, onapply }: {
    count: number; command: string; busy: boolean; ondiscard: () => void; onapply: () => void;
  } = $props();
</script>

<div class="bar" role="region" aria-label={t().pending(count)}>
  <span class="count">{t().pending(count)}</span>
  <code class="cmd"><span class="prompt" aria-hidden="true">$ </span>{command}</code>
  <span class="actions">
    <button type="button" class="btn quiet" onclick={ondiscard}>{t().discard}</button>
    <button type="button" class="btn primary" onclick={onapply} disabled={busy}>{t().apply}</button>
  </span>
</div>

<style>
  .bar {
    position: fixed; z-index: 20; left: 50%; bottom: var(--space-4); transform: translateX(-50%);
    width: min(940px, calc(100vw - 2 * var(--space-4)));
    display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3) var(--space-4);
    padding: var(--space-3) var(--space-3) var(--space-3) var(--space-5);
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    box-shadow: 0 18px 40px -22px oklch(0.2 0.05 262 / 0.45);
  }
  @media (prefers-reduced-motion: no-preference) {
    .bar { animation: rise 200ms var(--ease); }
  }
  @keyframes rise { from { transform: translate(-50%, 12px); opacity: 0; } }
  .count { font-size: 13px; color: var(--muted); white-space: nowrap; }
  .cmd {
    flex: 1; min-width: 220px; font-size: 13px; padding: 6px 10px; border-radius: 6px;
    background: var(--term); color: var(--term-ink); overflow-wrap: anywhere;
  }
  .prompt { color: var(--term-muted); }
  .actions { display: flex; gap: var(--space-2); }
</style>
