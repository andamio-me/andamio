<!--
  Una app, en secciones (el sidebar las lista; cada una tiene su link #/app/<app>/<sección>):
  Resumen (cómo está y qué pide atención), Deploys, Logs, Métricas (uso y caídas), Variables,
  Tareas, Base de datos y Ajustes (recursos, red, cambios, zona de peligro). Arriba, fijo: su
  nombre, su estado y sus acciones. Cada sección trae solo lo suyo. Toda acción pasa por la
  terminal, con el comando de la CLI a la vista.
-->
<script lang="ts">
  import type { AppData, Deploy, Meta, SetValues } from "../lib/api";
  import * as api from "../lib/api";
  import { ago, bytes, mib, since, status } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { commandFor, job } from "../lib/job.svelte";
  import { guard } from "../lib/guard.svelte";
  import CiFailure from "./CiFailure.svelte";
  import CronRuns from "./CronRuns.svelte";
  import DangerZone from "./DangerZone.svelte";
  import EditField from "./EditField.svelte";
  import History from "./History.svelte";
  import ListEditor from "./ListEditor.svelte";
  import Logs from "./Logs.svelte";
  import Overview from "./Overview.svelte";
  import MoreMenu from "./MoreMenu.svelte";
  import DeployProgress from "./DeployProgress.svelte";
  import PendingBar from "./PendingBar.svelte";
  import RollbackDialog from "./RollbackDialog.svelte";
  import Secrets from "./Secrets.svelte";
  import Skeleton from "./Skeleton.svelte";
  import SqlConsole from "./SqlConsole.svelte";
  import SourceSettings from "./SourceSettings.svelte";
  import TaskForm from "./TaskForm.svelte";
  import Timeline from "./Timeline.svelte";
  import Usage from "./Usage.svelte";

  import { appHref, type Section } from "../lib/nav";

  let { data, meta, reload, section = "overview" }: {
    data: AppData; meta: Meta | null; reload: () => Promise<void>; section?: Section;
  } = $props();

  const a = $derived(data.app);
  const lv = $derived(a.live);
  const st = $derived(status(a));
  const offline = $derived(Boolean(data.error));
  const refresh = () => void reload();
  const go = (s: Section) => appHref(a.name, s);

  // Los deploys (GitHub) llegan aparte: la página no los espera. Los usan Resumen, Deploys y el sidebar.
  let deploys = $state<Deploy[] | null>(null);
  $effect(() => {
    const n = data.app.name;
    void data;   // al recargar la app, también
    api.appDeploys(n).then((r) => (deploys = r.deploys)).catch(() => (deploys = deploys ?? []));
  });
  const lastFailed = $derived(deploys?.[0]?.status === "completed" && deploys[0].conclusion === "failure");
  // Deploy en vivo: se enciende si hay uno en curso (o la app espera su primero) y se queda hasta
  // que lo cierras, para que veas cómo terminó.
  let dpActive = $state(false);
  let dpFor = "";
  $effect(() => {
    if (dpFor !== data.app.name) { dpFor = data.app.name; dpActive = false; }
    if (deploys === null) return;
    const running = deploys[0] && deploys[0].status !== "completed";
    const waiting = !deploys.length && !data.app.live && !data.app.stopped;
    if (running || waiting) dpActive = true;
  });

  // Sugerencias (Resumen y Ajustes), disponibilidad y certificados (Resumen): solo donde se ven.
  let sugg = $state<api.Suggest | null>(null);
  let avail = $state<{ "24h": number | null; "7d": number | null } | null>(null);
  let certs = $state<api.Cert[] | null>(null);
  $effect(() => {
    const n = data.app.name;
    if (section !== "overview" && section !== "settings") return;
    api.suggest(n).then((r) => (sugg = r)).catch(() => (sugg = null));
  });
  $effect(() => {
    const n = data.app.name;
    if (section !== "overview") return;
    api.availability().then((r) => (avail = r.apps[n] ?? null)).catch(() => (avail = null));
    api.certs().then((r) => (certs = r.apps[n] ?? [])).catch(() => (certs = []));
  });

  // Cambios de configuración pendientes: viven aquí (no se pierden al cambiar de sección).
  let pending = $state<SetValues>({});
  const changes = $derived(Object.fromEntries(Object.entries(pending).filter(([, v]) => v !== undefined)) as SetValues);
  const count = $derived(Object.keys(changes).length);
  $effect(() => guard(() => count > 0 && !job.locked));
  const check = {
    mem: (v: string) => (/^[0-9]+[mg]$/.test(v) ? null : t().badMem),
    cpus: (v: string) => (/^[0-9]+(\.[0-9]+)?$/.test(v) && Number(v) > 0 ? null : t().badCpu),
    port: (v: string) => (/^[0-9]{2,5}$/.test(v) && Number(v) <= 65535 ? null : t().badPort),
    health: (v: string) => (/^\/[A-Za-z0-9._/-]*$/.test(v) ? null : t().badHealth),
    db_connections: (v: string) => (/^[0-9]{1,3}$/.test(v) && Number(v) <= 500 ? null : t().badDbConns),
    db_timeout: (v: string) => (/^(0|[1-9][0-9]{0,4}(ms|s|min))$/.test(v) ? null : t().badDbTimeout),
  };
  const after = (ok: boolean) => {
    if (ok) pending = {};
    void reload();
  };
  const apply = () => {
    job.arm({ action: "set", app: a.name, set: changes }, after);
    void job.run();
  };
  const toggle = () => job.arm({ action: a.stopped ? "start" : "stop", app: a.name }, after);
  // Una sugerencia "Usar": queda pendiente y te lleva a Ajustes, donde se ve y se aplica.
  function useSuggestion(key: "mem" | "cpus", value: string) {
    pending[key] = value;
    if (section !== "settings") location.hash = go("settings");
  }

  // Ajustes: sus secciones, con un índice a la derecha y un filtro (por título y palabras clave).
  // Base de datos: con PostgreSQL y MariaDB a la vez, cuál se consulta.
  let dbEngine = $state<api.SqlEngine>("postgres");
  const engineShown = $derived<api.SqlEngine>(a.db && a.mysql ? dbEngine : a.mysql ? "mysql" : "postgres");
  let setFilter = $state("");
  let setActive = $state("code");
  const SETS = $derived([
    { id: "code", label: t().srcTitle, words: `${t().srcTitle} repo ${t().srcFolder} ${t().srcBranch} ${t().srcWatch} pipeline github dir monorepo` },
    { id: "res", label: t().resources, words: `${t().resources} ${t().ram} ${t().cpus} ${t().port} ${t().health} ${t().access} memoria memory vpn public` },
    ...(data.app.db || data.app.mysql ? [{ id: "db", label: t().dbLimits, words: `${t().dbLimits} postgres base database conexiones connections timeout consulta query` }] : []),
    { id: "net", label: t().network, words: `${t().network} ${t().domainsTitle} ${t().corsTitle} ${t().foldersTitle} dominio domain volume` },
    { id: "changes", label: t().changes, words: `${t().changes} ${t().changesDesc} historial history revert deshacer undo` },
    { id: "danger", label: t().danger, words: `${t().danger} borrar eliminar delete destroy restaurar restore respaldo backup` },
  ]);
  const shows = (id: string) => {
    const q = setFilter.trim().toLowerCase();
    return !q || (SETS.find((x) => x.id === id)?.words.toLowerCase().includes(q) ?? true);
  };
  // La sección que se ve, para marcarla en el índice.
  $effect(() => {
    if (section !== "settings") return;
    void setFilter;
    const els = SETS.map((x) => document.getElementById(`set-${x.id}`)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver((entries) => {
      const top = entries.filter((e) => e.isIntersecting).sort((x, y) => x.boundingClientRect.top - y.boundingClientRect.top)[0];
      if (top) setActive = top.target.id.replace("set-", "");
    }, { rootMargin: "-80px 0px -60% 0px" });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  });

  // Tareas.
  let addingTask = $state(false);
  let taskPreset = $state("");
  // Para empezar sin saber cron: horarios típicos (el comando lo pones tú).
  const TASK_EXAMPLES = $derived([
    { schedule: "0 3 * * *", label: t().exNightly, hint: t().exNightlyHint },
    { schedule: "0 * * * *", label: t().exHourly, hint: t().exHourlyHint },
    { schedule: "*/15 * * * *", label: t().exQuarter, hint: t().exQuarterHint },
    { schedule: "0 8 * * 1", label: t().exWeekly, hint: t().exWeeklyHint },
  ]);
  let editingTask = $state("");
  let showRuns = $state<Record<string, boolean>>({});
  const runTask = (task: string) => job.arm({ action: "cron-run", app: a.name, task }, () => void reload());
  const nextText = (n: string | undefined) => (n === "-" ? t().notApplied : n === "*" ? t().runningNow : n || "?");

  // Deploys agrupados por día (Hoy, Ayer, el día), con la hora y cuánto tardó cada uno.
  const dayKey = (iso: string) => new Date(iso).toDateString();
  function dayLabel(iso: string): string {
    const d = new Date(iso), today = new Date();
    const diff = Math.round((new Date(today.toDateString()).getTime() - new Date(d.toDateString()).getTime()) / 86_400_000);
    if (diff === 0) return t().today;
    if (diff === 1) return t().yesterday;
    return new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" }).format(d);
  }
  function byDay(list: Deploy[]) {
    const out: { key: string; label: string; items: Deploy[] }[] = [];
    for (const d of list) {
      const k = dayKey(d.created);
      if (out.at(-1)?.key !== k) out.push({ key: k, label: dayLabel(d.created), items: [] });
      out.at(-1)!.items.push(d);
    }
    return out;
  }
  const clock = (iso: string) => new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
  const runSecs = (d: Deploy) => (d.started && d.updated && d.status === "completed"
    ? Math.max(0, (new Date(d.updated).getTime() - new Date(d.started).getTime()) / 1000) : null);
  const fmtDur = (s: number) => (s < 60 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`);

  // Deploys: volver a uno anterior y ver por qué falló.
  let rollbackTo = $state<Deploy | null>(null);
  let rollbackOpen = $state(false);
  let whyRun = $state<Deploy | null>(null);
  let whyOpen = $state(false);
  const live = $derived(lv?.version ?? "");
  const memBytes = $derived.by(() => {
    const m = String(a.mem ?? "").match(/^(\d+(?:\.\d+)?)([mg])$/i);
    return m ? Number(m[1]) * (m[2]!.toLowerCase() === "g" ? 1024 ** 3 : 1024 ** 2) : null;
  });

  // Lo que pide atención en el Resumen.
  const attention = $derived.by(() => {
    const out: { tone: "bad" | "warn" | "info"; text: string; action?: { label: string; run: () => void }; href?: string }[] = [];
    const s = t();
    if (lastFailed && deploys?.[0]) {
      const d = deploys[0];
      out.push({ tone: "bad", text: s.attnDeployFailed(d.sha), action: { label: s.seeWhy, run: () => { whyRun = d; whyOpen = true; } } });
    }
    for (const c of certs ?? []) {
      if (!c.ok) out.push({ tone: "bad", text: s.certProblem(c.host) });
      else if ((c.days ?? 99) < 21) out.push({ tone: "warn", text: s.certSoon(c.host, c.days ?? 0) });
    }
    if (sugg && !sugg.error) {
      if (sugg.mem?.suggest) {
        const v = sugg.mem.suggest;
        out.push({ tone: sugg.mem.why === "up" ? "warn" : "info",
          text: sugg.mem.why === "up" ? s.memUp(bytes(sugg.mem.peak), mib(a.mem), sugg.days) : s.memDown(bytes(sugg.mem.peak), mib(a.mem), sugg.days),
          action: { label: s.useValue(mib(v)), run: () => useSuggestion("mem", v) } });
      }
      if (sugg.cpu?.suggest) {
        const v = sugg.cpu.suggest;
        out.push({ tone: sugg.cpu.why === "up" ? "warn" : "info",
          text: sugg.cpu.why === "up" ? s.cpuUp(sugg.cpu.p95, sugg.cpu.limit, sugg.days) : s.cpuDown(sugg.cpu.max, sugg.cpu.limit, sugg.days),
          action: { label: s.useValue(`${v} CPU`), run: () => useSuggestion("cpus", v) } });
      }
    }
    return out;
  });
</script>

{#if job.busy && job.app === a.name}
  <div class="busy" role="status">
    <span class="spin" aria-hidden="true"></span>
    <span class="grow">{t().busyHere(job.kind)}</span>
    {#if job.minimized}<button type="button" class="btn small" onclick={() => job.expand()}>{t().seeProgress}</button>{/if}
  </div>
{/if}

<header class="head">
  <div class="id">
    <h1>{a.name}</h1>
    <span class="state"><span class={`dot ${offline ? "" : st.tone}`}></span>{offline ? t().noData : st.text}</span>
  </div>
  <div class="links">
    <a href={a.url} target="_blank" rel="noopener noreferrer">{a.url.replace("https://", "")}</a>
    <span class="tag" class:public={a.access === "public"}>{a.access === "public" ? t().public : t().vpnOnly}</span>
  </div>
  <div class="hacts">
    <!-- Una acción principal (Desplegar; o Encender si está apagada) y el resto en "⋯". -->
    {#if a.stopped}
      <button type="button" class="btn primary" onclick={toggle} disabled={job.locked} aria-label={t().start(a.name)}>{t().startShort}</button>
    {:else}
      <button type="button" class="btn primary" disabled={job.locked} title={t().deployNowHint}
        onclick={() => job.arm({ action: "deploy", app: a.name }, refresh)}>{t().deployShort}</button>
      <MoreMenu items={[
        { label: t().restart, hint: t().restartHint, disabled: job.locked || !lv, run: () => job.arm({ action: "restart", app: a.name }, after) },
        { label: t().stopShort, hint: t().stopHint, danger: true, disabled: job.locked || !lv, run: toggle },
      ]} />
    {/if}
  </div>
</header>

{#if dpActive && (section === "overview" || section === "deploys")}
  {#key a.name}
    <DeployProgress app={a.name} waitFirst={!deploys?.length} onfinish={refresh} onwhy={(d) => { whyRun = d; whyOpen = true; }} />
  {/key}
{/if}

{#if section === "overview"}
  {#if attention.length}
    <section aria-labelledby="attn" class="first">
      <h2 id="attn">{t().needsAttention}</h2>
      <ul class="attn">
        {#each attention as it, i (i)}
          <li class={it.tone}>
            <span class={`dot ${it.tone === "info" ? "" : it.tone}`}></span>
            <span class="grow">{it.text}</span>
            {#if it.action}<button type="button" class="btn small" disabled={job.locked} onclick={it.action.run}>{it.action.label}</button>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <Overview app={a} stamp={data} {deploys} {avail} {certs} {go} onwhy={(d) => { whyRun = d; whyOpen = true; }} />
{/if}

{#if section === "deploys"}
  <section aria-labelledby="deploys" class="first">
    <div class="shead">
      <div>
        <h2 id="deploys">{t().deploys}</h2>
        <p class="desc" class:failed={lastFailed}>{lastFailed ? t().lastFailed : t().deploysDesc(a.branch || "main")}</p>
      </div>
      <div class="hacts">
        {#if lastFailed}
          <button type="button" class="btn small" disabled={job.locked} onclick={() => job.arm({ action: "retry", app: a.name }, refresh)}>{t().retry}</button>
        {/if}
        {#if !a.stopped}
          <button type="button" class="btn small" disabled={job.locked} title={t().deployNowHint}
            onclick={() => job.arm({ action: "deploy", app: a.name }, refresh)}>{t().deployNow}</button>
        {/if}
      </div>
    </div>
    {#if deploys === null}
      <Skeleton rows={4} />
    {:else if deploys.length}
      <div class="days">
        {#each byDay(deploys) as g (g.key)}
          <h3 class="day">{g.label}</h3>
          <ul class="list deploys">{#each g.items as d (d.id)}{@render deployRow(d)}{/each}</ul>
        {/each}
      </div>
    {:else}
      <p class="box row empty">{t().noDeploys}</p>
    {/if}
  </section>
{/if}

{#if section === "logs"}
  <div class="first"><Logs app={a.name} worker={Boolean(a.worker)} tall /></div>
{/if}

{#if section === "metrics"}
  <Usage id="usage" app={a.name} heading={t().usage} desc={t().usageDesc} memLimit={memBytes} cpuLimit={a.cpus ? a.cpus * 100 : null} />
  {#key a.name}<Timeline app={a.name} />{/key}
{/if}

{#if section === "variables"}
  <div class="first"><Secrets app={a.name} secrets={a.secrets ?? []} ondone={refresh} autoCheck={lastFailed} /></div>
{/if}

{#if section === "tasks"}
  <section aria-labelledby="tasks" class="first">
    <div class="shead">
      <div>
        <h2 id="tasks">{t().tasks}</h2>
        <p class="desc">{t().tasksDesc(a.timezone ?? "UTC")}</p>
      </div>
      {#if !addingTask}
        <button type="button" class="btn small" onclick={() => (addingTask = true)} disabled={job.locked}>{t().newTask}</button>
      {/if}
    </div>
    <div class="box">
      {#if addingTask}
        <TaskForm app={a.name} taken={a.cron.map((c) => c.name)} timezoneSet={meta?.timezone_set ?? false} preset={taskPreset}
          onclose={() => { addingTask = false; taskPreset = ""; }} ondone={refresh} />
      {/if}
      {#each a.cron as c (c.name)}
        {#if editingTask === c.name}
          <TaskForm app={a.name} taken={a.cron.map((x) => x.name)} timezoneSet={meta?.timezone_set ?? true} edit={c}
            onclose={() => (editingTask = "")} ondone={refresh} />
        {:else}
          <div class="row">
            <div class="grow">
              <div class="tname"><strong>{c.name}</strong><code class="sched">{c.schedule}</code></div>
              <code class="cmd">{c.command}</code>
            </div>
            <dl class="when">
              <dt>{t().next}</dt><dd>{nextText(c.next)}</dd>
              <dt>{t().last}</dt>
              <dd>
                {#if c.last}
                  <span class="state"><span class={`dot ${c.last.rc === 0 ? "ok" : "bad"}`}></span>{c.last.rc === 0 ? t().okShort : t().code(c.last.rc)} · {ago(Date.now() / 1000 - c.last.start)}</span>
                {:else}<span class="muted">{t().notRun}</span>{/if}
              </dd>
            </dl>
            <span class="acts">
              <button type="button" class="btn small quiet" aria-expanded={Boolean(showRuns[c.name])}
                onclick={() => (showRuns[c.name] = !showRuns[c.name])}>{t().runsBtn}</button>
              <button type="button" class="btn small quiet" onclick={() => (editingTask = c.name)} disabled={job.locked}
                aria-label={t().editTask(c.name)}>{t().editShort}</button>
              <button type="button" class="btn small" onclick={() => runTask(c.name)} disabled={job.locked} aria-label={t().runTask(c.name)}>{t().runNow}</button>
              <button type="button" class="btn small quiet danger" disabled={job.locked} aria-label={t().removeX(c.name)}
                onclick={() => job.arm({ action: "cron-rm", app: a.name, task: c.name }, refresh)}>{t().remove}</button>
            </span>
            {#if showRuns[c.name]}<div class="runswrap"><CronRuns app={a.name} task={c.name} /></div>{/if}
          </div>
        {/if}
      {:else}
        {#if !addingTask}
          <div class="emptyst">
            <p>{t().tasksEmptyLead}</p>
            <div class="examples">
              {#each TASK_EXAMPLES as ex (ex.schedule)}
                <button type="button" class="ex" disabled={job.locked} onclick={() => { taskPreset = ex.schedule; addingTask = true; }}>
                  <span class="exl">{ex.label}</span><span class="exh">{ex.hint}</span><code>{ex.schedule}</code>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      {/each}
    </div>
  </section>
{/if}

{#if section === "database"}
  {#if a.db || a.mysql}
    {#if a.db && a.mysql}
      <div class="seg dbseg first" role="radiogroup" aria-label={t().dbEngine}>
        {#each [["postgres", "PostgreSQL"], ["mysql", "MariaDB"]] as [v, label] (v)}
          <button type="button" role="radio" aria-checked={dbEngine === v} class:on={dbEngine === v} onclick={() => (dbEngine = v as api.SqlEngine)}>{label}</button>
        {/each}
      </div>
    {/if}
    <div class:first={!(a.db && a.mysql)}>{#key `${a.name}:${engineShown}`}<SqlConsole app={a.name} engine={engineShown} />{/key}</div>
  {:else}
    <p class="box row empty first">{t().noDatabase}</p>
  {/if}
{/if}

{#if section === "settings"}
  <div class="setwrap">
    <div class="setmain">
      <div class="sfilter">
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
        <input type="search" bind:value={setFilter} placeholder={t().filterSettings} aria-label={t().filterSettings} spellcheck="false" />
      </div>
      {#if shows('code')}
    <section aria-labelledby="code" id="set-code" class="sset first">
      <div class="shead"><div><h2 id="code">{t().srcTitle}</h2><p class="desc">{t().srcDesc}</p></div></div>
      <SourceSettings app={a} ondone={refresh} />
    </section>
      {/if}
      {#if shows('res')}
    <section aria-labelledby="cfg" id="set-res" class="sset">
      <div class="shead"><div><h2 id="cfg">{t().resources}</h2><p class="desc">{t().configDesc}</p></div></div>
      <dl class="kv box pad">
        <EditField id="f-mem" label={t().ram} current={a.mem} shown={mib(a.mem)} bind:pending={pending.mem} hint={t().memHint} check={check.mem} disabled={job.locked} format={mib} />
        <EditField id="f-cpus" label={t().cpus} current={String(a.cpus)} shown={String(a.cpus)} bind:pending={pending.cpus} hint={t().cpuHint} check={check.cpus} disabled={job.locked} />
        <EditField id="f-port" label={t().port} current={String(a.port)} shown={String(a.port)} bind:pending={pending.port} hint={t().portHint} check={check.port} disabled={job.locked} mono />
        <EditField id="f-health" label={t().health} current={a.health} shown={a.health || "—"} bind:pending={pending.health} hint={t().healthHint} check={check.health} disabled={job.locked} mono />
        <dt id="acc-label">{t().access}</dt>
        <dd>
          <div class="seg" role="radiogroup" aria-labelledby="acc-label">
            {#each [["vpn", t().accessVpn], ["public", t().accessPublic]] as [val, text] (val)}
              {@const on = (pending.access ?? a.access) === val}
              <button type="button" role="radio" aria-checked={on} class:on disabled={job.locked}
                onclick={() => (pending.access = val === a.access ? undefined : (val as "vpn" | "public"))}>{text}</button>
            {/each}
          </div>
          {#if pending.access === "public"}<p class="warn">{t().publicWarn}</p>{/if}
        </dd>
        {#if sugg && !sugg.error && (sugg.mem?.suggest || sugg.cpu?.suggest)}
          <dt>{t().suggestions}</dt>
          <dd>
            <ul class="sugg">
              {#if sugg.mem?.suggest}
                <li>
                  <span>{sugg.mem.why === "up" ? t().memUp(bytes(sugg.mem.peak), mib(a.mem), sugg.days) : t().memDown(bytes(sugg.mem.peak), mib(a.mem), sugg.days)}</span>
                  <button type="button" class="btn small" disabled={job.locked || pending.mem === sugg.mem.suggest}
                    onclick={() => useSuggestion("mem", sugg!.mem!.suggest!)}>{t().useValue(mib(sugg.mem.suggest))}</button>
                </li>
              {/if}
              {#if sugg.cpu?.suggest}
                <li>
                  <span>{sugg.cpu.why === "up" ? t().cpuUp(sugg.cpu.p95, sugg.cpu.limit, sugg.days) : t().cpuDown(sugg.cpu.max, sugg.cpu.limit, sugg.days)}</span>
                  <button type="button" class="btn small" disabled={job.locked || pending.cpus === sugg.cpu.suggest}
                    onclick={() => useSuggestion("cpus", sugg!.cpu!.suggest!)}>{t().useValue(`${sugg.cpu.suggest} CPU`)}</button>
                </li>
              {/if}
            </ul>
          </dd>
        {/if}
        {#if a.worker}<dt>{t().worker}</dt><dd class="mono">{a.worker}</dd>{/if}
      </dl>
    </section>
      {/if}
      {#if (a.db || a.mysql) && shows('db')}
    <section aria-labelledby="dbl" id="set-db" class="sset">
      <div class="shead"><div><h2 id="dbl">{t().dbLimits}</h2><p class="desc">{t().dbLimitsDesc}</p></div>
        <a class="btn small quiet" href="#/services">{t().svSee}</a></div>
      <dl class="kv box pad">
        <EditField id="f-dbc" label={t().dbConns} current={String(a.db_connections)} shown={a.db_connections ? String(a.db_connections) : t().svNoLimit}
          bind:pending={pending.db_connections} hint={t().dbConnsHint} check={check.db_connections} disabled={job.locked}
          format={(v) => (v === "0" ? t().svNoLimit : v)} />
        <EditField id="f-dbt" label={t().dbTimeout} current={a.db_timeout} shown={a.db_timeout !== "0" ? a.db_timeout : t().svNoLimit}
          bind:pending={pending.db_timeout} hint={t().dbTimeoutHint} check={check.db_timeout} disabled={job.locked} mono
          format={(v) => (v === "0" ? t().svNoLimit : v)} />
      </dl>
    </section>
      {/if}
      {#if shows('net')}
    <section aria-labelledby="net" id="set-net" class="sset">
      <div class="shead"><div><h2 id="net">{t().network}</h2><p class="desc">{t().networkDesc}</p></div></div>
      <div class="lists">
        <ListEditor app={a.name} kind="domain" title={t().domainsTitle} items={a.domains} placeholder={t().domainPh} ondone={refresh}
          fixed={a.url.replace("https://", "").split("/")[0]} />
        <ListEditor app={a.name} kind="cors" title={t().corsTitle} items={a.cors} placeholder={t().corsPh} ondone={refresh} />
        <ListEditor app={a.name} kind="volume" title={t().foldersTitle} items={a.volumes} placeholder={t().folderPh} ondone={refresh}
          note={t().folderRmNote} />
      </div>
    </section>
      {/if}
      {#if shows('changes')}
    <section aria-labelledby="changes" id="set-changes" class="sset">
      <div class="shead"><div><h2 id="changes">{t().changes}</h2><p class="desc">{t().changesDesc}</p></div></div>
      {#key a.name}<History app={a.name} embedded limit={5} />{/key}
    </section>
      {/if}
      {#if shows('danger')}
    <div id="set-danger" class="sset">
      <DangerZone app={a.name} repo={a.repo} protectedApp={a.name === meta?.dashboard_app} restorable={a.db || a.mysql || a.volumes.length > 0} />
    </div>
      {/if}
      {#if !SETS.some((x) => shows(x.id))}<p class="box row empty">{t().filterNone(setFilter)}</p>{/if}
    </div>
    <nav class="toc" aria-label={t().onThisPage}>
      <p class="toch">{t().onThisPage}</p>
      {#each SETS.filter((x) => shows(x.id)) as x (x.id)}
        <button type="button" class:on={setActive === x.id} onclick={() => document.getElementById(`set-${x.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}>{x.label}</button>
      {/each}
    </nav>
  </div>
{/if}

{#snippet deployRow(d: Deploy)}
  {@const done = d.status === "completed"}
  {@const ok = done && d.conclusion === "success"}
  {@const isLive = ok && live !== "" && d.sha === live}
  {@const dur = runSecs(d)}
  <li class:islive={isLive} class:failed={done && !ok}>
    <span class={`dot ${!done ? "warn" : ok ? "ok" : "bad"}`} aria-hidden="true"></span>
    <div class="dmain">
      <a href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a>
      <div class="dsub">
        <code>{d.sha}</code>
        <span title={new Date(d.created).toLocaleString()}>{clock(d.created)}</span>
        {#if !done}<span class="warn-t">{t().inProgress}</span>
        {:else if dur !== null}<span>{t().deployTook(fmtDur(dur))}</span>{/if}
        {#if done && !ok}<span class="bad-t">{d.conclusion === "failure" ? t().deployFailedWord : d.conclusion}</span>{/if}
      </div>
    </div>
    <div class="dacts">
      {#if isLive}<span class="tag live">{t().inProduction}</span>{/if}
      {#if done && !ok}
        <button type="button" class="btn small" onclick={() => { whyRun = d; whyOpen = true; }}>{t().seeWhy}</button>
      {:else if ok && !isLive && d.full && lv && !a.stopped && section === "deploys"}
        <button type="button" class="btn small quiet roll" disabled={job.locked} aria-label={t().rollbackTo(d.sha)}
          onclick={() => { rollbackTo = d; rollbackOpen = true; }}>{t().rollbackShort}</button>
      {/if}
    </div>
  </li>
{/snippet}

<CiFailure bind:open={whyOpen} app={a.name} run={whyRun} />
<RollbackDialog bind:open={rollbackOpen} app={a.name} current={live} target={rollbackTo} ondone={refresh} />

{#if count && !job.open}
  <PendingBar {count} command={commandFor({ action: "set", app: a.name, set: changes })} busy={job.locked}
    ondiscard={() => (pending = {})} onapply={apply} />
{/if}

<style>
  .head {
    display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3) var(--space-5); padding-bottom: var(--space-5);
    border-bottom: 1px solid var(--line);
  }
  .id { display: flex; align-items: baseline; gap: var(--space-4); }
  .links { display: flex; align-items: center; gap: var(--space-3); flex: 1; }
  .state { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
  .hacts { display: flex; flex-wrap: wrap; gap: var(--space-2); }
  section, .first { margin-top: var(--space-6); }
  :global(section.sec) { margin-top: var(--space-6); }
  .shead { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); }
  .more { font-size: 13.5px; }
  .kv { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: var(--space-2) var(--space-4); margin: 0; align-items: center; }
  .kv.pad { padding: var(--space-4) var(--space-5); }
  .kv :global(dt) { color: var(--muted); font-size: 14px; }
  .kv :global(dd) { margin: 0; overflow-wrap: anywhere; }
  .attn { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
  .attn li {
    display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); padding: var(--space-3) var(--space-4);
    border-radius: 10px; border: 1px solid var(--line); background: var(--surface); font-size: 14px;
  }
  .attn li.bad { border-color: color-mix(in oklch, var(--bad) 40%, var(--line)); background: color-mix(in oklch, var(--bad) 6%, var(--surface)); }
  .attn li.warn { border-color: color-mix(in oklch, var(--warn) 40%, var(--line)); background: color-mix(in oklch, var(--warn) 7%, var(--surface)); }
  .attn li.info { background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .mono { font-family: var(--mono); font-size: 0.9em; }
  .num { font-variant-numeric: tabular-nums; }
  .muted { color: var(--muted); }
  .warn { margin: 6px 0 0; font-size: 13px; color: var(--warn-text); }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); }
  .seg button {
    font: 500 13px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px;
    padding: 7px 12px; cursor: pointer; transition: background-color 150ms var(--ease), color 150ms var(--ease);
  }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }
  .seg button:disabled { cursor: not-allowed; opacity: 0.6; }
  .row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3) var(--space-5); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); margin: 0; }
  .row:last-child { border-bottom: 0; }
  .empty { color: var(--muted); font-size: 14px; }
  .acts { display: flex; gap: var(--space-1); margin-left: auto; }
  .tname { display: flex; align-items: baseline; gap: var(--space-3); }
  .lists { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-4); }
  .desc.failed { color: var(--bad-text); }
  .warn-t { color: var(--warn-text); }
  .bad-t { color: var(--bad-text); }
  .runswrap { flex-basis: 100%; }
  .sugg { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
  .sugg li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); font-size: 13.5px;
    padding: var(--space-2) var(--space-3); border-radius: 8px; background: color-mix(in oklch, var(--accent) 7%, var(--surface)); }
  .busy {
    display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4); padding: var(--space-3) var(--space-4);
    border-radius: 10px; background: color-mix(in oklch, var(--warn) 10%, var(--surface)); border: 1px solid color-mix(in oklch, var(--warn) 35%, var(--line));
    color: var(--warn-text); font-weight: 500; font-size: 14px;
  }
  .spin { width: 12px; height: 12px; border-radius: 50%; border: 2px solid color-mix(in oklch, var(--warn) 30%, transparent); border-top-color: var(--warn); flex: none; }
  @media (prefers-reduced-motion: no-preference) { .spin { animation: spin 0.9s linear infinite; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  .tag.live { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .list { list-style: none; margin: 0; padding: 0; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
  .list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); }
  .list li:last-child { border-bottom: 0; }
  .list li .btn.quiet { min-height: 26px; }
  .emptyst { padding: var(--space-5); display: grid; gap: var(--space-3); }
  .emptyst p { margin: 0; color: var(--muted); max-width: 64ch; }
  .examples { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--space-2); }
  .ex {
    display: grid; gap: 2px; text-align: left; font: inherit; color: var(--ink); background: var(--surface); cursor: pointer;
    border: 1px solid var(--line); border-radius: 10px; padding: var(--space-3);
    transition: border-color 120ms var(--ease), background-color 120ms var(--ease);
  }
  .ex:hover:not(:disabled) { border-color: var(--accent); background: color-mix(in oklch, var(--accent) 5%, var(--surface)); }
  .exl { font-weight: 600; font-size: 14px; }
  .exh { font-size: 12.5px; color: var(--muted); }
  .ex code { font-size: 11.5px; color: var(--muted); margin-top: 4px; }
  .days { display: grid; gap: var(--space-2); }
  .day { margin: var(--space-3) 0 0; font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
  .day:first-child { margin-top: 0; }
  .deploys li { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: var(--space-3); }
  .deploys li.islive { background: color-mix(in oklch, var(--ok) 7%, var(--surface)); }
  .deploys li.failed { background: color-mix(in oklch, var(--bad) 4%, var(--surface)); }
  .deploys li:first-child { border-radius: 12px 12px 0 0; }
  .deploys li:last-child { border-radius: 0 0 12px 12px; }
  .deploys li:only-child { border-radius: 12px; }
  .dmain { min-width: 0; display: grid; gap: 2px; }
  .dmain a { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dsub { display: flex; flex-wrap: wrap; gap: 4px var(--space-3); font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .dsub code { font-size: 12px; }
  .dacts { display: flex; align-items: center; gap: var(--space-2); }
  /* "Volver aquí" solo donde estás (mouse o teclado): la lista no se llena de botones iguales. */
  @media (hover: hover) {
    .deploys .roll { opacity: 0; transition: opacity 120ms var(--ease); }
    .deploys li:hover .roll, .deploys li:focus-within .roll { opacity: 1; }
  }
  .grow { flex: 1; min-width: 200px; }
  .sched { font-size: 12.5px; color: var(--muted); }
  .cmd { display: block; font-size: 12.5px; margin-top: 4px; color: var(--muted); overflow-wrap: anywhere; }
  .when { display: grid; grid-template-columns: auto auto; gap: 2px var(--space-3); margin: 0; font-size: 13.5px; }
  .when dt { color: var(--muted); }
  .when dd { margin: 0; }
  @media (max-width: 820px) {
    .kv { grid-template-columns: 96px minmax(0, 1fr); }
  }
  .dbseg { margin-bottom: var(--space-3); }
  .setwrap { display: grid; grid-template-columns: minmax(0, 1fr) 180px; gap: var(--space-6); align-items: start; margin-top: var(--space-5); }
  .setmain > :global(.sset) { margin-top: var(--space-6); scroll-margin-top: 72px; }
  .setmain > :global(.sset.first) { margin-top: var(--space-4); }
  .sfilter { display: flex; align-items: center; gap: 8px; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--muted); }
  .sfilter input { flex: 1; font: 14px var(--sans); color: var(--ink); background: transparent; border: 0; padding: 9px 0; outline: none; }
  .sfilter:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent) 22%, transparent); }
  .toc { position: sticky; top: 72px; display: grid; gap: 2px; }
  .toch { margin: 0 0 6px; font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
  .toc button { text-align: left; font: 13.5px var(--sans); color: var(--muted); background: none; border: 0; border-radius: 6px; padding: 5px 10px; cursor: pointer; }
  .toc button:hover { color: var(--ink); background: var(--sunken); }
  .toc button.on { color: var(--ink); font-weight: 600; background: color-mix(in oklch, var(--accent) 9%, transparent); }
  @media (max-width: 1100px) { .setwrap { grid-template-columns: minmax(0, 1fr); } .toc { display: none; } }
</style>
