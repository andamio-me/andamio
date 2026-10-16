<!--
  Tus apps en detalle denso, debajo del plano. Toda la fila abre la app; la URL abre el sitio.
  Las apps de un mismo repo (front y back) van juntas bajo el nombre del repo, con su carpeta.
  CPU de 24 h en una gráfica mini (una sola consulta para todas: /api/sparks).
-->
<script lang="ts">
  import type { App, Sparks } from "../lib/api";
  import { mib, status } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { prefetchApp } from "../lib/cache.svelte";
  import Sparkline from "./Sparkline.svelte";

  let { apps, offline = false, avail = {}, sparks = null }: {
    apps: App[]; offline?: boolean; avail?: Record<string, { "24h": number | null; "7d": number | null }>; sparks?: Sparks | null;
  } = $props();
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v >= 99.95 ? 100 : v.toFixed(v >= 99 ? 2 : 1)} %`);
  const tone = (v: number | null | undefined) => (v === null || v === undefined ? "" : v >= 99.5 ? "ok" : v >= 95 ? "warn" : "bad");

  // Grupos: cada app sola, o las de un mismo repo juntas (las que tienen carpeta).
  const groups = $derived.by(() => {
    const out: { repo: string; items: App[] }[] = [];
    for (const a of apps) {
      const g = a.dir ? out.find((x) => x.repo === a.repo && x.items[0]?.dir) : undefined;
      if (g) g.items.push(a);
      else out.push({ repo: a.dir ? a.repo : "", items: [a] });
    }
    return out;
  });
  const host = (url: string) => url.replace("https://", "");
  const lastCpu = (name: string) => {
    const p = sparks?.sparks[name];
    return p?.length ? p[p.length - 1]![1] : null;
  };

  const go = (e: MouseEvent, name: string) => {
    if (!(e.target as HTMLElement).closest("a")) location.hash = `#/app/${name}`;
  };
</script>

{#if apps.length}
  <div class="wrap">
    <table>
      <thead>
        <tr>
          <th scope="col">{t().app}</th><th scope="col">{t().status}</th><th scope="col">{t().url}</th>
          <th scope="col">{t().access}</th><th scope="col">{t().cpu24}</th><th scope="col" class="num">{t().ram}</th>
          <th scope="col" class="num" title={t().availabilityHint}>{t().online24}</th>
          <th scope="col">{t().version}</th>
        </tr>
      </thead>
      {#each groups as g (g.repo || g.items[0]!.name)}
        <tbody class:grouped={g.items.length > 1}>
          {#if g.items.length > 1}
            <tr class="grp"><th colspan="8" scope="rowgroup"><span class="repo">{g.repo}</span><span class="muted"> · {t().appsInRepo(g.items.length)}</span></th></tr>
          {/if}
          {#each g.items as a (a.name)}
            {@const st = status(a)}
            {@const cpu = lastCpu(a.name)}
            <tr onclick={(e) => go(e, a.name)} onmouseenter={() => prefetchApp(a.name)} onfocusin={() => prefetchApp(a.name)}>
              <td>
                <a class="name" href={`#/app/${a.name}`}>{a.name}</a>
                {#if a.dir}<span class="dir">{a.dir}/</span>{/if}
              </td>
              <td><span class="state"><span class={`dot ${offline ? "" : st.tone}`}></span>{offline ? t().noData : st.text}</span></td>
              <td class="url"><a href={a.url} target="_blank" rel="noopener noreferrer" title={host(a.url)}>{host(a.url)}</a></td>
              <td><span class="tag" class:public={a.access === "public"}>{a.access === "public" ? t().public : t().vpnOnly}</span></td>
              <td class="spark">
                {#if sparks && sparks.sparks[a.name]?.length && !a.stopped}
                  <div class="sp">
                    <Sparkline points={sparks.sparks[a.name]!} start={sparks.start} end={sparks.end} step={sparks.step} height={22}
                      label={t().ovSpark(t().cpu)} />
                  </div>
                  <span class="cpu">{cpu === null ? "" : `${cpu < 1 ? cpu.toFixed(1) : Math.round(cpu)} %`}</span>
                {:else}<span class="muted">—</span>{/if}
              </td>
              <td class="num">
                {#if a.live?.mem && !offline}{t().of(mib(a.live.mem), mib(a.mem))}{:else}<span class="muted">{mib(a.mem)}</span>{/if}
              </td>
              <td class="num"><span class={`pct ${a.stopped ? "" : tone(avail[a.name]?.["24h"])}`}>{a.stopped ? "—" : pct(avail[a.name]?.["24h"])}</span></td>
              <td><code class="muted">{a.live?.version ?? "—"}</code></td>
            </tr>
          {/each}
        </tbody>
      {/each}
    </table>
  </div>
{:else}
  <p class="empty">{t().noApps} <code>{t().noAppsCmd}</code></p>
{/if}

<style>
  .pct { font-variant-numeric: tabular-nums; }
  .pct.ok { color: var(--ok-text); }
  .pct.warn { color: var(--warn-text); }
  .pct.bad { color: var(--bad-text); font-weight: 600; }
  .wrap { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; font-size: 12.5px; font-weight: 500; color: var(--muted); white-space: nowrap;
    padding: var(--space-3); border-bottom: 1px solid var(--line); background: var(--sunken);
  }
  td { padding: 11px var(--space-3); border-bottom: 1px solid var(--line); vertical-align: middle; white-space: nowrap; }
  tbody:last-child tr:last-child td { border-bottom: 0; }
  tbody tr:not(.grp) { cursor: pointer; transition: background-color 120ms var(--ease); }
  tbody tr:not(.grp):hover { background: color-mix(in oklch, var(--accent) 5%, var(--surface)); }
  .grp th {
    background: color-mix(in oklch, var(--sunken) 55%, var(--surface)); font-size: 12px; padding: 7px var(--space-4);
    border-bottom: 1px solid var(--line); text-transform: none; letter-spacing: 0;
  }
  .repo { font-family: var(--mono); color: var(--ink); font-weight: 600; }
  .grouped tr:not(.grp) td:first-child { padding-left: calc(var(--space-4) + 12px); }
  .name { font-weight: 600; color: var(--ink); }
  .dir { display: block; margin-top: 1px; font: 11.5px var(--mono); color: var(--muted); }
  .state { display: inline-flex; align-items: center; gap: 8px; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .muted { color: var(--muted); }
  .url a { display: inline-block; max-width: 210px; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
  .spark { min-width: 130px; }
  .sp { display: inline-block; width: 84px; vertical-align: middle; }
  .cpu { margin-left: 8px; font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .empty { color: var(--muted); }

  @media (max-width: 1200px) { th:nth-child(8), td:nth-child(8) { display: none; } }
  @media (max-width: 760px) {
    thead { display: none; }
    table, tbody, tr, td, .grp th { display: block; width: 100%; }
    tr { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); }
    td { border: 0; padding: 2px 0; text-align: left; white-space: normal; }
    .grouped tr:not(.grp) td:first-child { padding-left: 0; }
    .num { text-align: left; }
  }
</style>
