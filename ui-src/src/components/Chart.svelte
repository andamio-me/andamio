<!--
  Una gráfica de línea en el tiempo (SVG, sin librerías): una o dos series, eje Y desde 0, una
  línea de límite opcional (p. ej. la RAM que tiene la app) y, al pasar el mouse o con las
  flechas del teclado, una cruz con los valores de ese momento. Los huecos (sin datos: la app
  apagada) quedan como huecos, no como una línea recta inventada.
-->
<script lang="ts">
  import type { Point } from "../lib/api";
  import { t } from "../lib/i18n.svelte";

  type Series = { key: string; label: string; tone: 1 | 2; points: Point[] };
  let { series, start, end, step, format, axis = format, limit = null, height = 150, title, empty = "", binary = false }: {
    series: Series[]; start: number; end: number; step: number; format: (v: number) => string; axis?: (v: number) => string;
    limit?: { value: number; label: string } | null; height?: number; title: string; empty?: string;
    binary?: boolean;   // bytes: los ticks redondos en KiB/MiB/GiB, no en potencias de 10
  } = $props();

  let width = $state(320);
  let hover = $state<number | null>(null);   // índice en `times`
  const pad = { l: 52, r: 12, t: 12, b: 24 };

  const times = $derived.by(() => {
    const longest = series.reduce((a, s) => (s.points.length > a.length ? s.points : a), [] as Point[]);
    return longest.map((p) => p[0]);
  });
  const byTime = $derived(series.map((s) => new Map(s.points.map(([x, y]) => [x, y]))));
  const hasData = $derived(series.some((s) => s.points.length));

  function nice(v: number): number {
    if (!(v > 0)) return 1;
    if (binary && v >= 1024) {
      const unit = 1024 ** Math.floor(Math.log(v) / Math.log(1024));
      return nice10(v / unit) * unit;
    }
    return nice10(v);
  }
  function nice10(v: number): number {
    const e = 10 ** Math.floor(Math.log10(v));
    for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * e >= v) return m * e;
    return 10 * e;
  }
  const dataMax = $derived(Math.max(0, ...series.flatMap((s) => s.points.map((p) => p[1]))));
  // El límite entra en la escala solo si el uso se le acerca: si no, aplastaría la línea contra el piso
  // (una app que usa 0.2 % de 50 %). Entonces queda como texto arriba, con una flecha.
  const drawLimit = $derived(limit !== null && dataMax >= limit.value * 0.4);
  const yMax = $derived(nice(Math.max(drawLimit ? limit!.value : 0, dataMax) * 1.08));
  const x = (tm: number) => pad.l + ((tm - start) / Math.max(1, end - start)) * Math.max(10, width - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - v / yMax) * (height - pad.t - pad.b);

  /** Tramos continuos: se cortan donde faltan datos (más de 1.5 pasos entre puntos). */
  function runs(points: Point[]): Point[][] {
    const out: Point[][] = [];
    let cur: Point[] = [];
    for (const p of points) {
      if (cur.length && p[0] - cur[cur.length - 1]![0] > step * 1.5) {
        out.push(cur);
        cur = [];
      }
      cur.push(p);
    }
    if (cur.length) out.push(cur);
    return out;
  }
  const line = (pts: Point[]) => pts.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  const area = (pts: Point[]) =>
    `${line(pts)}L${x(pts[pts.length - 1]![0]).toFixed(1)},${y(0)}L${x(pts[0]![0]).toFixed(1)},${y(0)}Z`;

  const span = $derived(end - start);
  const fmtTime = $derived(new Intl.DateTimeFormat(undefined, span > 86400 * 1.5
    ? { weekday: "short", day: "numeric" } : { hour: "2-digit", minute: "2-digit" }));
  const fmtFull = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const xTicks = $derived([0, 1, 2, 3].map((i) => start + (span * (i + 0.5)) / 4));
  const yTicks = $derived([0, yMax / 2, yMax]);

  function pick(e: PointerEvent) {
    if (!times.length) return;
    const svg = e.currentTarget as SVGElement;
    const px = e.clientX - svg.getBoundingClientRect().left;
    let best = 0;
    for (let i = 1; i < times.length; i++) if (Math.abs(x(times[i]!) - px) < Math.abs(x(times[best]!) - px)) best = i;
    hover = best;
  }
  function key(e: KeyboardEvent) {
    if (!times.length) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      const d = e.key === "ArrowLeft" ? -1 : 1;
      hover = Math.min(times.length - 1, Math.max(0, (hover ?? times.length - 1) + d));
    } else if (e.key === "Escape") hover = null;
  }

  const hoverT = $derived(hover === null ? null : times[hover] ?? null);
  // El recuadro va al lado de la cruz (a la izquierda si la cruz pasó la mitad): no tapa la línea.
  const tipLeft = $derived(hoverT === null ? 0 : x(hoverT));
  const flip = $derived(tipLeft > width / 2);
  // Lo que dice un lector de pantalla: el último valor y el máximo de cada serie.
  const summary = $derived(series.map((s) => {
    const vals = s.points.map((p) => p[1]);
    return vals.length ? t().chartSummary(s.label, format(vals[vals.length - 1]!), format(Math.max(...vals))) : `${s.label}: ${t().noData}`;
  }).join(". "));
</script>

<div class="chart" bind:clientWidth={width}>
  <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
  <svg {width} {height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${summary}`} tabindex={hasData ? 0 : -1}
    onpointermove={pick} onpointerleave={() => (hover = null)} onkeydown={key} onblur={() => (hover = null)}>
    {#each yTicks as v (v)}
      <line class="grid" x1={pad.l} x2={width - pad.r} y1={y(v)} y2={y(v)} />
      <text class="ax" x={pad.l - 8} y={y(v)} text-anchor="end" dominant-baseline="middle">{axis(v)}</text>
    {/each}
    {#each xTicks as tm (tm)}
      <text class="ax" x={x(tm)} y={height - 6} text-anchor="middle">{fmtTime.format(tm * 1000)}</text>
    {/each}
    {#if limit && !drawLimit}
      <text class="ax lim" x={width - pad.r} y={pad.t - 2} text-anchor="end">{limit.label} ↑</text>
    {:else if limit}
      <line class="limit" x1={pad.l} x2={width - pad.r} y1={y(limit.value)} y2={y(limit.value)} />
      <text class="ax lim" x={width - pad.r} y={y(limit.value) - 5} text-anchor="end">{limit.label}</text>
    {/if}
    {#each series as s (s.key)}
      {#each runs(s.points) as r, i (i)}
        {#if series.length === 1}<path class={`area c${s.tone}`} d={area(r)} />{/if}
        <path class={`line c${s.tone}`} d={line(r)} />
      {/each}
    {/each}
    {#if hoverT !== null}
      <line class="cross" x1={x(hoverT)} x2={x(hoverT)} y1={pad.t} y2={height - pad.b} />
      {#each series as s, i (s.key)}
        {@const v = byTime[i]?.get(hoverT)}
        {#if v !== undefined}<circle class={`dot c${s.tone}`} cx={x(hoverT)} cy={y(v)} r="4" />{/if}
      {/each}
    {/if}
  </svg>
  {#if !hasData}<p class="empty">{empty || t().noDataRange}</p>{/if}
  {#if hoverT !== null}
    <div class="tip" class:flip style:left={`${tipLeft}px`} aria-hidden="true">
      <div class="when">{fmtFull.format(hoverT * 1000)}</div>
      {#each series as s, i (s.key)}
        {@const v = byTime[i]?.get(hoverT)}
        <div class="row"><span class={`key c${s.tone}`}></span><strong>{v === undefined ? "—" : format(v)}</strong><span class="lbl">{s.label}</span></div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .chart { position: relative; width: 100%; }
  svg { display: block; overflow: visible; touch-action: pan-y; border-radius: 4px; }
  svg:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .ax { fill: var(--muted); font: 11px var(--sans); font-variant-numeric: tabular-nums; }
  .lim { fill: var(--muted); font-weight: 500; }
  .limit { stroke: color-mix(in oklch, var(--ink) 45%, transparent); stroke-width: 1; }
  .line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .area { stroke: none; opacity: 0.1; }
  .line.c1 { stroke: var(--chart-1); }
  .line.c2 { stroke: var(--chart-2); }
  .area.c1 { fill: var(--chart-1); }
  .area.c2 { fill: var(--chart-2); }
  .cross { stroke: color-mix(in oklch, var(--ink) 35%, transparent); stroke-width: 1; }
  .dot { stroke: var(--surface); stroke-width: 2; }
  .dot.c1 { fill: var(--chart-1); }
  .dot.c2 { fill: var(--chart-2); }
  .empty {
    position: absolute; inset: 0 0 24px 52px; display: grid; place-items: center; margin: 0;
    color: var(--muted); font-size: 13px; pointer-events: none;
  }
  .tip {
    position: absolute; top: 2px; transform: translateX(10px); z-index: 2; pointer-events: none;
    background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px;
    box-shadow: 0 10px 24px -12px oklch(0.15 0.05 262 / 0.4); font-size: 12.5px; white-space: nowrap;
  }
  .tip.flip { transform: translateX(calc(-100% - 10px)); }
  .when { color: var(--muted); margin-bottom: 2px; }
  .row { display: flex; align-items: center; gap: 6px; }
  .row strong { font-variant-numeric: tabular-nums; font-weight: 600; }
  .lbl { color: var(--muted); }
  .key { width: 12px; height: 2px; border-radius: 1px; }
  .key.c1 { background: var(--chart-1); }
  .key.c2 { background: var(--chart-2); }
</style>
