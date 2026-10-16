<!--
  Un deploy en curso, en vivo (como Vercel o Railway): sus tres etapas de GitHub Actions
  (revisión, construir y publicar, desplegar en el servidor), cada una con su paso actual y su
  tiempo, y una barra de avance. Se consulta cada pocos segundos mientras corre; al terminar dice
  cómo salió y avisa (onfinish) para recargar la app. Con `waitFirst` (una app recién creada),
  espera a que aparezca su primer deploy.
-->
<script lang="ts">
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";

  let { app, waitFirst = false, onfinish, onwhy }: {
    app: string; waitFirst?: boolean; onfinish: () => void; onwhy: (d: api.Deploy) => void;
  } = $props();

  let data = $state<api.DeployProgress | null>(null);
  let finished = $state<"" | "ok" | "bad">("");
  let now = $state(Date.now());
  let seenRunning = false;

  $effect(() => {
    const a = app;
    let stop = false, timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      try {
        const d = await api.deployProgress(a);
        if (stop) return;
        data = d;
        const running = d.run && d.run.status !== "completed";
        if (running) seenRunning = true;
        if (d.run && !running && seenRunning && !finished) {
          finished = d.run.conclusion === "success" ? "ok" : "bad";
          onfinish();
        }
        if (running || (waitFirst && !d.run)) timer = setTimeout(tick, 4000);
      } catch {
        if (!stop) timer = setTimeout(tick, 8000);
      }
    };
    void tick();
    const clock = setInterval(() => (now = Date.now()), 1000);
    return () => { stop = true; clearTimeout(timer); clearInterval(clock); };
  });

  const run = $derived(data?.run ?? null);
  const live = $derived(Boolean(run && run.status !== "completed"));
  const show = $derived(live || (waitFirst && !run) || Boolean(finished));
  const LABELS: Record<string, () => string> = {
    "Revisión": () => t().dpCheck, "Construir y publicar imágenes": () => t().dpBuild, "Desplegar en el VPS": () => t().dpDeploy,
  };
  const label = (n: string) => (LABELS[n]?.() ?? n);
  const secs = (a: string, b: string) => Math.max(0, ((b ? new Date(b).getTime() : now) - new Date(a).getTime()) / 1000);
  const fmt = (s: number) => (s < 60 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`);
  const current = (j: api.CiJob) => j.steps.find((s) => s.status === "in_progress")?.name ?? "";
  // Avance: pasos terminados sobre el total (el deploy tiene pocos pasos pero los más largos).
  const progress = $derived.by(() => {
    const all = (data?.jobs ?? []).flatMap((j) => j.steps);
    if (!all.length) return live ? 0.04 : 0;
    return all.filter((s) => s.status === "completed").length / all.length;
  });
  const total = $derived(run ? secs(run.started || run.created, run.status === "completed" ? run.updated ?? "" : "") : 0);
</script>

{#if show}
  <section class={`dp ${finished || (live ? "live" : "wait")}`} aria-live="polite" aria-labelledby="dp-title">
    <div class="dhead">
      <span class="dstate" aria-hidden="true">
        {#if finished === "ok"}✓{:else if finished === "bad"}✗{:else}<span class="spin"></span>{/if}
      </span>
      <div class="dtitle">
        <h2 id="dp-title">
          {#if finished === "ok"}{t().dpDone}{:else if finished === "bad"}{t().dpFailed}{:else if run}{t().dpRunning}{:else}{t().dpWaiting}{/if}
        </h2>
        {#if run}<p><code>{run.sha}</code> · {run.title}</p>{:else}<p>{t().dpWaitingHint}</p>{/if}
      </div>
      <span class="spacer"></span>
      {#if run}<span class="dtime">{fmt(total)}</span>{/if}
      {#if finished === "bad" && run}<button type="button" class="btn small" onclick={() => onwhy(run!)}>{t().seeWhy}</button>{/if}
      {#if run}<a class="btn small quiet" href={run.url} target="_blank" rel="noopener noreferrer">{t().dpGithub}</a>{/if}
      {#if finished}<button type="button" class="btn small quiet" onclick={() => (finished = "")} aria-label={t().close}>×</button>{/if}
    </div>
    <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(progress * 100)}>
      <span style:width={`${Math.max(4, progress * 100)}%`}></span>
    </div>
    {#if data?.jobs.length}
      <ol class="jobs">
        {#each data.jobs as j (j.name)}
          {@const st = j.status !== "completed" ? (j.status === "in_progress" ? "run" : "queued") : j.conclusion === "success" ? "ok" : j.conclusion === "skipped" ? "skip" : "bad"}
          <li class={st}>
            <span class="jicon" aria-hidden="true">
              {#if st === "ok"}✓{:else if st === "bad"}✗{:else if st === "run"}<span class="spin small"></span>{:else}○{/if}
            </span>
            <span class="jname">{label(j.name)}</span>
            <span class="jstep">{st === "run" ? current(j) : st === "queued" ? t().dpQueued : st === "skip" ? t().dpSkipped : ""}</span>
            <span class="jtime">{j.started ? fmt(secs(j.started, j.completed)) : ""}</span>
          </li>
        {/each}
      </ol>
    {/if}
  </section>
{/if}

<style>
  .dp { margin-top: var(--space-5); border: 1px solid var(--line); border-radius: 12px; background: var(--surface); overflow: hidden; }
  .dp.live, .dp.wait { border-color: color-mix(in oklch, var(--accent) 40%, var(--line)); }
  .dp.ok { border-color: color-mix(in oklch, var(--ok) 40%, var(--line)); }
  .dp.bad { border-color: color-mix(in oklch, var(--bad) 40%, var(--line)); }
  .dhead { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); padding: var(--space-4) var(--space-5) var(--space-3); }
  .dstate { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; flex: none;
    background: color-mix(in oklch, var(--accent) 12%, var(--surface)); color: var(--accent); }
  .ok .dstate { background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .bad .dstate { background: color-mix(in oklch, var(--bad) 12%, var(--surface)); color: var(--bad-text); }
  .dtitle { min-width: 0; }
  .dtitle h2 { margin: 0; font-size: 15px; text-transform: none; letter-spacing: 0; color: var(--ink); }
  .dtitle p { margin: 2px 0 0; font-size: 13px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 60ch; }
  .spacer { flex: 1; }
  .dtime { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 13px; }
  .bar { height: 3px; background: var(--sunken); }
  .bar span { display: block; height: 100%; background: var(--accent); transition: width 600ms var(--ease); }
  .ok .bar span { background: var(--ok); }
  .bad .bar span { background: var(--bad); }
  .jobs { list-style: none; margin: 0; padding: var(--space-2) 0; }
  .jobs li { display: grid; grid-template-columns: 22px minmax(140px, auto) minmax(0, 1fr) auto; align-items: center; gap: var(--space-3); padding: 6px var(--space-5); font-size: 14px; }
  .jicon { text-align: center; font-weight: 700; color: var(--muted); }
  .ok .jicon { color: var(--ok-text); }
  .bad .jicon { color: var(--bad-text); }
  .queued .jname, .skip .jname { color: var(--muted); }
  .jstep { color: var(--muted); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .jtime { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
  .spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid color-mix(in oklch, var(--accent) 25%, transparent); border-top-color: var(--accent); display: inline-block; }
  .spin.small { width: 12px; height: 12px; }
  @media (prefers-reduced-motion: no-preference) { .spin { animation: spin 0.9s linear infinite; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (max-width: 640px) { .jobs li { grid-template-columns: 22px minmax(0, 1fr) auto; } .jstep { display: none; } }
</style>
