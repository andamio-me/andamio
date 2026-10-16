<!--
  Servicios: el PostgreSQL, el Redis y el MariaDB (si alguna app lo usa) que comparten tus apps. Cuánto usan ahora (memoria, CPU,
  conexiones, claves), qué usa cada app y su configuración, que se cambia aquí (andamio
  servicios). Cambiarla reinicia el servicio: una ventana lo dice antes de correr nada.
  Los límites de cada app (conexiones, tiempo por consulta) viven en los Ajustes de la app.
-->
<script lang="ts">
  import PageHead from "./PageHead.svelte";
  import Modal from "./Modal.svelte";
  import Skeleton from "./Skeleton.svelte";
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { bytes } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { commandFor, job } from "../lib/job.svelte";

  type Svc = "postgres" | "redis" | "mariadb";
  let data = $state<api.DataServices | null>(null);
  let error = $state("");
  let draft = $state<Record<Svc, Record<string, string>>>({ postgres: {}, redis: {}, mariadb: {} });

  async function load() {
    try {
      data = await api.dataServices();
      error = data.error;
      draft = { postgres: { ...data.config.postgres }, redis: { ...data.config.redis }, mariadb: { ...data.config.mariadb } };
    } catch (e) {
      error = String((e as Error).message);
    }
  }
  onMount(() => void load());

  const live = $derived(data?.live ?? null);
  const pg = $derived(live?.postgres ?? null);
  const rd = $derived(live?.redis ?? null);
  const md = $derived(live?.mariadb ?? null);
  const mdOn = $derived(Boolean(data?.mariadb_needed || md?.up));
  const mb = (v: string) => Number(v.slice(0, -1)) * (v.slice(-1).toLowerCase() === "g" ? 1024 : 1);
  const toBytes = (v: string) => mb(v) * 1048576;
  const pct = (a: number, b: number) => (b > 0 ? Math.min(100, Math.round((a / b) * 100)) : 0);
  const tone = (p: number) => (p >= 90 ? "bad" : p >= 75 ? "warn" : "ok");

  // Lo que cambiaste en el formulario de cada servicio, y si sirve.
  const changed = (s: Svc) => (data ? Object.entries(draft[s]).filter(([k, v]) => v !== data!.config[s][k]) : []);
  const pgChanged = $derived(changed("postgres"));
  const rdChanged = $derived(changed("redis"));
  const mdChanged = $derived(changed("mariadb"));
  const RX: Record<string, RegExp> = {
    mem: /^[1-9][0-9]{0,5}[mg]$/, cpus: /^[0-9]+(\.[0-9]+)?$/, max_connections: /^[0-9]{2,4}$/, work_mem: /^[1-9][0-9]{0,3}(kB|MB)$/,
  };
  function problem(s: Svc): string {
    if (!data) return "";
    const d = draft[s];
    for (const [k, v] of Object.entries(d)) {
      if (RX[k] && !RX[k].test(v)) return t().svBad(k);
    }
    if (s === "postgres" && mb(d.mem!) < 256) return t().svPgMin;
    if (s === "redis" && mb(d.mem!) < 32) return t().svRedisMin;
    if (s === "mariadb" && mb(d.mem!) < 256) return t().svMdMin;
    if (s !== "redis" && (Number(d.max_connections) < 20 || Number(d.max_connections) > 1000)) return t().svConnsRange;
    if (live?.server) {
      if (Number(d.cpus) > live.server.cpus || Number(d.cpus) < 0.1) return t().svCpuMax(live.server.cpus);
      const need = mb(draft.postgres.mem!) + Math.floor(mb(draft.redis.mem!) * 1.5) + (data.mariadb_needed ? mb(draft.mariadb.mem!) : 0);
      const room = Math.floor((live.server.mem_total / 1048576) * 0.7);
      if (need > room) return t().svMemRoom(need, room);
    }
    return "";
  }
  const pgProblem = $derived(problem("postgres"));
  const rdProblem = $derived(problem("redis"));
  const mdProblem = $derived(problem("mariadb"));

  // Aplicar: una ventana dice qué cambia y que el servicio se reinicia; después corre el comando.
  let confirmFor = $state<Svc | null>(null);
  let confirmOpen = $state(false);
  const action = (s: Svc): api.Action => ({ action: "services", service: s, set: Object.fromEntries(changed(s)) });
  function ask(s: Svc) {
    confirmFor = s;
    confirmOpen = true;
  }
  function apply() {
    if (!confirmFor) return;
    confirmOpen = false;
    job.arm(action(confirmFor), () => void load());
    void job.run();
  }

  const pgConns = $derived(Object.values(pg?.conns ?? {}).reduce((a, b) => a + b, 0));
  const mdConns = $derived(Object.values(md?.conns ?? {}).reduce((a, b) => a + b, 0));
  const SVC_NAME: Record<Svc, string> = { postgres: "PostgreSQL", redis: "Redis", mariadb: "MariaDB" };
  const LABEL: Record<string, () => string> = {
    mem: () => t().svMem, cpus: () => "CPU", max_connections: () => t().svMaxConns, work_mem: () => t().svWorkMem,
    policy: () => t().svPolicy, engine: () => t().svEngine,
  };
  const ENGINE: Record<string, string> = { redis: "Redis", valkey: "Valkey", dragonfly: "Dragonfly" };
  const engineName = $derived(ENGINE[rd?.engine ?? data?.config.redis.engine ?? "redis"] ?? "Redis");
  // Dragonfly no tiene las políticas volatile-*: al elegirlo, si estaba en una, vuelve a noeviction.
  $effect(() => {
    if (data && draft.redis.engine === "dragonfly" && !data.dragonfly_policies.includes(draft.redis.policy ?? "")) draft.redis.policy = "noeviction";
  });
  const policies = $derived(draft.redis.engine === "dragonfly" ? data?.dragonfly_policies ?? [] : data?.policies ?? []);
  const appsWith = (k: "db" | "redis" | "mysql") => Object.entries(data?.apps ?? {}).filter(([, a]) => a[k]);
  const fmtLimit = (n: number) => (n ? String(n) : t().svNoLimit);
  const fmtTimeout = (v: string) => (v && v !== "0" ? v : t().svNoLimit);
</script>

<PageHead title={t().svTitle} desc={t().svPageDesc}>
  {#snippet actions()}
    <button type="button" class="btn quiet" onclick={() => void load()} disabled={!data}>{t().refresh}</button>
  {/snippet}
</PageHead>

{#if error}<p class="banner" role="alert">{error}</p>{/if}

{#if !data}
  <Skeleton kind="detail" />
{:else}
  <!-- PostgreSQL -->
  <section aria-labelledby="sv-pg" class="svc">
    <div class="shead">
      <div>
        <h2 id="sv-pg"><span class={`dot ${pg?.up ? "ok" : live ? "bad" : ""}`} aria-hidden="true"></span>PostgreSQL {#if pg?.version}<span class="ver">{pg.version}</span>{/if}</h2>
        <p class="desc">{t().svPgDesc}</p>
      </div>
    </div>

    <div class="meters">
      {@render meter(t().svMem, pg?.mem_used ?? null, toBytes(data.config.postgres.mem!), bytes)}
      {@render meter(t().svConns, pg?.conns ? pgConns : null, Number(data.config.postgres.max_connections), String)}
      <div class="meter">
        <span class="mlbl">CPU</span>
        <span class="mval">{pg?.up ? `${pg.cpu?.toFixed(1)} %` : "—"}</span>
        <span class="msub">{t().svCpuOf(data.config.postgres.cpus!)}</span>
      </div>
    </div>

    {@render dbApps("db", pg)}

    {@render form("postgres", ["mem", "cpus", "max_connections", "work_mem"], pgChanged, pgProblem)}
  </section>

  <!-- Redis (o Valkey, o Dragonfly: el mismo protocolo) -->
  <section aria-labelledby="sv-rd" class="svc">
    <div class="shead">
      <div>
        <h2 id="sv-rd"><span class={`dot ${rd?.up ? "ok" : live ? "bad" : ""}`} aria-hidden="true"></span>{engineName} {#if rd?.version}<span class="ver">{rd.version}</span>{/if}</h2>
        <p class="desc">{t().svRedisDesc}</p>
      </div>
    </div>

    <div class="meters">
      {@render meter(t().svData, rd?.data_used ?? null, toBytes(data.config.redis.mem!), bytes)}
      <div class="meter">
        <span class="mlbl">{t().svKeys}</span>
        <span class="mval">{rd?.keys ?? "—"}</span>
        <span class="msub">{rd?.evicted ? t().svEvicted(rd.evicted) : t().svNoEvicted}</span>
      </div>
      <div class="meter">
        <span class="mlbl">CPU</span>
        <span class="mval">{rd?.up ? `${rd.cpu?.toFixed(1)} %` : "—"}</span>
        <span class="msub">{t().svCpuOf(data.config.redis.cpus!)}</span>
      </div>
    </div>

    {#if appsWith("redis").length}
      <div class="box tablebox">
        <table>
          <thead><tr><th>App</th><th>{t().svClients}</th><th>{t().svKeyPrefix}</th></tr></thead>
          <tbody>
            {#each appsWith("redis") as [name] (name)}
              <tr>
                <td><a href={`#/app/${name}`}>{name}</a></td>
                <td class="num">{rd?.engine === "dragonfly" ? "—" : (rd?.clients?.[name] ?? 0)}</td>
                <td><code>{name}:*</code></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    {@render form("redis", ["engine", "mem", "cpus", "policy"], rdChanged, rdProblem)}
  </section>

  <!-- MariaDB: solo si alguna app la usa -->
  <section aria-labelledby="sv-md" class="svc">
    <div class="shead">
      <div>
        <h2 id="sv-md"><span class={`dot ${md?.up ? "ok" : mdOn && live ? "bad" : ""}`} aria-hidden="true"></span>MariaDB {#if md?.version}<span class="ver">{md.version}</span>{/if}</h2>
        <p class="desc">{t().svMdDesc}</p>
      </div>
    </div>
    {#if mdOn}
      <div class="meters">
        {@render meter(t().svMem, md?.mem_used ?? null, toBytes(data.config.mariadb.mem!), bytes)}
        {@render meter(t().svConns, md?.conns ? mdConns : null, Number(data.config.mariadb.max_connections), String)}
        <div class="meter">
          <span class="mlbl">CPU</span>
          <span class="mval">{md?.up ? `${md.cpu?.toFixed(1)} %` : "—"}</span>
          <span class="msub">{t().svCpuOf(data.config.mariadb.cpus!)}</span>
        </div>
      </div>
      {@render dbApps("mysql", md)}
    {:else}
      <p class="off">{t().svMdOff}</p>
    {/if}
    {@render form("mariadb", ["mem", "cpus", "max_connections"], mdChanged, mdProblem)}
  </section>
{/if}

{#snippet dbApps(key: "db" | "mysql", live: { conns?: Record<string, number>; sizes?: Record<string, number>; apps?: Record<string, { role: string; db: string }> } | null)}
  {#if appsWith(key).length}
    <div class="box tablebox">
      <table>
        <thead><tr><th>App</th><th>{t().svSize}</th><th>{t().svConnsNow}</th><th>{t().svConnLimit}</th><th>{t().svTimeout}</th><th><span class="sr-only">{t().settings}</span></th></tr></thead>
        <tbody>
          {#each appsWith(key) as [name, a] (name)}
            {@const r = live?.apps?.[name]}
            <tr>
              <td><a href={`#/app/${name}`}>{name}</a></td>
              <td class="num">{r && live?.sizes?.[r.db] !== undefined ? bytes(live.sizes[r.db]!) : "—"}</td>
              <td class="num">{r ? (live?.conns?.[r.role] ?? 0) : "—"}</td>
              <td class="num" class:muted={!a.db_connections}>{fmtLimit(a.db_connections)}</td>
              <td class="num" class:muted={a.db_timeout === "0"}>{fmtTimeout(a.db_timeout)}</td>
              <td class="end"><a class="btn small quiet" href={`#/app/${name}/settings`}>{t().svEditLimits}</a></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/snippet}

{#snippet meter(label: string, used: number | null, limit: number, fmt: (n: number) => string)}
  {@const p = used === null ? 0 : pct(used, limit)}
  <div class="meter">
    <span class="mlbl">{label}</span>
    <span class="mval">{used === null ? "—" : fmt(used)} <span class="of">/ {fmt(limit)}</span></span>
    <span class={`bar ${tone(p)}`} role="meter" aria-label={label} aria-valuemin="0" aria-valuemax="100" aria-valuenow={p}><span style:width={`${p}%`}></span></span>
  </div>
{/snippet}

{#snippet form(s: Svc, keys: string[], changes: [string, string][], bad: string)}
  <details class="cfg" open={changes.length > 0}>
    <summary>{t().svConfig} <span class="cur">{keys.map((k) => data!.config[s][k]).join(" · ")}</span></summary>
    <div class="fields">
      {#each keys as k (k)}
        <label class="f">
          <span class="lbl">{LABEL[k]?.()}</span>
          {#if k === "policy"}
            <select bind:value={draft[s][k]} disabled={job.locked}>
              {#each policies as p (p)}<option value={p}>{p}</option>{/each}
            </select>
            <span class="help" class:warn={draft[s][k] !== "noeviction"}>{t().svPolicyHint(draft[s][k]!)}</span>
          {:else if k === "engine"}
            <select bind:value={draft[s][k]} disabled={job.locked}>
              {#each data!.engines as e (e)}<option value={e}>{ENGINE[e] ?? e}</option>{/each}
            </select>
            <span class="help" class:warn={draft[s][k] === "dragonfly"}>{t().svEngineHint(draft[s][k]!)}</span>
          {:else}
            <input bind:value={draft[s][k]} class="mono" spellcheck="false" autocomplete="off" disabled={job.locked}
              aria-invalid={RX[k] && !RX[k].test(draft[s][k] ?? "") ? "true" : undefined} />
            <span class="help">{t().svHint(s, k, data!.defaults[s][k]!)}</span>
          {/if}
        </label>
      {/each}
    </div>
    <div class="foot">
      {#if bad}<span class="help error">{bad}</span>{:else if changes.length}<span class="help">{t().svRestartNote}</span>{/if}
      <span class="spacer"></span>
      {#if changes.length}<button type="button" class="btn quiet small" onclick={() => (draft[s] = { ...data!.config[s] })}>{t().cancel}</button>{/if}
      <button type="button" class="btn primary small" disabled={!changes.length || Boolean(bad) || job.locked} onclick={() => ask(s)}>{t().svApply}</button>
    </div>
  </details>
{/snippet}

<Modal bind:open={confirmOpen} id="sv-confirm" alert={t().svRestartAlert(SVC_NAME[confirmFor ?? "postgres"])}>
  {#snippet heading()}{t().svConfirmTitle(SVC_NAME[confirmFor ?? "postgres"])}{/snippet}
  {#if confirmFor && data}
    <div class="m-body">
    <ul class="clist">
      {#each changed(confirmFor) as [k, v] (k)}
        <li><span>{LABEL[k]?.()}</span> <code>{data.config[confirmFor][k]}</code> → <code>{v}</code></li>
      {/each}
    </ul>
    {#if confirmFor === "redis" && draft.redis.engine !== data.config.redis.engine}
      <p class="mnote">{t().svEngineCopy(ENGINE[data.config.redis.engine!] ?? "", ENGINE[draft.redis.engine!] ?? "")}</p>
      {#if draft.redis.engine === "dragonfly"}<p class="mnote warn">{t().svDragonflyLoss}</p>{/if}
    {/if}
    <p class="cmd"><code>{commandFor(action(confirmFor))}</code></p>
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (confirmOpen = false)}>{t().cancel}</button>
      <button type="button" class="btn primary" onclick={apply}>{t().svApplyNow}</button>
    </div>
  {/if}
</Modal>

<style>
  .svc { margin-top: var(--space-6); }
  .svc:first-of-type { margin-top: 0; }
  h2 { display: flex; align-items: center; gap: 10px; }
  .ver { font: 500 12.5px var(--mono); color: var(--muted); text-transform: none; letter-spacing: 0; }
  .meters { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-5); margin: var(--space-2) 0 var(--space-4); }
  .meter { display: grid; gap: 4px; align-content: start; }
  .mlbl { font-size: 13px; color: var(--muted); }
  .mval { font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
  .of { font-size: 14px; font-weight: 400; color: var(--muted); }
  .msub { font-size: 13px; color: var(--muted); }
  .bar { display: block; height: 6px; border-radius: 999px; background: var(--sunken); overflow: hidden; margin-top: 2px; }
  .bar span { display: block; height: 100%; border-radius: inherit; background: var(--ok); transition: width 500ms var(--ease); }
  .bar.warn span { background: var(--warn); }
  .bar.bad span { background: var(--bad); }
  .tablebox { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; font-weight: 500; font-size: 12.5px; color: var(--muted); padding: 10px var(--space-4); border-bottom: 1px solid var(--line); white-space: nowrap; }
  td { padding: 8px var(--space-4); border-bottom: 1px solid var(--line); }
  tr:last-child td { border-bottom: 0; }
  .num { font-variant-numeric: tabular-nums; }
  .muted { color: var(--muted); }
  .off { margin: var(--space-2) 0 0; font-size: 14px; color: var(--muted); }
  .end { text-align: right; }
  .cfg { margin-top: var(--space-3); border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
  .cfg summary { cursor: pointer; padding: var(--space-3) var(--space-4); font-weight: 500; display: flex; gap: var(--space-3); align-items: baseline; flex-wrap: wrap; }
  .cfg .cur { font: 13px var(--mono); color: var(--muted); font-weight: 400; }
  .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-4) var(--space-5); padding: var(--space-2) var(--space-4) var(--space-4); border-top: 1px solid var(--line); }
  .f { display: grid; gap: 6px; align-content: start; }
  .lbl { font-size: 13.5px; color: var(--muted); }
  .f input, .f select {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px;
  }
  .f input:focus-visible, .f select:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 22%, transparent); border-color: var(--accent); }
  .f input[aria-invalid="true"] { border-color: var(--bad); }
  .help { font-size: 12.5px; color: var(--muted); }
  .help.warn { color: var(--warn-text); }
  .help.error { color: var(--bad-text); }
  .foot { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); padding: var(--space-3) var(--space-4); border-top: 1px solid var(--line); background: var(--sunken); border-radius: 0 0 12px 12px; }
  .spacer { flex: 1; }
  .clist { list-style: none; margin: 0 0 var(--space-3); padding: 0; display: grid; gap: 6px; }
  .clist span { color: var(--muted); }
  .mnote { margin: 0; font-size: 14px; color: var(--muted); }
  .mnote.warn { color: var(--warn-text); }
  .cmd code { font-size: 12.5px; padding: 6px 10px; border-radius: 6px; background: var(--sunken); display: inline-block; overflow-wrap: anywhere; }
  @media (max-width: 700px) { .meters { grid-template-columns: 1fr; } }
</style>
