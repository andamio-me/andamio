<!--
  Los últimos 7 días de la app, una barra por hora: verde en línea, ámbar parcial, roja caída,
  gris sin medición. Debajo, sus caídas (cuándo y cuánto). Sale de la salud de su contenedor web,
  en Prometheus del servidor. Una app detenida a propósito también cuenta como caída.
-->
<script lang="ts">
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";

  let { app }: { app: string } = $props();

  let data = $state<api.Timeline | null>(null);
  let hover = $state<number | null>(null);
  $effect(() => {
    const a = app;
    data = null;
    api.timeline(a).then((d) => (data = d)).catch((e) => (data = { hours: [], outages: [], start: 0, end: 0, error: String(e.message) }));
  });

  const tone = (v: number | null) => (v === null ? "none" : v >= 0.999 ? "ok" : v > 0.01 ? "warn" : "bad");
  const hourFmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric" });
  const label = (h: [number, number | null]) =>
    `${hourFmt.format((h[0] - 3600) * 1000)}: ${h[1] === null ? t().noMeasure : `${Math.round(h[1] * 1000) / 10} % ${t().onlineWord}`}`;
  const measured = $derived((data?.hours ?? []).filter((h) => h[1] !== null).length);
  // Las marcas de los días (la medianoche de cada uno).
  const days = $derived((data?.hours ?? []).map((h, i) => ({ i, d: new Date((h[0] - 3600) * 1000) })).filter((x) => x.d.getHours() === 0));
</script>

<section aria-labelledby="tl-title">
  <div class="shead">
    <div><h2 id="tl-title">{t().timeline}</h2><p class="desc">{t().timelineDesc}</p></div>
  </div>
  <div class="box wrap">
    {#if !data}
      <div class="bars ph" aria-hidden="true">{#each Array(168) as _, i (i)}<span class="bar none"></span>{/each}</div>
    {:else if data.error}
      <p class="muted">{data.error}</p>
    {:else}
      <div class="cap">
        <span class="muted">{hover !== null && data.hours[hover] ? label(data.hours[hover]!) : t().last7days}</span>
        <span class="legend">
          <span><i class="bar ok"></i>{t().online}</span><span><i class="bar warn"></i>{t().partial}</span>
          <span><i class="bar bad"></i>{t().down}</span><span><i class="bar none"></i>{t().noMeasure}</span>
        </span>
      </div>
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_static_element_interactions -->
      <div class="bars" role="img" aria-label={t().timelineSummary(measured, data.outages.length)} onmouseleave={() => (hover = null)}>
        {#each data.hours as h, i (h[0])}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <span class={`bar ${tone(h[1])}`} class:on={hover === i} title={label(h)} onmouseenter={() => (hover = i)}></span>
        {/each}
      </div>
      <div class="days" aria-hidden="true">
        {#each days as d (d.i)}<span style:left={`${(d.i / data.hours.length) * 100}%`}>{dayFmt.format(d.d)}</span>{/each}
      </div>
      {#if data.outages.length}
        <ul class="outages">
          {#each data.outages as o (o.start)}
            <li><span class="dot bad"></span>{hourFmt.format(o.start * 1000)}
              <span class="muted">· {o.ongoing ? t().ongoing : t().lasted(o.mins)}</span></li>
          {/each}
        </ul>
      {:else if measured}
        <p class="ok-line">{t().noOutages}</p>
      {/if}
    {/if}
  </div>
</section>

<style>
  .wrap { padding: var(--space-4); display: grid; gap: var(--space-2); }
  .cap { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-2) var(--space-4); font-size: 13px; }
  .legend { display: flex; flex-wrap: wrap; gap: var(--space-3); color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: 5px; }
  .legend .bar { width: 8px; height: 10px; display: inline-block; }
  .bars { display: flex; gap: 1px; height: 34px; align-items: stretch; }
  .bar { flex: 1; min-width: 1px; border-radius: 1.5px; background: var(--sunken); }
  .bar.ok { background: color-mix(in oklch, var(--ok) 75%, var(--surface)); }
  .bar.warn { background: var(--warn); }
  .bar.bad { background: var(--bad); }
  .bar.none { background: color-mix(in oklch, var(--ink) 8%, var(--surface)); }
  .bar.on { outline: 2px solid var(--ink); outline-offset: 1px; }
  .ph .bar { opacity: 0.6; }
  .days { position: relative; height: 16px; font-size: 11.5px; color: var(--muted); }
  .days span { position: absolute; transform: translateX(-2px); white-space: nowrap; }
  .muted { color: var(--muted); margin: 0; }
  .outages { list-style: none; margin: var(--space-2) 0 0; padding: 0; display: grid; gap: 4px; font-size: 13.5px; }
  .outages li { display: flex; align-items: center; gap: 8px; }
  .ok-line { margin: var(--space-2) 0 0; font-size: 13.5px; color: var(--ok-text); }
  @media (max-width: 640px) { .days span:nth-child(even) { display: none; } }
</style>
