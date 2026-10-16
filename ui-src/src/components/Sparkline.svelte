<!--
  Una línea mini de las últimas horas (SVG, sin ejes): la forma del uso, no los números. Se estira
  al ancho que tenga; los huecos (sin datos) quedan como huecos. El techo es el máximo de la serie,
  o `max` si se le da (p. ej. el límite de la app, para que la altura diga "cuánto de lo que tiene").
-->
<script lang="ts">
  import type { Point } from "../lib/api";

  let { points, start, end, step, max = 0, tone = 1, label, height = 32 }: {
    points: Point[]; start: number; end: number; step: number; max?: number; tone?: 1 | 2; label: string; height?: number;
  } = $props();

  const H = 32;
  const top = $derived(Math.max(max, ...points.map((p) => p[1])) * 1.1 || 1);
  const x = (t: number) => ((t - start) / Math.max(1, end - start)) * 100;
  const y = (v: number) => H - 1 - (v / top) * (H - 3);
  const runs = $derived.by(() => {
    const out: Point[][] = [];
    let cur: Point[] = [];
    for (const p of points) {
      if (cur.length && p[0] - cur[cur.length - 1]![0] > step * 1.5) { out.push(cur); cur = []; }
      cur.push(p);
    }
    if (cur.length) out.push(cur);
    return out;
  });
  const line = (r: Point[]) => r.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(2)},${y(p[1]).toFixed(2)}`).join("");
  const area = (r: Point[]) => `${line(r)}L${x(r[r.length - 1]![0]).toFixed(2)},${H}L${x(r[0]![0]).toFixed(2)},${H}Z`;
</script>

<svg viewBox={`0 0 100 ${H}`} preserveAspectRatio="none" role="img" aria-label={label} class={`c${tone}`} style:height={`${height}px`}>
  <line class="base" x1="0" x2="100" y1={H - 0.5} y2={H - 0.5} />
  {#each runs as r, i (i)}
    <path class="area" d={area(r)} />
    <path class="line" d={line(r)} />
  {/each}
</svg>

<style>
  svg { display: block; width: 100%; height: 32px; overflow: visible; }
  .base { stroke: var(--line); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .line { fill: none; stroke-width: 1.5; vector-effect: non-scaling-stroke; stroke-linejoin: round; }
  .c1 .line { stroke: var(--chart-1); }
  .c2 .line { stroke: var(--chart-2); }
  .c1 .area { fill: color-mix(in oklch, var(--chart-1) 12%, transparent); }
  .c2 .area { fill: color-mix(in oklch, var(--chart-2) 12%, transparent); }
</style>
