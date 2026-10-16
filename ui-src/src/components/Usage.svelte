<!--
  El uso en el tiempo (de Prometheus del servidor): CPU, RAM y red, de una app o del servidor
  entero. Un solo selector de rango arriba manda sobre las tres. Mientras recarga, las gráficas
  se quedan con lo de antes, más tenues (sin saltos).
-->
<script lang="ts">
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { bytes } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import Chart from "./Chart.svelte";

  let { app = "", memLimit = null, cpuLimit = null, id, heading, desc, height = 140 }: {
    app?: string; memLimit?: number | null; cpuLimit?: number | null; id: string; heading: string; desc: string; height?: number;
  } = $props();

  const RANGES: api.Range[] = ["1h", "6h", "24h", "7d"];
  let range = $state<api.Range>("24h");
  let data = $state<api.Metrics | null>(null);
  let loading = $state(false);
  let error = $state("");

  async function load(r: api.Range, a: string) {
    loading = true;
    try {
      const d = await api.metrics(r, a);
      if (r !== range) return;   // cambiaste de rango mientras llegaba: vale el nuevo
      data = d;
      error = d.error || "";
    } catch (e) {
      error = String((e as Error).message);
    } finally {
      loading = false;
    }
  }
  $effect(() => {
    const r = range, a = app;
    void load(r, a);
  });
  onMount(() => {
    const every = setInterval(() => { if (!document.hidden) void load(range, app); }, 60_000);
    return () => clearInterval(every);
  });

  const pct = (v: number) => `${v < 10 ? v.toFixed(1) : Math.round(v)} %`;
  const pctAxis = (v: number) => `${v >= 10 || Number.isInteger(v) ? Math.round(v) : v.toFixed(1)} %`;
  const rate = (v: number) => `${bytes(v)}/s`;
  const last = (pts: api.Point[] | undefined) => (pts?.length ? pts[pts.length - 1]![1] : null);

  const s = $derived(data?.series ?? {});
  const frame = $derived(data ? { start: data.start, end: data.end, step: data.step } : { start: 0, end: 1, step: 60 });
</script>

<section aria-labelledby={id} class="usage">
  <div class="shead">
    <div><h2 {id}>{heading}</h2><p class="desc">{desc}</p></div>
    <div class="seg" role="radiogroup" aria-label={t().range}>
      {#each RANGES as r (r)}
        <button type="button" role="radio" aria-checked={range === r} class:on={range === r} onclick={() => (range = r)}>{t().rangeLabel(r)}</button>
      {/each}
    </div>
  </div>
  {#if error && !data?.series?.cpu}
    <p class="box err">{error}</p>
  {:else}
    <div class="grid" class:loading={loading && data}>
      <div class="box cell">
        <div class="head"><h3>{t().cpu}</h3>{#if last(s.cpu) !== null}<span class="now">{t().nowValue(pct(last(s.cpu)!))}</span>{/if}</div>
        {#if data}
          <Chart title={t().cpu} {...frame} {height} format={pct} axis={pctAxis}
            limit={cpuLimit ? { value: cpuLimit, label: t().limitOf(pctAxis(cpuLimit)) } : null}
            series={[{ key: "cpu", label: t().cpu, tone: 1, points: s.cpu ?? [] }]} />
        {:else}<div class="ph" style:height={`${height}px`} role="status" aria-label={t().loading}></div>{/if}
      </div>
      <div class="box cell">
        <div class="head"><h3>{t().ram}</h3>{#if last(s.mem) !== null}<span class="now">{t().nowValue(bytes(last(s.mem)!))}</span>{/if}</div>
        {#if data}
          <Chart title={t().ram} {...frame} {height} format={bytes} binary
            limit={memLimit ? { value: memLimit, label: t().limitOf(bytes(memLimit)) } : null}
            series={[{ key: "mem", label: t().ram, tone: 1, points: s.mem ?? [] }]} />
        {:else}<div class="ph" style:height={`${height}px`} role="status" aria-label={t().loading}></div>{/if}
      </div>
      <div class="box cell">
        <div class="head">
          <h3>{t().net}</h3>
          <span class="legend"><span class="k c1"></span>{t().netIn} <span class="k c2"></span>{t().netOut}</span>
        </div>
        {#if data}
          <Chart title={t().net} {...frame} {height} format={rate} binary
            series={[{ key: "rx", label: t().netIn, tone: 1, points: s.rx ?? [] }, { key: "tx", label: t().netOut, tone: 2, points: s.tx ?? [] }]} />
        {:else}<div class="ph" style:height={`${height}px`} role="status" aria-label={t().loading}></div>{/if}
      </div>
    </div>
  {/if}
</section>

<style>
  .usage { margin-top: var(--space-7); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-4); transition: opacity 200ms var(--ease); }
  .grid.loading { opacity: 0.55; }
  .cell { padding: var(--space-3) var(--space-4) var(--space-2); }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); }
  .cell h3 { margin: 0; font-size: 14px; font-weight: 600; }
  .now { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .legend { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted); }
  .k { width: 12px; height: 2px; border-radius: 1px; display: inline-block; }
  .k.c1 { background: var(--chart-1); }
  .k.c2 { background: var(--chart-2); margin-left: 6px; }
  .ph { border-radius: 8px; background: linear-gradient(90deg, var(--sunken), color-mix(in oklch, var(--sunken) 60%, var(--line)), var(--sunken)); background-size: 200% 100%; }
  @media (prefers-reduced-motion: no-preference) { .ph { animation: shimmer 1.4s ease-in-out infinite; } }
  @keyframes shimmer { from { background-position: 100% 0; } to { background-position: -100% 0; } }
  .err { margin: 0; padding: var(--space-3) var(--space-4); color: var(--muted); font-size: 14px; }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); }
  .seg button {
    font: 500 13px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px;
    padding: 7px 10px; cursor: pointer; transition: background-color 150ms var(--ease), color 150ms var(--ease);
  }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }
</style>
