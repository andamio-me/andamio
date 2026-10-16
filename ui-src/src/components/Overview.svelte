<!--
  El Resumen de una app: cómo va en 5 segundos. Arriba el pulso de las últimas 24 h (CPU y RAM
  contra su límite, tráfico) y si estuvo en línea, hora por hora. Debajo, a la izquierda, lo que
  pasó (deploys, cambios, arranques, caídas y tareas, en una sola línea de tiempo); a la derecha,
  sus piezas (contenedores y servicios), sus tareas, su respaldo y su conexión. Cada cosa lleva a
  su sección para el detalle.
-->
<script lang="ts">
  import type { App, Deploy, Point } from "../lib/api";
  import * as api from "../lib/api";
  import { ago, bytes, mib, until } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import type { Section } from "../lib/nav";
  import Skeleton from "./Skeleton.svelte";
  import Sparkline from "./Sparkline.svelte";

  let { app: a, stamp, deploys, avail, certs, go, onwhy }: {
    app: App; stamp: unknown; deploys: Deploy[] | null;
    avail: { "24h": number | null; "7d": number | null } | null; certs: api.Cert[] | null;
    go: (s: Section) => string; onwhy: (d: Deploy) => void;
  } = $props();

  let metrics = $state<api.Metrics | null>(null);
  let timeline = $state<api.Timeline | null>(null);
  let services = $state<api.Services | null>(null);
  let changes = $state<api.Change[] | null>(null);
  let backups = $state<api.Backups | null>(null);
  $effect(() => {
    const n = a.name;
    void stamp;   // al recargar la app, todo de nuevo
    const fail = (e: Error) => String(e.message);
    api.metrics("24h", n).then((m) => (metrics = m)).catch((e) => (metrics = { range: "24h", start: 0, end: 0, step: 600, error: fail(e), series: {} }));
    api.timeline(n).then((d) => (timeline = d)).catch((e) => (timeline = { hours: [], outages: [], start: 0, end: 0, error: fail(e) }));
    api.services(n).then((d) => (services = d)).catch((e) => (services = { services: [], error: fail(e) }));
    api.history(n).then((d) => (changes = d.changes)).catch(() => (changes = []));
    api.backups().then((d) => (backups = d)).catch(() => (backups = null));
  });

  const now = () => Date.now() / 1000;
  const last = (p: Point[] | undefined) => (p?.length ? p[p.length - 1]![1] : null);
  const peak = (p: Point[] | undefined) => (p?.length ? Math.max(...p.map((x) => x[1])) : null);
  const memLimit = $derived.by(() => {
    const m = String(a.mem ?? "").match(/^(\d+(?:\.\d+)?)([mg])$/i);
    return m ? Number(m[1]) * (m[2]!.toLowerCase() === "g" ? 1024 ** 3 : 1024 ** 2) : 0;
  });
  const cpuLimit = $derived(a.cpus * 100);   // % de un núcleo
  const s = $derived(metrics?.series ?? {});
  const net = $derived.by(() => {
    const tx = new Map((s.tx ?? []).map(([x, v]) => [x, v]));
    return (s.rx ?? []).map(([x, v]) => [x, v + (tx.get(x) ?? 0)] as Point);
  });
  // La RAM en MiB, como su límite (app.yml): "5.8 MiB de 256 MiB", mismas unidades.
  const mem = (n: number) => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(2)} GiB` : `${(n / 1024 ** 2).toFixed(n < 100 * 1024 ** 2 ? 1 : 0)} MiB`);
  const fullDate = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
  const ofLimit = (v: number | null, lim: number) => (v === null || !lim ? null : Math.min(100, (v / lim) * 100));
  const fmtPct = (v: number | null) => (v === null ? "—" : `${v < 1 && v > 0 ? v.toFixed(1) : Math.round(v)} %`);
  const meterTone = (p: number | null) => (p === null ? "" : p >= 90 ? "bad" : p >= 75 ? "warn" : "");
  const cpuNow = $derived(ofLimit(last(s.cpu), cpuLimit));
  const memNow = $derived(last(s.mem));
  const memPct = $derived(ofLimit(memNow, memLimit));

  // En línea, las últimas 24 h (una barra por hora).
  const day = $derived((timeline?.hours ?? []).slice(-24));
  const hourTone = (v: number | null) => (v === null ? "none" : v >= 0.999 ? "ok" : v > 0.01 ? "warn" : "bad");
  const hourFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
  const hourLabel = (h: [number, number | null]) =>
    `${hourFmt.format((h[0] - 3600) * 1000)}: ${h[1] === null ? t().noMeasure : `${Math.round(h[1] * 1000) / 10} % ${t().onlineWord}`}`;
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v >= 99.95 ? 100 : v.toFixed(v >= 99 ? 2 : 1)} %`);
  const pctTone = (v: number | null | undefined) => (v === null || v === undefined ? "" : v >= 99.5 ? "ok" : v >= 95 ? "warn" : "bad");

  // Lo que pasó: una sola línea de tiempo, lo más nuevo arriba.
  type Item = { at: number; kind: "deploy" | "change" | "start" | "down" | "task"; tone: "ok" | "warn" | "bad" | "";
    text: string; sub: string; href?: string; why?: Deploy; live?: boolean };
  const activity = $derived.by(() => {
    if (deploys === null || changes === null) return null;
    const out: Item[] = [];
    const tx = t();
    for (const d of deploys.slice(0, 8)) {
      const done = d.status === "completed", ok = done && d.conclusion === "success";
      out.push({ at: new Date(d.created).getTime() / 1000, kind: "deploy", tone: !done ? "warn" : ok ? "ok" : "bad",
        text: d.title, sub: `${!done ? tx.inProgress : ok ? tx.ovDeploy : tx.ovDeployFailed} · ${d.sha}`, href: d.url,
        why: done && !ok ? d : undefined, live: ok && d.sha === a.live?.version });
    }
    for (const c of changes.slice(0, 8)) {
      out.push({ at: c.at, kind: "change", tone: "", text: c.subject, sub: `${tx.changeKind[c.kind]} · ${c.short}` });
    }
    if (a.live?.started) {
      out.push({ at: new Date(a.live.started).getTime() / 1000, kind: "start", tone: "ok",
        text: tx.ovStarted, sub: `${tx.version} ${a.live.version}${a.live.restarts ? ` · ${tx.ovRestarts(a.live.restarts)}` : ""}` });
    }
    for (const o of timeline?.outages ?? []) {
      out.push({ at: o.start, kind: "down", tone: "bad", text: o.ongoing ? tx.ovDownNow : tx.ovDown, sub: o.ongoing ? tx.ongoing : tx.lasted(o.mins) });
    }
    for (const c of a.cron) {
      if (c.last) out.push({ at: c.last.start, kind: "task", tone: c.last.rc === 0 ? "" : "bad",
        text: c.last.rc === 0 ? tx.ovTaskOk(c.name) : tx.ovTaskFailed(c.name, c.last.rc), sub: tx.ovTook(c.last.secs) });
    }
    return out.sort((x, y) => y.at - x.at).slice(0, 8);
  });

  // Sus piezas: el contenedor web, el worker y los servicios compartidos que usa.
  type Piece = { key: string; label: string; status: string; mem: number | null; cpu: number | null; shared: boolean };
  const pieces = $derived.by(() => {
    if (!services) return null;
    const tx = t();
    const find = (k: string) => services!.services.find((x) => x.kind === k);
    const out: Piece[] = [];
    const add = (k: string, label: string, shared: boolean) => {
      const x = find(k);
      out.push({ key: k, label, status: x?.status ?? (a.stopped && !shared ? "stopped" : "down"), mem: x?.mem ?? null, cpu: x?.cpu ?? null, shared });
    };
    add("app", tx.ovWeb, false);
    if (a.worker) add("worker", "Worker", false);
    if (a.db) add("postgres", "PostgreSQL", true);
    if (a.redis) add("redis", "Redis", true);
    return out;
  });
  const pieceTone = (st: string) => (st === "healthy" || st === "none" ? "ok" : st === "starting" ? "warn" : st === "stopped" ? "" : "bad");
  const pieceText = (st: string) => {
    const tx = t();
    return st === "healthy" ? tx.ovHealthy : st === "none" ? tx.running : st === "starting" ? tx.starting
      : st === "stopped" ? tx.stopped : st === "unhealthy" ? tx.unhealthy : tx.ovDownWord;
  };

  const nextText = (n: string | undefined) => (n === "-" ? t().notApplied : n === "*" ? t().runningNow : n || "?");
  const certTone = (c: api.Cert) => (!c.ok ? "bad" : (c.days ?? 0) < 7 ? "bad" : (c.days ?? 0) < 21 ? "warn" : "ok");
  const keeps = $derived([a.db && t().ovKeepsDb, a.volumes.length && t().ovKeepsFolders(a.volumes.length)].filter(Boolean) as string[]);
</script>

<section aria-labelledby="pulse" class="pulse-sec">
  <div class="shead"><h2 id="pulse">{t().ovPulse}</h2><a class="more" href={go("metrics")}>{t().seeMetrics}</a></div>
  <div class="pulse">
    <div class="vitals">
      <div class="vital">
        <div class="vh"><span class="vl">{t().cpu}</span>{#if metrics && !metrics.error}<span class="pk">{t().ovPeak(fmtPct(ofLimit(peak(s.cpu), cpuLimit)))}</span>{/if}</div>
        <div class="vv"><strong class="num">{metrics ? fmtPct(cpuNow) : "…"}</strong><span class="muted">{t().ovOfCpu(a.cpus)}</span></div>
        <div class={`meter ${meterTone(cpuNow)}`} aria-hidden="true"><span style:width={`${cpuNow ?? 0}%`}></span></div>
        {#if metrics && !metrics.error}<Sparkline points={s.cpu ?? []} start={metrics.start} end={metrics.end} step={metrics.step} label={t().ovSpark(t().cpu)} />{/if}
      </div>
      <div class="vital">
        <div class="vh"><span class="vl">{t().ram}</span>{#if metrics && !metrics.error && peak(s.mem) !== null}<span class="pk">{t().ovPeak(mem(peak(s.mem)!))}</span>{/if}</div>
        <div class="vv"><strong class="num">{metrics ? (memNow === null ? "—" : mem(memNow)) : "…"}</strong><span class="muted">{t().ovOf(mib(a.mem))}</span></div>
        <div class={`meter ${meterTone(memPct)}`} aria-hidden="true"><span style:width={`${memPct ?? 0}%`}></span></div>
        {#if metrics && !metrics.error}<Sparkline points={s.mem ?? []} start={metrics.start} end={metrics.end} step={metrics.step} label={t().ovSpark(t().ram)} />{/if}
      </div>
      <div class="vital">
        <div class="vh"><span class="vl">{t().ovTraffic}</span>{#if metrics && !metrics.error && peak(net) !== null}<span class="pk">{t().ovPeak(`${bytes(peak(net)!)}/s`)}</span>{/if}</div>
        <div class="vv"><strong class="num">{metrics ? (last(net) === null ? "—" : `${bytes(last(net)!)}/s`) : "…"}</strong>
          {#if last(s.rx) !== null}<span class="muted">↓ {bytes(last(s.rx)!)}/s · ↑ {bytes(last(s.tx) ?? 0)}/s</span>{/if}</div>
        <div class="meter ghost" aria-hidden="true"></div>
        {#if metrics && !metrics.error}<Sparkline points={net} start={metrics.start} end={metrics.end} step={metrics.step} tone={2} label={t().ovSpark(t().ovTraffic)} />{/if}
      </div>
    </div>
    {#if metrics?.error}<p class="err muted">{metrics.error}</p>{/if}
    <div class="uptime">
      <div class="uh">
        <span class="vl">{t().ovOnline}</span>
        <span class="num">
          {#if avail}<span class={`pctv ${pctTone(avail["24h"])}`}>{pct(avail["24h"])}</span> <span class="muted">24 h</span>
            <span class="muted">·</span> <span class={`pctv ${pctTone(avail["7d"])}`}>{pct(avail["7d"])}</span> <span class="muted">7 {t().days}</span>
          {:else}<span class="muted">…</span>{/if}
        </span>
      </div>
      <div class="hours" role="img" aria-label={t().ovHoursLabel(day.filter((h) => h[1] !== null && h[1] < 0.999).length)}>
        {#if !timeline}
          {#each Array(24) as _, i (i)}<span class="hr none"></span>{/each}
        {:else}
          {#each day as h (h[0])}<span class={`hr ${hourTone(h[1])}`} title={hourLabel(h)}></span>{/each}
        {/if}
      </div>
      <div class="hlabels muted" aria-hidden="true"><span>{t().ovAgo24}</span><span>{t().now}</span></div>
    </div>
  </div>
</section>

<div class="split">
  <section aria-labelledby="act">
    <div class="shead"><h2 id="act">{t().ovActivity}</h2><a class="more" href={go("deploys")}>{t().seeAllDeploys}</a></div>
    {#if activity === null}
      <Skeleton rows={4} />
    {:else if activity.length}
      <ol class="feed">
        {#each activity as it, i (i)}
          <li class={it.tone}>
            <span class={`ic ${it.kind} ${it.tone}`} aria-hidden="true">
              <svg viewBox="0 0 24 24">
                {#if it.kind === "deploy"}<path d="M12 19V5M5 12l7-7 7 7" />
                {:else if it.kind === "change"}<path d="M4 6h10M18 6h2M4 18h4M12 18h8M14 3v6M8 15v6" />
                {:else if it.kind === "start"}<path d="M12 3v8M6.4 6.4a8 8 0 1 0 11.2 0" />
                {:else if it.kind === "down"}<path d="M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
                {:else}<path d="M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />{/if}
              </svg>
            </span>
            <div class="body">
              <div class="line1">
                {#if it.href}<a href={it.href} target="_blank" rel="noopener noreferrer">{it.text}</a>{:else}<span>{it.text}</span>{/if}
                {#if it.live}<span class="tag live">{t().inProduction}</span>{/if}
              </div>
              <div class="line2 muted">
                <span class={it.tone === "bad" ? "bad-t" : ""}>{it.sub}</span>
                {#if it.why}<button type="button" class="link" onclick={() => onwhy(it.why!)}>{t().seeWhy}</button>{/if}
              </div>
            </div>
            <time class="muted num" datetime={new Date(it.at * 1000).toISOString()} title={fullDate.format(it.at * 1000)}>{ago(now() - it.at)}</time>
          </li>
        {/each}
      </ol>
    {:else}
      <p class="box empty">{t().ovNoActivity}</p>
    {/if}
  </section>

  <aside class="parts" aria-label={t().ovParts}>
    <section aria-labelledby="svc">
      <h3 id="svc">{t().ovServices}</h3>
      {#if pieces === null}
        <Skeleton rows={2} />
      {:else}
        <ul class="plist">
          {#each pieces as p (p.key)}
            <li>
              <span class={`dot ${pieceTone(p.status)}`}></span>
              <span class="pname">{p.label}{#if p.shared}<span class="muted small"> · {t().ovShared}</span>{/if}</span>
              <span class="muted small">{pieceText(p.status)}</span>
              <span class="num small pm">{p.mem === null ? "" : mem(p.mem)}</span>
            </li>
          {/each}
        </ul>
        {#if services?.error}<p class="muted small">{services.error}</p>{/if}
      {/if}
    </section>

    <section aria-labelledby="tsk">
      <div class="h3row"><h3 id="tsk">{t().ovTasks}</h3>{#if a.cron.length}<a class="more" href={go("tasks")}>{t().ovSee}</a>{/if}</div>
      {#if a.cron.length}
        <ul class="plist">
          {#each a.cron.slice(0, 4) as c (c.name)}
            <li>
              <span class={`dot ${c.last ? (c.last.rc === 0 ? "ok" : "bad") : ""}`}></span>
              <span class="pname mono">{c.name}</span>
              <span class="muted small">{c.next === "*" ? t().runningNow : t().ovNext(nextText(c.next))}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="muted small">{t().ovNoTasks} <a href={go("tasks")}>{t().ovAddTask}</a></p>
      {/if}
    </section>

    <section aria-labelledby="bk">
      <div class="h3row"><h3 id="bk">{t().ovBackup}</h3><a class="more" href="#/backups">{t().ovSee}</a></div>
      {#if backups === null}
        <p class="muted small">…</p>
      {:else if !backups.enabled || !backups.configured}
        <p class="muted small">{t().ovBackupOff}</p>
      {:else}
        <p class="bline">
          <span class={`dot ${backups.result === "success" ? "ok" : backups.running ? "warn" : "bad"}`}></span>
          {backups.running ? t().ovBackupRunning : backups.last ? t().ovBackupLast(ago(now() - backups.last)) : t().ovBackupNever}
          {#if backups.next}<span class="muted small"> · {t().ovNextShort(until(backups.next))}</span>{/if}
        </p>
        <p class="muted small">{keeps.length ? t().ovKeeps(keeps.join(t().ovAnd)) : t().ovKeepsNothing}</p>
      {/if}
    </section>

    <section aria-labelledby="cx">
      <h3 id="cx">{t().ovConnection}</h3>
      <ul class="plist">
        {#if certs === null}<li><span class="muted small">…</span></li>{/if}
        {#each certs ?? [] as c (c.host)}
          <li>
            <span class={`dot ${certTone(c)}`}></span>
            <span class="pname mono">{c.host}</span>
            <span class={`small ${certTone(c) === "ok" ? "muted" : certTone(c) + "-t"}`}>{c.ok ? t().certDays(c.days ?? 0) : t().certBad(c.error ?? "")}</span>
          </li>
        {/each}
        <li><span class="ghostdot"></span><span class="pname mono">{a.repo}</span><span class="muted small">{a.access === "public" ? t().public : t().vpnOnly}</span></li>
      </ul>
    </section>
  </aside>
</div>

<style>
  section { margin-top: 0; }
  .pulse-sec { margin-top: var(--space-6); }
  .shead { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); }
  .more { font-size: 13.5px; }
  .muted { color: var(--muted); }
  .small { font-size: 13px; }
  .num { font-variant-numeric: tabular-nums; }
  .mono { font-family: var(--mono); font-size: 0.86em; }
  .bad-t { color: var(--bad-text); }
  .warn-t { color: var(--warn-text); }

  .pulse { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); overflow: hidden; }
  .vitals { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .vital { padding: var(--space-4) var(--space-5) var(--space-3); display: grid; gap: 6px; align-content: start; }
  .vital + .vital { border-left: 1px solid var(--line); }
  .vh { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-2); }
  .vl { font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
  .pk { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .vv { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px; }
  .vv strong { font-size: 24px; font-weight: 600; letter-spacing: -0.01em; line-height: 1.15; }
  .vv .muted { font-size: 13px; }
  .meter { height: 4px; border-radius: 99px; background: var(--sunken); overflow: hidden; }
  .meter span { display: block; height: 100%; min-width: 2px; border-radius: inherit; background: var(--accent); transition: width 400ms var(--ease); }
  .meter.warn span { background: var(--warn); }
  .meter.bad span { background: var(--bad); }
  .meter.ghost { background: transparent; }
  .err { padding: 0 var(--space-5); margin: 0 0 var(--space-3); font-size: 13px; }
  .uptime { border-top: 1px solid var(--line); padding: var(--space-3) var(--space-5) var(--space-4); display: grid; gap: 8px; background: color-mix(in oklch, var(--sunken) 45%, var(--surface)); }
  .uh { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: var(--space-2); font-size: 14px; }
  .pctv { font-weight: 600; }
  .pctv.ok { color: var(--ok-text); }
  .pctv.warn { color: var(--warn-text); }
  .pctv.bad { color: var(--bad-text); }
  .hours { display: grid; grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 3px; height: 22px; }
  .hr { border-radius: 3px; background: var(--sunken); }
  .hr.ok { background: color-mix(in oklch, var(--ok) 70%, var(--surface)); }
  .hr.warn { background: var(--warn); }
  .hr.bad { background: var(--bad); }
  .hr.none { background: var(--line); }
  .hlabels { display: flex; justify-content: space-between; font-size: 12px; }

  .split { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(280px, 1fr); gap: var(--space-6); margin-top: var(--space-6); align-items: start; }

  .feed { list-style: none; margin: 0; padding: 0; position: relative; }
  .feed::before { content: ""; position: absolute; left: 15px; top: 18px; bottom: 18px; width: 1px; background: var(--line); }
  .feed li { position: relative; display: grid; grid-template-columns: 32px minmax(0, 1fr) auto; gap: var(--space-3); align-items: start; padding: var(--space-2) 0; }
  .ic { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; background: var(--surface); border: 1px solid var(--line); color: var(--muted); }
  .ic svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .ic.ok { color: var(--ok-text); border-color: color-mix(in oklch, var(--ok) 35%, var(--line)); background: color-mix(in oklch, var(--ok) 8%, var(--surface)); }
  .ic.warn { color: var(--warn-text); border-color: color-mix(in oklch, var(--warn) 40%, var(--line)); background: color-mix(in oklch, var(--warn) 9%, var(--surface)); }
  .ic.bad { color: var(--bad-text); border-color: color-mix(in oklch, var(--bad) 40%, var(--line)); background: color-mix(in oklch, var(--bad) 8%, var(--surface)); }
  .body { min-width: 0; padding-top: 5px; }
  .line1 { display: flex; flex-wrap: wrap; align-items: center; gap: 4px var(--space-2); font-size: 14.5px; }
  .line1 a, .line1 span:first-child { overflow-wrap: anywhere; }
  .line2 { display: flex; flex-wrap: wrap; gap: var(--space-2); font-size: 12.5px; margin-top: 2px; }
  .feed time { font-size: 12.5px; padding-top: 7px; white-space: nowrap; }
  .link { font: inherit; color: var(--accent); background: none; border: 0; padding: 0; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
  .tag.live { font-size: 11.5px; padding: 1px 8px; border-radius: 999px; background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .empty { padding: var(--space-4); color: var(--muted); font-size: 14px; }

  .parts { border-left: 1px solid var(--line); padding-left: var(--space-6); display: grid; gap: var(--space-5); }
  .parts h3 { margin: 0 0 var(--space-2); font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
  .h3row { display: flex; justify-content: space-between; align-items: baseline; }
  .h3row .more { font-size: 12.5px; }
  .plist { list-style: none; margin: 0; padding: 0; display: grid; gap: 7px; }
  .plist li { display: flex; align-items: center; gap: var(--space-2); font-size: 14px; min-width: 0; }
  .pname { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pm { min-width: 58px; text-align: right; color: var(--muted); }
  .ghostdot { width: 8px; height: 8px; border-radius: 50%; border: 1.5px solid var(--line); flex: none; }
  .bline { margin: 0 0 4px; display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); font-size: 14px; }
  .parts p { margin: 0; }

  @media (max-width: 1100px) {
    .split { grid-template-columns: minmax(0, 1fr); }
    .parts { border-left: 0; padding-left: 0; border-top: 1px solid var(--line); padding-top: var(--space-5); grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  }
  @media (max-width: 720px) {
    .vitals { grid-template-columns: minmax(0, 1fr); }
    .vital + .vital { border-left: 0; border-top: 1px solid var(--line); }
    .hours { gap: 2px; }
  }
</style>
