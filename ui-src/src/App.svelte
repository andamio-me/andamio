<!--
  Panel de andamio (andamio ui). Inicio: el plano vivo de tu servidor y tus apps. Detalle: una
  app, con sus acciones. Los datos vienen de bin/andamio (tus archivos y el servidor por SSH).
-->
<script lang="ts">
  import { onMount, tick as nextFrame } from "svelte";
  import { dirty } from "./lib/guard.svelte";
  import { onFinished } from "./lib/job.svelte";
  import Modal from "./components/Modal.svelte";
  import Skeleton from "./components/Skeleton.svelte";
  import JobPill from "./components/JobPill.svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import { parseApp } from "./lib/nav";
  import { cachedApp, fetchApp } from "./lib/cache.svelte";
  import * as api from "./lib/api";
  import { ago, since, status } from "./lib/format";
  import { job } from "./lib/job.svelte";
  import { setLang, t } from "./lib/i18n.svelte";
  import AppDetail from "./components/AppDetail.svelte";
  import AppsTable from "./components/AppsTable.svelte";
  import Backups from "./components/Backups.svelte";
  import Services from "./components/Services.svelte";
  import History from "./components/History.svelte";
  import Palette from "./components/Palette.svelte";
  import Settings from "./components/Settings.svelte";
  import Toasts from "./components/Toasts.svelte";
  import Usage from "./components/Usage.svelte";
  import { notices } from "./lib/notices.svelte";
  import Mark from "./components/Mark.svelte";
  import NewApp from "./components/NewApp.svelte";
  import Plan from "./components/Plan.svelte";
  import Terminal from "./components/Terminal.svelte";

  let meta = $state<api.Meta | null>(null);
  let route = $state(location.hash);
  let home = $state<api.AppsData | null>(null);
  let detail = $state<api.AppData | null>(null);
  let error = $state("");
  let loading = $state(false);
  let loadedAt = $state(0);
  let tick = $state(0);
  // Los deploys recientes los trae el vigía de avisos (uno solo, para no preguntarle dos veces a GitHub).
  const recent = $derived(notices.deploys?.slice(0, 8) ?? null);
  // Disponibilidad y certificados para el inicio (aparte: no frenan el plano).
  let avail = $state<api.Availability["apps"]>({});
  let sparks = $state<api.Sparks | null>(null);
  let certs = $state<Record<string, api.Cert[]>>({});
  const loadExtras = () => {
    api.availability().then((r) => (avail = r.apps)).catch(() => {});
    api.sparks().then((r) => (sparks = r)).catch(() => {});
    api.certs().then((r) => (certs = r.apps)).catch(() => {});
  };

  // Lo que necesita atención, arriba del plano: solo aparece si hay algo.
  const problems = $derived.by(() => {
    if (!home || home.error) return [];
    const s = t();
    const out: { what: string; fix: string; href?: string }[] = [];
    for (const a of home.apps) {
      const st = status(a);
      if (!a.stopped && st.tone === "bad") out.push({ what: s.appDown(a.name, st.text), fix: s.appDownFix(a.name), href: `#/app/${a.name}` });
    }
    const sv = home.server;
    if (sv && sv.disk_total && sv.disk_used / sv.disk_total >= 0.85) {
      out.push({ what: s.diskFull(Math.round((sv.disk_used / sv.disk_total) * 100)), fix: s.diskFix });
    }
    const b = home.platform?.backups;
    if (b?.configured && b.last && b.result && b.result !== "success") out.push({ what: s.backupBad, fix: s.backupFix });
    if (home.security?.fail) out.push({ what: s.secBad(home.security.fail), fix: s.secFix });
    for (const [app, list] of Object.entries(certs)) {
      for (const c of list) {
        if (!c.ok) out.push({ what: s.certProblem(c.host), fix: c.error ?? "", href: `#/app/${app}` });
        else if ((c.days ?? 99) < 14) out.push({ what: s.certSoon(c.host, c.days ?? 0), fix: s.certSoonFix, href: `#/app/${app}` });
      }
    }
    return out;
  });

  const checkSecurity = () => job.arm({ action: "estado" }, () => void load());

  const appRoute = $derived(parseApp(route));
  const appName = $derived(appRoute?.app ?? null);
  const section = $derived(appRoute?.section ?? null);
  // Qué hay que cargar: cambiar de sección dentro de una app no vuelve a traer la app.
  const pageKey = $derived(appName ? `app:${appName}` : route);

  // El sidebar: contraído (se recuerda en este navegador) y, en pantallas chicas, abierto o no.
  const SIDEBAR_KEY = "andamio.sidebar";
  let collapsed = $state((() => { try { return localStorage.getItem(SIDEBAR_KEY) === "collapsed"; } catch { return false; } })());
  $effect(() => { try { localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "open"); } catch { /* sin almacenamiento */ } });
  let sideOpen = $state(false);
  let narrow = $state(matchMedia("(max-width: 900px)").matches);
  // Las apps del sidebar (su estado): las mismas del inicio, al día cada minuto en cualquier página.
  const sideApps = $derived(home?.apps ?? []);
  const failedDeploys = $derived.by(() => {
    const seen = new Set<string>(), bad = new Set<string>();
    for (const d of notices.deploys ?? []) {
      if (!d.app || seen.has(d.app)) continue;
      seen.add(d.app);
      if (d.status === "completed" && d.conclusion === "failure") bad.add(d.app);
    }
    return bad;
  });
  const backupBad = $derived(Boolean(home?.platform?.backups?.configured && home.platform.backups.result && home.platform.backups.result !== "success" && home.platform.backups.last));
  const isNew = $derived(route === "#/new");
  const backupsRoute = $derived(route.match(/^#\/backups(?:\/([a-z0-9-]+))?$/));
  const historyRoute = $derived(route.match(/^#\/history(?:\/([a-z0-9-]+))?$/));
  const isSettings = $derived(route === "#/settings");
  const isServices = $derived(route === "#/services");
  let paletteOpen = $state(false);
  // Salir con cambios sin aplicar: a dónde ibas (la ventana pregunta antes).
  let leaving = $state<string | null>(null);
  let leaveOpen = $state(false);
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);

  // Scroll: al volver atrás, donde estabas; al ir a una página nueva, arriba.
  const scrolls = new Map<string, number>();
  const visited: string[] = [location.hash];
  let restoreTo: number | null = null;

  async function load() {
    loading = true;
    error = "";
    try {
      if (isNew || backupsRoute || historyRoute || isSettings || isServices) {
        if (!home) api.apps().then((h) => (home = h)).catch(() => {});   // el sidebar necesita las apps
        return;   // estas páginas traen lo suyo
      } else if (appName) {
        // Si ya se vio (o se precargó al pasar el mouse), está en pantalla: esto lo pone al día.
        detail = await fetchApp(appName, 4_000);
        if (!home) api.apps().then((h) => (home = h)).catch(() => {});   // el sidebar necesita las apps
      } else {
        home = await api.apps();
        loadExtras();
      }
      loadedAt = Date.now();
    } catch (e) {
      error = e instanceof api.ApiError && e.status === 404 ? t().noSuch : String((e as Error).message);
      if (appName) detail = null;
    } finally {
      loading = false;
      if (restoreTo !== null) {
        const y = restoreTo;
        restoreTo = null;
        await nextFrame();
        window.scrollTo(0, y);
      }
    }
  }

  onMount(() => {
    let current = location.hash;
    let bypass = false;
    const onHash = () => {
      // Una acción larga corriendo (la página está bloqueada): ni el botón Atrás la deja a medias.
      // Con cambios sin aplicar: se vuelve a esta página y se pregunta.
      // (Minimizada, se puede navegar y mirar: las acciones siguen bloqueadas hasta que termine.)
      // Cambiar de sección dentro de la misma app no pierde nada (los cambios pendientes viven en la app).
      const sameApp = parseApp(current)?.app !== undefined && parseApp(current)?.app === parseApp(location.hash)?.app;
      if (!bypass && ((job.critical && job.locked && !job.minimized) || (dirty() && !sameApp))) {
        const target = location.hash;
        history.replaceState(null, "", current || "#/");
        if (!(job.critical && !job.minimized)) {
          leaving = target;
          leaveOpen = true;
        }
        return;
      }
      bypass = false;
      scrolls.set(current, window.scrollY);
      const back = visited.length > 1 && visited[visited.length - 2] === location.hash;
      if (back) visited.pop(); else visited.push(location.hash);
      current = location.hash;
      route = location.hash;
      const next = parseApp(location.hash)?.app;
      if (!sameApp) detail = next ? cachedApp(next) : null;
      sideOpen = false;
      restoreTo = back ? (scrolls.get(location.hash) ?? 0) : null;
      window.scrollTo(0, 0);
      // Con lector de pantalla o teclado: la página nueva empieza en su contenido, no en el link que tocaste.
      document.getElementById("main")?.focus({ preventScroll: true });
    };
    leaveNow = () => {
      leaveOpen = false;
      if (leaving === null) return;
      bypass = true;
      location.hash = leaving;
      leaving = null;
    };
    const onUnload = (e: BeforeUnloadEvent) => { if (dirty()) e.preventDefault(); };
    window.addEventListener("beforeunload", onUnload);
    // Al terminar cualquier acción, los datos de la página se ponen al día.
    onFinished(() => void load());
    window.addEventListener("hashchange", onHash);
    // Ctrl+K (⌘K en Mac): ir a cualquier cosa escribiendo.
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k" && !(job.critical && job.locked && !job.minimized)) {
        e.preventDefault();
        paletteOpen = !paletteOpen;
      }
    };
    window.addEventListener("keydown", onKey);
    // Tocar un botón bloqueado mientras corre una acción: la terminal (o su pastilla) explica por qué.
    const onPoint = (e: PointerEvent) => {
      if (job.locked && (e.target as Element | null)?.closest?.("button:disabled")) job.nudge();
    };
    document.addEventListener("pointerdown", onPoint, true);
    const clock = setInterval(() => (tick += 1), 15000);
    // La lista se pone al día sola cada 30 s mientras la miras (el detalle tiene sus logs en vivo).
    const refresh = setInterval(() => {
      if (!document.hidden && !appName && !loading) void load();
    }, 30000);
    // En otras páginas, el estado de las apps (para el sidebar) cada minuto.
    const sideRefresh = setInterval(() => {
      if (!document.hidden && pageKey !== "#/" && pageKey !== "" && pageKey !== "#") api.apps().then((h) => (home = h)).catch(() => {});
    }, 60000);
    const mq = matchMedia("(max-width: 900px)");
    const onMq = () => { narrow = mq.matches; if (!narrow) sideOpen = false; };
    mq.addEventListener("change", onMq);
    api.meta().then((m) => {
      meta = m;
      setLang(m.lang);
      document.documentElement.lang = m.lang;
      document.title = `andamio · ${m.domain}`;
      notices.start();
      // Si recargaste mientras una acción corría: se vuelve a mostrar, con lo que ya salió.
      api.currentJob().then((j) => { if (j.id) job.attach(j.id, j.command!, j.action ?? "", j.state ?? "running"); }).catch(() => {});
    }).catch((e) => (error = String(e.message)));
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("beforeunload", onUnload);
      document.removeEventListener("pointerdown", onPoint, true);
      clearInterval(clock);
      clearInterval(refresh);
      clearInterval(sideRefresh);
      mq.removeEventListener("change", onMq);
    };
  });

  // Cargar cada vez que cambia la vista (una vez que hay sesión).
  $effect(() => {
    void pageKey;
    if (meta) void load();
  });

  let leaveNow = () => {};

  const stamp = $derived.by(() => {
    void tick;
    return loadedAt ? `${t().updated} ${ago((Date.now() - loadedAt) / 1000)}` : "";
  });
</script>

<a class="skip" href="#main" onclick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>{t().skip}</a>
<div class="progress" class:on={loading} aria-hidden="true"></div>

<div class="shell">
<Sidebar {meta} apps={sideApps} {route} current={appName} {section} {failedDeploys} {backupBad}
  collapsed={collapsed && !narrow} bind:open={sideOpen} onfind={() => (paletteOpen = true)}
  oncollapse={(v: boolean) => (collapsed = v)} />
<div class="content">
<header class="top">
  <div class="inner">
    <button type="button" class="menu" onclick={() => (sideOpen = true)} aria-label={t().menu} aria-expanded={sideOpen}>
      <svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M2.5 4h11M2.5 8h11M2.5 12h11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
    </button>
    <a class="brand" href="#/" aria-label="andamio"><Mark size={18} /><span>andamio</span></a>
    <span class="spacer"></span>
    <span class="stamp" aria-live="off">{stamp}</span>
    <button type="button" class="btn small refresh" onclick={() => { void load(); notices.refresh(); }} disabled={loading} aria-busy={loading}>
      <svg class:spin={loading} viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M13.5 8a5.5 5.5 0 11-1.6-3.9M13.5 2.5v3h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
      {t().refresh}
    </button>
  </div>
</header>

<main id="main" tabindex="-1">
  {#if error && !(appName ? detail : home)}
    <p class="banner" role="alert">{error}</p>
  {/if}

  {#if isNew}
    <NewApp {meta} />
  {:else if backupsRoute}
    <Backups preset={backupsRoute[1] ?? ""} />
  {:else if historyRoute}
    {#key historyRoute[1]}<History app={historyRoute[1] ?? ""} />{/key}
  {:else if isSettings}
    <Settings />
  {:else if isServices}
    <Services />
  {:else if appName}
    {#if detail}
      <div class="fresh" class:stale={loading}><AppDetail data={detail} {meta} reload={load} section={section ?? "overview"} /></div>
    {:else if !error}
      <Skeleton kind="detail" />
    {/if}
  {:else}
    {@const offline = Boolean(home?.error)}
    <h1 class="sr-only">{t().homeTitle(meta?.domain ?? "")}</h1>
    {#if home?.error}<p class="banner" role="status">{t().serverErr}: {home.error}</p>{/if}
    {#if problems.length}
      <section class="attention" aria-labelledby="att-title">
        <h2 id="att-title">{t().attention}</h2>
        <ul>
          {#each problems as p, i (i)}
            <li>
              <span class="dot bad"></span>
              <div>
                {#if p.href}<a href={p.href}><strong>{p.what}</strong></a>{:else}<strong>{p.what}</strong>{/if}
                <div class="fix">{p.fix}</div>
              </div>
            </li>
          {/each}
        </ul>
      </section>
    {/if}
    <Plan apps={home?.apps ?? []} server={home?.server ?? null} domain={meta?.domain ?? ""} alias={meta?.server ?? ""}
      loading={!home} {offline} platform={home?.platform ?? null} security={home?.security ?? null} oncheck={checkSecurity} />
    {#if home && !offline}
      <Usage id="server-usage" heading={t().serverUsage} desc={t().serverUsageDesc} height={110}
        memLimit={home.server?.mem_total ?? null} />
    {/if}
    <section class="apps" aria-labelledby="apps-title">
      <div class="shead">
        <h2 id="apps-title">{t().apps}</h2>
        <a class="btn small" href="#/new">{t().newApp}</a>
      </div>
      {#if home}<AppsTable apps={home.apps} {offline} {avail} {sparks} />{:else}<Skeleton rows={2} />{/if}
    </section>
    <section class="apps" aria-labelledby="recent-title">
      <div class="shead"><div><h2 id="recent-title">{t().recent}</h2><p class="desc">{t().recentDesc}</p></div></div>
      {#if recent === null}
        <Skeleton rows={4} />
      {:else if recent.length}
        <ul class="box recent">
          {#each recent as d (d.id)}
            {@const done = d.status === "completed"}
            {@const ok = done && d.conclusion === "success"}
            <li>
              <span class={`dot ${!done ? "warn" : ok ? "ok" : "bad"}`} aria-label={!done ? t().inProgress : ok ? t().deployOk : d.conclusion}></span>
              <a class="app" href={`#/app/${d.app}`}>{d.app}</a>
              <a class="title" href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a>
              <code class="muted">{d.sha}</code>
              <span class="muted when">{ago(since(d.created))}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="box empty">{t().noRecent}</p>
      {/if}
    </section>
  {/if}
</main>
</div>
</div>

<Toasts />
<Modal bind:open={leaveOpen} id="leave" alert={t().leaveAlert}>
  {#snippet heading()}{t().leaveTitle}{/snippet}
  <div class="m-body"><p class="m-note">{t().leaveDesc}</p></div>
  <div class="m-foot">
    <button type="button" class="btn" onclick={() => { leaveOpen = false; leaving = null; }}>{t().stay}</button>
    <button type="button" class="btn primary" onclick={() => leaveNow()}>{t().leaveAnyway}</button>
  </div>
</Modal>
<Palette bind:open={paletteOpen} oncheck={checkSecurity} />
<Terminal user={meta?.user ?? ""} />
<JobPill />

<style>
  .skip { position: absolute; left: -9999px; top: 8px; z-index: 50; }
  /* Mientras el servidor responde (unos segundos por SSH): una barra fina arriba. */
  .progress { position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 60; pointer-events: none; opacity: 0; transition: opacity 200ms var(--ease); }
  .progress.on { opacity: 1; background: linear-gradient(90deg, transparent, var(--accent), transparent); background-size: 40% 100%; background-repeat: no-repeat; }
  @media (prefers-reduced-motion: no-preference) {
    .progress.on { animation: slide 1.1s var(--ease) infinite; }
    .spin { animation: spin 0.9s linear infinite; }
  }
  @keyframes slide { from { background-position: -40% 0; } to { background-position: 140% 0; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  .refresh { gap: 6px; }
  /* Lo de antes, mientras llega lo nuevo: se ve, un poco atenuado. */
  .fresh { transition: opacity 200ms var(--ease); }
  .fresh.stale { opacity: 0.72; }
  .skip:focus { left: 16px; background: var(--surface); padding: 8px 12px; border-radius: 6px; }
  .top {
    position: sticky; top: 0; z-index: 10;
    background: color-mix(in oklch, var(--canvas) 92%, transparent);
    border-bottom: 1px solid var(--line);
  }
  @supports (backdrop-filter: blur(8px)) {
    .top { backdrop-filter: saturate(1.4) blur(10px); }
  }
  .inner {
    max-width: var(--page); margin: 0 auto; padding: var(--space-2) var(--space-5);
    display: flex; align-items: center; gap: var(--space-4); min-height: 48px;
  }
  /* Pantallas chicas: el sidebar se abre con ☰; arriba, la marca. */
  @media (max-width: 900px) {
    .menu { display: inline-grid; }
    .top .brand { display: inline-flex; }
  }
  .brand { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--ink); font-weight: 650; letter-spacing: -0.01em; font-size: 16px; }
  .brand :global(svg) { color: var(--accent); }
  .brand:hover { text-decoration: none; }
  .spacer { flex: 1; }
  .stamp { color: var(--muted); font-size: 13px; }
  /* El sidebar a la izquierda; el contenido ocupa el resto. */
  .shell { display: flex; align-items: flex-start; min-height: 100vh; }
  .content { flex: 1; min-width: 0; }
  .menu { display: none; width: 34px; height: 34px; place-items: center; border: 0; border-radius: 8px; background: transparent; color: var(--ink); cursor: pointer; }
  .menu:hover { background: var(--sunken); }
  .top .brand { display: none; }
  main { max-width: var(--page); margin: 0 auto; padding: var(--space-6) var(--space-5) 140px; outline: none; }
  main :global(h1) { font-size: 28px; line-height: 1.15; letter-spacing: -0.02em; margin: 0; font-weight: 650; }
  main :global(h2) {
    font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    font-weight: 600; margin: 0 0 var(--space-3);
  }
  .apps { margin-top: var(--space-7); }
  .banner {
    margin: 0 0 var(--space-5); padding: var(--space-3) var(--space-4); border-radius: 8px; font-size: 14px;
    background: color-mix(in oklch, var(--bad) 10%, var(--surface));
    border: 1px solid color-mix(in oklch, var(--bad) 35%, var(--line));
  }
  .muted { color: var(--muted); }
  .loading { padding: var(--space-7) 0; }
  .attention {
    margin-bottom: var(--space-5); padding: var(--space-4) var(--space-5); border-radius: 12px;
    background: color-mix(in oklch, var(--bad) 8%, var(--surface)); border: 1px solid color-mix(in oklch, var(--bad) 35%, var(--line));
  }
  .attention h2 { color: var(--bad-text); }
  .attention ul { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-3); }
  .attention li { display: flex; gap: var(--space-3); align-items: baseline; }
  .attention .fix { font-size: 13.5px; color: var(--muted); }
  .recent { list-style: none; margin: 0; padding: 0; }
  .recent li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); }
  .recent li:last-child { border-bottom: 0; }
  .recent .app { font-weight: 600; color: var(--ink); min-width: 140px; }
  .recent .title { flex: 1; min-width: 220px; }
  .recent .when { min-width: 80px; text-align: right; }
  .empty { margin: 0; padding: var(--space-3) var(--space-4); color: var(--muted); }
  @media (max-width: 640px) {
    /* En el celular: la marca, Ir a (Ctrl+K), historial, ajustes y Actualizar. El servidor está en Ajustes. */
    .stamp { display: none; }
    .inner { gap: var(--space-2); }
    .inner { padding: var(--space-3) var(--space-4); }
    main { padding: var(--space-5) var(--space-4) 140px; }
  }
</style>
