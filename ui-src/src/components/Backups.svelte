<!--
  Respaldos: cómo va el diario (el último, el próximo), "Respaldar ahora" y la lista de los que
  hay, cada uno con "Restaurar una app…". La lista la deja el servidor al terminar cada
  respaldo (sin secretos, se lee sin sudo); la primera vez se carga con un botón.
-->
<script lang="ts">
  import PageHead from "./PageHead.svelte";
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { ago, bytes, until } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import Skeleton from "./Skeleton.svelte";
  import { job } from "../lib/job.svelte";
  import RestoreDialog from "./RestoreDialog.svelte";

  let { preset = "" }: { preset?: string } = $props();

  let data = $state<api.Backups | null>(null);
  let apps = $state<api.App[]>([]);
  let error = $state("");
  let restoring = $state<api.Snapshot | null>(null);
  let allArchive = $state(false);
  const archive = $derived(data?.archive ?? []);
  const archiveShown = $derived(allArchive ? archive : archive.slice(0, 8));
  const daysLeft = (time: number) => Math.max(0, Math.ceil((data?.archive_days ?? 90) - (now() - time) / 86400));
  let dialogOpen = $state(false);

  async function load() {
    try {
      const [b, a] = await Promise.all([api.backups(), api.apps().catch(() => null)]);
      data = b;
      if (a) apps = a.apps;
      error = b.error;
    } catch (e) {
      error = String((e as Error).message);
    }
  }
  onMount(() => void load());

  const now = () => Date.now() / 1000;
  const fmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  const dur = (s: number | null) => (s === null ? "—" : s >= 60 ? `${Math.floor(s / 60)} min ${s % 60} s` : `${s} s`);
  const tone = $derived(!data?.configured ? "" : data.running ? "warn" : data.result && data.result !== "success" ? "bad" : data.last ? "ok" : "");

  const backupNow = () => job.arm({ action: "backup-now" }, () => void load());
  const loadList = () => job.arm({ action: "backup-list" }, () => void load());
  function openRestore(s: api.Snapshot) {
    restoring = s;
    dialogOpen = true;
  }
</script>


<PageHead title={t().backups} desc={t().backupsDesc}>
  {#snippet actions()}
    {#if data?.enabled}
      <button type="button" class="btn primary" onclick={backupNow} disabled={job.locked || data.running}>{t().backupNow}</button>
    {/if}
  {/snippet}
</PageHead>

{#if error && !data?.configured}
  <p class="banner" role="alert">{error}</p>
{/if}

{#if !data}
  <div class="pad"><Skeleton rows={4} /></div>
{:else if !data.enabled}
  <div class="box empty">
    <p>{t().backupsOff}</p>
    <code>andamio backups</code>
  </div>
{:else}
  <dl class="status">
    <div>
      <dt>{t().lastBackup}</dt>
      <dd>
        <span class={`dot ${tone}`}></span>
        {#if data.running}{t().backupRunning}
        {:else if !data.last}{t().backupNever}
        {:else if data.result !== "success"}{t().backupFailed(ago(now() - data.last))}
        {:else}{t().backupLast(ago(now() - data.last))}{/if}
      </dd>
    </div>
    {#if data.next}<div><dt>{t().nextBackup}</dt><dd>{until(data.next)}</dd></div>{/if}
    <div><dt>{t().keeps}</dt><dd>{t().keepsWhat}</dd></div>
  </dl>

  <section aria-labelledby="snaps">
    <div class="shead">
      <div><h2 id="snaps">{t().snapshots}</h2><p class="desc">{t().snapshotsDesc}</p></div>
      {#if data.listed}<button type="button" class="btn small" onclick={loadList} disabled={job.locked}>{t().reloadList}</button>{/if}
    </div>
    {#if !data.listed}
      <div class="box empty">
        <p>{t().listMissing}</p>
        <button type="button" class="btn small" onclick={loadList} disabled={job.locked}>{t().loadList}</button>
      </div>
    {:else if !data.snapshots?.length}
      <p class="box empty">{t().noSnapshots}</p>
    {:else}
      <div class="box table-wrap">
        <table>
          <thead>
            <tr><th scope="col">{t().when}</th><th scope="col" class="num">{t().took}</th><th scope="col" class="num">{t().size}</th>
              <th scope="col" class="num">{t().added}</th><th scope="col">{t().id}</th><th scope="col"><span class="sr-only">{t().actions}</span></th></tr>
          </thead>
          <tbody>
            {#each data.snapshots as s, i (s.id)}
              <tr>
                <td>
                  <span class="date">{s.time ? fmt.format(s.time * 1000) : "?"}</span>
                  <span class="muted ago">{s.time ? ago(now() - s.time) : ""}</span>
                  {#if i === 0}<span class="tag">{t().newest}</span>{/if}
                </td>
                <td class="num">{dur(s.secs)}</td>
                <td class="num">{s.size ? bytes(s.size) : "—"}</td>
                <td class="num muted">{s.added !== null ? `+${bytes(s.added)}` : "—"}</td>
                <td><code>{s.short}</code></td>
                <td class="act"><button type="button" class="btn small" onclick={() => openRestore(s)} disabled={job.locked}>{t().restoreApp}</button></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="foot">{t().listedAt(data.listed_at ? ago(now() - data.listed_at) : "?")}</p>
    {/if}
  </section>

  {#if data.listed}
    <section aria-labelledby="arch">
      <div class="shead">
        <div><h2 id="arch">{t().archiveTitle}</h2><p class="desc">{t().archiveDesc(data.archive_days ?? 90)}</p></div>
        {#if archive.length}<span class="muted total">{t().archiveTotal(archive.length, bytes(data.archive_total ?? 0))}</span>{/if}
      </div>
      {#if !archive.length}
        <p class="box empty">{t().archiveEmpty}</p>
      {:else}
        <div class="box table-wrap">
          <table>
            <thead>
              <tr><th scope="col">{t().archiveFile}</th><th scope="col">{t().when}</th><th scope="col" class="num">{t().size}</th>
                <th scope="col" class="num">{t().archiveGone}</th></tr>
            </thead>
            <tbody>
              {#each archiveShown as f (f.name)}
                <tr>
                  <td><code>{f.name}</code></td>
                  <td><span class="date">{fmt.format(f.time * 1000)}</span></td>
                  <td class="num">{bytes(f.size)}</td>
                  <td class="num muted">{t().archiveIn(daysLeft(f.time))}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if archive.length > 8}
          <button type="button" class="btn small quiet more" onclick={() => (allArchive = !allArchive)}>
            {allArchive ? t().showLess : t().showAll(archive.length)}
          </button>
        {/if}
      {/if}
    </section>
  {/if}
{/if}

<RestoreDialog bind:open={dialogOpen} snapshot={restoring} {apps} {preset} ondone={() => void load()} />

<style>
  .muted { color: var(--muted); }
  .pad { padding: var(--space-6) 0; }
  .banner {
    margin: var(--space-5) 0 0; padding: var(--space-3) var(--space-4); border-radius: 8px; font-size: 14px;
    background: color-mix(in oklch, var(--bad) 10%, var(--surface)); border: 1px solid color-mix(in oklch, var(--bad) 35%, var(--line));
  }
  .status { display: flex; flex-wrap: wrap; gap: var(--space-4) var(--space-7); margin: var(--space-5) 0 0; }
  .status dt { font-size: 13px; color: var(--muted); }
  .status dd { margin: 2px 0 0; display: flex; align-items: center; gap: 8px; }
  section { margin-top: var(--space-7); }
  .empty { padding: var(--space-4); display: grid; gap: var(--space-3); justify-items: start; margin: var(--space-5) 0 0; color: var(--muted); }
  section .empty { margin: 0; }
  .empty p { margin: 0; max-width: 62ch; }
  .table-wrap { overflow-x: auto; padding: 0; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; font-weight: 600; font-size: 12.5px; color: var(--muted); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); white-space: nowrap; }
  td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); white-space: nowrap; }
  tr:last-child td { border-bottom: 0; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .date { font-weight: 500; }
  .ago { margin-left: var(--space-2); font-size: 13px; }
  .tag { margin-left: var(--space-2); font-size: 12px; padding: 2px 8px; border-radius: 999px; background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .act { text-align: right; width: 1%; }
  .foot { margin: var(--space-2) 0 0; font-size: 13px; color: var(--muted); }
  .total { font-size: 13.5px; }
  .more { margin-top: var(--space-2); }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
