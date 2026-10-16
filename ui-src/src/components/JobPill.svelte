<!--
  La terminal minimizada: una pastilla abajo a la derecha con lo que corre y cuánto lleva. Un
  clic la vuelve a abrir. Si pide tu contraseña, se abre sola (job.svelte). Al terminar queda en
  verde o rojo hasta que la abras o la cierres (y llega el aviso, ver notices).
-->
<script lang="ts">
  import { onMount } from "svelte";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";

  let now = $state(Date.now());
  onMount(() => {
    const every = setInterval(() => (now = Date.now()), 1000);
    return () => clearInterval(every);
  });

  const elapsed = $derived.by(() => {
    if (!job.startedAt) return "";
    const s = Math.max(0, Math.floor((now - job.startedAt) / 1000));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  });
  const label = $derived(job.command.replace(/^andamio /, ""));
  const tone = $derived(job.phase !== "done" ? "run" : job.rc === 0 ? "ok" : "bad");
  const statusText = $derived(job.phase !== "done" ? t().workingNow : job.rc === 0 ? t().done : job.rc === 130 ? t().cancelled : t().failed(job.rc ?? 1));
</script>

{#if job.open && job.minimized}
  <div class={`pill ${tone}`} role="status" aria-live="polite">
    <button type="button" class="main" onclick={() => job.expand()} aria-label={`${statusText}: ${job.command}. ${t().expand}`}>
      <span class="ic" aria-hidden="true">
        {#if tone === "run"}<span class="spin"></span>
        {:else if tone === "ok"}<svg viewBox="0 0 16 16" width="13" height="13"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {:else}<svg viewBox="0 0 16 16" width="13" height="13"><path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>{/if}
      </span>
      <span class="txt">
        <span class="st">{statusText}{#if tone === "run" && elapsed} · {elapsed}{/if}</span>
        <code class="cmd">{label}</code>
      </span>
      <span class="open" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="13" height="13"><path d="M4 10l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </span>
    </button>
    {#if job.phase === "done"}
      <button type="button" class="x" onclick={() => job.close()} aria-label={t().close}>
        <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
      </button>
    {/if}
    {#key job.nudges}{#if job.nudges && tone === "run"}<span class="nudge">{t().nudge}</span>{/if}{/key}
  </div>
{/if}

<style>
  .pill {
    position: fixed; z-index: 35; right: var(--space-4); bottom: var(--space-4); max-width: min(420px, calc(100vw - 2 * var(--space-4)));
    display: flex; align-items: center; gap: 2px; padding: 4px; border-radius: 999px;
    background: var(--term); color: var(--term-ink); box-shadow: 0 18px 40px -16px oklch(0.15 0.05 262 / 0.6), 0 0 0 1px oklch(1 0 0 / 0.08);
  }
  @media (prefers-reduced-motion: no-preference) { .pill { animation: in 200ms var(--ease); } }
  @keyframes in { from { opacity: 0; transform: translateY(8px); } }
  .pill.ok { box-shadow: 0 18px 40px -16px oklch(0.15 0.05 262 / 0.6), 0 0 0 1.5px var(--term-ok); }
  .pill.bad { box-shadow: 0 18px 40px -16px oklch(0.15 0.05 262 / 0.6), 0 0 0 1.5px var(--term-bad); }
  .main {
    display: flex; align-items: center; gap: var(--space-3); min-width: 0; border: 0; background: transparent; color: inherit;
    padding: 6px 10px 6px 8px; border-radius: 999px; cursor: pointer; text-align: left; font: inherit;
  }
  .main:hover { background: oklch(1 0 0 / 0.06); }
  .main:focus-visible { outline: 2px solid var(--chalk); outline-offset: 1px; }
  .ic { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; flex: none; background: oklch(1 0 0 / 0.08); }
  .ok .ic { color: var(--term-ok); }
  .bad .ic { color: var(--term-bad); }
  .spin { width: 12px; height: 12px; border-radius: 50%; border: 2px solid oklch(1 0 0 / 0.2); border-top-color: var(--term-ink); }
  @media (prefers-reduced-motion: no-preference) { .spin { animation: spin 0.9s linear infinite; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  .txt { display: grid; min-width: 0; line-height: 1.3; }
  .st { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .ok .st { color: var(--term-ok); }
  .bad .st { color: var(--term-bad); }
  .cmd { font-size: 12px; color: var(--term-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .open { color: var(--term-muted); display: grid; place-items: center; }
  .x { width: 30px; height: 30px; display: grid; place-items: center; border: 0; border-radius: 50%; background: transparent; color: var(--term-muted); cursor: pointer; flex: none; }
  .x:hover { background: oklch(1 0 0 / 0.08); color: var(--term-ink); }
  .nudge {
    position: absolute; right: 0; bottom: calc(100% + 8px); white-space: nowrap; font-size: 12.5px; padding: 6px 10px; border-radius: 8px;
    background: var(--term); color: var(--term-warn); box-shadow: 0 0 0 1px oklch(1 0 0 / 0.08); animation: nudge 3.5s var(--ease) forwards;
  }
  @keyframes nudge { 0%, 80% { opacity: 1; } 100% { opacity: 0; } }
</style>
