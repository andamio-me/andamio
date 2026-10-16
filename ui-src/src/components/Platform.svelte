<!--
  La fila de la plataforma, al pie del plano (como en ejemplo.com): backups, alertas y seguridad.
  Lo que no está configurado se ve punteado, con el comando que lo configura. Seguridad trae
  "Revisar ahora" (el mismo andamio estado, en la terminal) y sus avisos con su arreglo.
-->
<script lang="ts">
  import type { Platform, Security } from "../lib/api";
  import { ago, until } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";

  let { platform, security, loading, oncheck }: {
    platform: Platform | null; security: Security | null; loading: boolean; oncheck: () => void;
  } = $props();

  let showIssues = $state(false);
  const now = () => Date.now() / 1000;
  const b = $derived(platform?.backups);
  const alerts = $derived(platform ? [platform.alerts.ntfy && "ntfy", platform.alerts.telegram && "Telegram"].filter(Boolean).join(" · ") : "");
  const backupTone = $derived(!b?.configured ? "" : b.running ? "warn" : b.result && b.result !== "success" ? "bad" : b.last ? "ok" : "");
  const secTone = $derived(!security ? "" : security.fail ? "bad" : security.warn ? "warn" : "ok");
</script>

<div class="platform">
  <div class="rule"><span>{t().platform}</span></div>
  <div class="cells">
    <div class="cell" class:ghost={!loading && !b?.configured}>
      <div class="ttl"><span class={`pdot ${backupTone}`}></span>{t().backups}</div>
      {#if loading}
        <div class="sub skl" aria-label={t().loading}></div>
      {:else if !b?.configured}
        <div class="sub">{t().notConfigured}</div>
        <code class="cmd">andamio backups</code>
      {:else}
        <div class="sub">
          {#if b.running}{t().backupRunning}
          {:else if !b.last}{t().backupNever}
          {:else if b.result !== "success"}{t().backupFailed(ago(now() - b.last))}
          {:else}{t().backupLast(ago(now() - b.last))}{/if}
        </div>
        {#if b.next}<div class="sub dim">{t().backupNext(until(b.next))}</div>{/if}
        <div class="btns"><a class="cbtn quiet" href="#/backups">{t().seeBackups}</a></div>
      {/if}
    </div>

    <div class="cell" class:ghost={!loading && !alerts}>
      <div class="ttl"><span class={`pdot ${alerts ? "ok" : ""}`}></span>{t().alerts}</div>
      {#if loading}
        <div class="sub skl" aria-label={t().loading}></div>
      {:else if alerts}
        <div class="sub">{t().alertsOn(alerts)}</div>
      {:else}
        <div class="sub">{t().notConfigured}</div>
        <code class="cmd">andamio alertas</code>
      {/if}
    </div>

    <div class="cell" class:ghost={!security}>
      <div class="ttl"><span class={`pdot ${secTone}`}></span>{t().security}</div>
      {#if security}
        <div class="sub">{t().checked(ago(now() - security.at))}</div>
        <div class="sub dim">{t().secCounts(security.ok, security.warn, security.fail)}</div>
      {:else}
        <div class="sub">{t().notChecked}</div>
      {/if}
      <div class="btns">
        <button type="button" class="cbtn" onclick={oncheck} disabled={job.locked}>{t().checkNow}</button>
        {#if security?.items.length}
          <button type="button" class="cbtn quiet" aria-expanded={showIssues} aria-controls="sec-issues"
            onclick={() => (showIssues = !showIssues)}>{showIssues ? t().hideIssues : t().showIssues(security.items.length)}</button>
        {/if}
      </div>
    </div>
  </div>

  {#if showIssues && security?.items.length}
    <ul id="sec-issues" class="issues">
      {#each security.items as it, i (i)}
        <li>
          <span class={`pdot ${it.status === "FAIL" ? "bad" : "warn"}`}></span>
          <div>
            <div><span class="area">{it.area}</span> {it.what}</div>
            {#if it.fix}<div class="fix">→ {it.fix}</div>{/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .platform { grid-column: 1 / -1; margin-top: var(--space-2); }
  .rule { display: flex; align-items: center; gap: var(--space-3); color: var(--chalk-dim); font-size: 13px; margin-bottom: var(--space-3); }
  .rule::after { content: ""; flex: 1; border-top: 1px dashed color-mix(in oklch, var(--chalk-dim) 70%, transparent); }
  .cells { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-4); }
  .cell {
    background: var(--print-deep); border: 1.25px solid var(--chalk); border-radius: 6px;
    padding: var(--space-3) var(--space-4); display: grid; gap: 3px; align-content: start;
  }
  .cell.ghost { background: transparent; border-style: dashed; border-color: var(--chalk-dim); }
  .ttl { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 15px; color: var(--chalk); }
  .sub { font-size: 13px; color: var(--chalk); }
  .sub.dim, .ghost .sub { color: var(--chalk-dim); }
  .cmd { font-size: 12px; color: var(--chalk); margin-top: 2px; }
  .pdot { width: 8px; height: 8px; border-radius: 50%; background: var(--chalk-dim); flex: none; }
  .pdot.ok { background: oklch(0.84 0.15 155); }
  .pdot.warn { background: oklch(0.87 0.13 85); }
  .pdot.bad { background: oklch(0.76 0.17 25); }
  .btns { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-2); }
  .cbtn {
    font: 500 12.5px/1 var(--sans); color: var(--print-deep); background: var(--chalk); border: 1px solid var(--chalk);
    border-radius: 6px; padding: 7px 10px; cursor: pointer;
  }
  .cbtn.quiet { color: var(--chalk); background: transparent; border-color: color-mix(in oklch, var(--chalk) 50%, transparent); }
  .cbtn:hover:not(:disabled) { filter: brightness(1.06); }
  a.cbtn { text-decoration: none; display: inline-block; }
  .cbtn:disabled { opacity: 0.5; cursor: not-allowed; }
  .issues { list-style: none; margin: var(--space-4) 0 0; padding: 0; display: grid; gap: var(--space-2); }
  .issues li {
    display: flex; gap: var(--space-3); align-items: baseline; padding: var(--space-3) var(--space-4);
    border: 1px solid color-mix(in oklch, var(--chalk-dim) 60%, transparent); border-radius: 6px; font-size: 13.5px; color: var(--chalk);
  }
  .area { color: var(--chalk-dim); margin-right: 6px; }
  .fix { color: var(--chalk-dim); font-size: 12.5px; margin-top: 2px; font-family: var(--mono); overflow-wrap: anywhere; }
  @media (max-width: 760px) { .cells { grid-template-columns: 1fr; } }
  .skl { height: 12px; width: 60%; margin-top: 6px; border-radius: 4px; background: color-mix(in oklch, var(--chalk) 25%, transparent); }
</style>
