<!--
  El sidebar: arriba el servidor y "Ir a…" (Ctrl+K); Inicio; tus apps (la abierta, desplegada con
  sus secciones); la plataforma (respaldos, historial, ajustes); abajo los avisos y el botón para
  contraerlo a íconos (se recuerda en este navegador). En pantallas chicas se abre con ☰, encima
  del contenido. Los números dicen dónde mirar: ✕ si el último deploy falló, un punto rojo si el
  último respaldo falló.
-->
<script lang="ts">
  import type { App, Meta } from "../lib/api";
  import { prefetchApp } from "../lib/cache.svelte";
  import { status } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { appHref, type Section } from "../lib/nav";
  import Mark from "./Mark.svelte";
  import NoticeBell from "./NoticeBell.svelte";
  import ServerSwitch from "./ServerSwitch.svelte";

  let { meta, apps, route, current, section, failedDeploys, backupBad, collapsed = false, open = $bindable(false), onfind, oncollapse }: {
    meta: Meta | null; apps: App[]; route: string; current: string | null; section: Section | null;
    failedDeploys: Set<string>; backupBad: boolean; collapsed?: boolean; open?: boolean; onfind: () => void;
    oncollapse: (v: boolean) => void;
  } = $props();

  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
  const sections = $derived.by(() => {
    const s = t();
    const app = apps.find((a) => a.name === current);
    const list: { id: Section; label: string; icon: string }[] = [
      { id: "overview", label: s.secOverview, icon: "M2.5 8.5L8 3l5.5 5.5M4 7v6h8V7" },
      { id: "deploys", label: s.secDeploys, icon: "M8 2v8M4.5 6.5L8 10l3.5-3.5M3 13.5h10" },
      { id: "logs", label: s.secLogs, icon: "M3 4h10M3 8h10M3 12h6" },
      { id: "metrics", label: s.secMetrics, icon: "M2.5 12.5l3.5-4 3 2.5 4.5-6" },
      { id: "variables", label: s.secVariables, icon: "M5.5 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5zM7.5 7.5L13 13M11 11l1.5-1.5" },
      { id: "tasks", label: s.secTasks, icon: "M8 3.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9zM8 5.5V8l1.8 1.2" },
      ...(app?.db || app?.mysql ? [{ id: "database" as Section, label: s.secDatabase, icon: "M3.5 4.5c0-1.1 2-2 4.5-2s4.5.9 4.5 2-2 2-4.5 2-4.5-.9-4.5-2zM3.5 4.5v7c0 1.1 2 2 4.5 2s4.5-.9 4.5-2v-7M3.5 8c0 1.1 2 2 4.5 2s4.5-.9 4.5-2" }] : []),
      { id: "settings", label: s.secSettings, icon: "M8 5.8a2.2 2.2 0 100 4.4 2.2 2.2 0 000-4.4zM8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" },
    ];
    return list;
  });
  const isHome = $derived(route === "" || route === "#" || route === "#/");
  const onRoute = (hash: string) => route === hash || route.startsWith(`${hash}/`);
  // Varias apps de un mismo repo (front y back): juntas, en el orden de la primera.
  const ordered = $derived.by(() => {
    const out: App[] = [];
    for (const a of apps) {
      if (out.includes(a)) continue;
      out.push(a);
      if (a.dir) out.push(...apps.filter((b) => b !== a && b.dir && b.repo === a.repo));
    }
    return out;
  });
</script>

{#snippet icon(d: string)}
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path {d} fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg>
{/snippet}

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="scrim" class:open onclick={() => (open = false)}></div>
<aside class="side" class:collapsed class:open aria-label={t().sidebar}>
  <div class="top">
    <a class="brand" href="#/" aria-label="andamio"><Mark size={19} />{#if !collapsed}<span>andamio</span>{/if}</a>
    {#if meta && !collapsed}<div class="srv"><ServerSwitch domain={meta.domain} server={meta.server} /></div>{/if}
    <button type="button" class="find" onclick={onfind} aria-label={t().palette} title={`${t().palette} (${isMac ? "⌘" : "Ctrl"} K)`}>
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
      {#if !collapsed}<span class="ftxt">{t().goToShort}</span><kbd>{isMac ? "⌘" : "Ctrl"} K</kbd>{/if}
    </button>
  </div>

  <nav class="nav">
    <a class="item" class:on={isHome} aria-current={isHome ? "page" : undefined} href="#/" title={collapsed ? t().home : undefined}>
      {@render icon("M2.5 7.5L8 3l5.5 4.5V13H10V9.5H6V13H2.5z")}{#if !collapsed}<span>{t().home}</span>{/if}
    </a>

    <div class="group">{#if !collapsed}{t().sbApps}{:else}<span class="rule"></span>{/if}</div>
    <ul class="apps">
      {#each ordered as a (a.name)}
        {@const st = status(a)}
        {@const here = current === a.name}
        <li>
          <a class="item app" class:on={here && section === "overview"} class:here href={appHref(a.name)}
            aria-current={here && section === "overview" ? "page" : undefined} title={collapsed ? `${a.name} · ${st.text}` : undefined}
            onmouseenter={() => prefetchApp(a.name)} onfocus={() => prefetchApp(a.name)}>
            <span class={`dot ${st.tone}`} aria-label={st.text}></span>
            {#if !collapsed}<span class="name">{a.name}</span>{#if a.dir}<span class="adir" title={`${a.repo} · ${a.dir}/`}>{a.dir.split("/").pop()}/</span>{/if}{#if failedDeploys.has(a.name) && !here}<span class="badge bad" title={t().attnDeployFailed("")}>✕</span>{/if}{/if}
          </a>
          {#if here}
            <ul class="subs">
              {#each sections as s (s.id)}
                {@const on = section === s.id}
                <li>
                  <a class="item sub" class:on href={appHref(a.name, s.id)} aria-current={on ? "page" : undefined} title={collapsed ? s.label : undefined}>
                    {@render icon(s.icon)}{#if !collapsed}<span>{s.label}</span>{/if}
                    {#if s.id === "deploys" && failedDeploys.has(a.name)}<span class="badge bad" aria-label={t().lastFailed}>✕</span>{/if}
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ul>
    <a class="item newapp" class:on={route === "#/new"} href="#/new" title={collapsed ? t().newApp : undefined}>
      {@render icon("M8 3v10M3 8h10")}{#if !collapsed}<span>{t().newApp}</span>{/if}
    </a>

    <div class="group">{#if !collapsed}{t().sbPlatform}{:else}<span class="rule"></span>{/if}</div>
    <a class="item" class:on={onRoute("#/backups")} href="#/backups" title={collapsed ? t().backups : undefined}>
      {@render icon("M3 5.5h10v7.5H3zM2 3h12v2.5H2zM6.5 8.5h3")}{#if !collapsed}<span>{t().backups}</span>{/if}
      {#if backupBad}<span class="badge dotbad" aria-label={t().backupBad}></span>{/if}
    </a>
    <a class="item" class:on={route === "#/services"} href="#/services" title={collapsed ? t().svTitle : undefined}>
      {@render icon("M3 4c0-1.1 2.2-2 5-2s5 .9 5 2-2.2 2-5 2-5-.9-5-2zM3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4M3 8c0 1.1 2.2 2 5 2s5-.9 5-2")}{#if !collapsed}<span>{t().svTitle}</span>{/if}
    </a>
    <a class="item" class:on={onRoute("#/history")} href="#/history" title={collapsed ? t().history : undefined}>
      {@render icon("M2.5 8a5.5 5.5 0 105.5-5.5A5.6 5.6 0 003.6 5M3.2 2.6V5h2.4M8 5v3.2l2 1.3")}{#if !collapsed}<span>{t().history}</span>{/if}
    </a>
    <a class="item" class:on={route === "#/settings"} href="#/settings" title={collapsed ? t().settings : undefined}>
      {@render icon("M8 5.8a2.2 2.2 0 100 4.4 2.2 2.2 0 000-4.4zM8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4")}{#if !collapsed}<span>{t().settings}</span>{/if}
    </a>
  </nav>

  <div class="bottom">
    <NoticeBell up />
    <button type="button" class="collapse" onclick={() => oncollapse(!collapsed)} aria-pressed={collapsed}
      aria-label={collapsed ? t().expandSidebar : t().collapseSidebar} title={collapsed ? t().expandSidebar : t().collapseSidebar}>
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d={collapsed ? "M6 4l4 4-4 4" : "M10 4L6 8l4 4"} fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
  </div>
</aside>

<style>
  .side {
    position: sticky; top: 0; height: 100vh; width: 248px; flex: none; display: flex; flex-direction: column;
    border-right: 1px solid var(--line); background: color-mix(in oklch, var(--canvas) 70%, var(--surface));
    transition: width 200ms var(--ease);
  }
  .side.collapsed { width: 64px; }
  .top { display: grid; gap: var(--space-2); padding: var(--space-4) var(--space-3) var(--space-3); }
  .brand { display: inline-flex; align-items: center; gap: var(--space-2); padding: 0 var(--space-2); color: var(--ink); font-weight: 650; font-size: 16px; letter-spacing: -0.01em; }
  .brand:hover { text-decoration: none; }
  .brand :global(svg) { color: var(--accent); flex: none; }
  .srv { padding: 0 var(--space-1); font-size: 13px; }
  .find {
    display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 8px 0 10px; border: 1px solid var(--line); border-radius: 8px;
    background: var(--surface); color: var(--muted); font: 13px var(--sans); cursor: pointer;
  }
  .collapsed .find { justify-content: center; padding: 0; }
  .find:hover { color: var(--ink); border-color: color-mix(in oklch, var(--muted) 60%, var(--line)); }
  .ftxt { flex: 1; text-align: left; }
  kbd { font: 11px var(--mono); border: 1px solid var(--line); border-radius: 5px; padding: 1px 5px; color: var(--muted); }
  .nav { flex: 1; overflow-y: auto; padding: var(--space-1) var(--space-3) var(--space-3); display: grid; align-content: start; gap: 2px; }
  .group { margin: var(--space-4) var(--space-2) var(--space-1); font-size: 11.5px; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted); }
  .rule { display: block; border-top: 1px solid var(--line); margin: 0 4px; }
  .adir { font: 11.5px var(--mono); color: var(--muted); margin-left: auto; padding-left: 6px; white-space: nowrap; }
  .apps, .subs { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
  .subs { margin: 2px 0 6px 13px; padding-left: 10px; border-left: 1px solid var(--line); }
  .collapsed .subs { margin-left: 0; padding-left: 0; border-left: 0; }
  .item {
    display: flex; align-items: center; gap: 10px; min-height: 34px; padding: 0 10px; border-radius: 8px;
    color: var(--muted); font-size: 14px; text-decoration: none; position: relative;
  }
  .collapsed .item { justify-content: center; padding: 0; }
  .item:hover { background: var(--sunken); color: var(--ink); text-decoration: none; }
  .item.on { background: color-mix(in oklch, var(--accent) 13%, var(--surface)); color: var(--ink); font-weight: 600; }
  .item.on::before { content: ""; position: absolute; left: -3px; top: 8px; bottom: 8px; width: 2px; border-radius: 2px; background: var(--accent); }
  .collapsed .item.on::before { display: none; }
  .item.app.here:not(.on) { color: var(--ink); font-weight: 600; }
  .item.sub { min-height: 30px; font-size: 13.5px; }
  .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .item :global(svg) { flex: none; }
  .badge { margin-left: auto; font-size: 11px; font-weight: 700; line-height: 1; }
  .badge.bad { color: var(--bad-text); }
  .badge.dotbad { width: 8px; height: 8px; border-radius: 50%; background: var(--bad); }
  .collapsed .badge { position: absolute; top: 4px; right: 6px; }
  .newapp { margin-top: 2px; }
  .bottom { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2) var(--space-3) var(--space-3); border-top: 1px solid var(--line); }
  .collapsed .bottom { flex-direction: column; }
  .collapse { width: 30px; height: 30px; display: grid; place-items: center; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; }
  .collapse:hover { background: var(--sunken); color: var(--ink); }
  .scrim { display: none; }

  /* Pantallas chicas: el sidebar se abre encima del contenido (☰), siempre completo. */
  @media (max-width: 900px) {
    .side { position: fixed; z-index: 45; left: 0; top: 0; width: 272px; transform: translateX(-100%); transition: transform 220ms var(--ease); box-shadow: 0 0 40px -10px oklch(0.1 0.05 262 / 0.5); }
    .side.collapsed { width: 272px; }
    .side.open { transform: none; }
    .collapse { display: none; }
    .scrim.open { display: block; position: fixed; inset: 0; z-index: 44; background: oklch(0.12 0.02 262 / 0.5); }
  }
  @media (prefers-reduced-motion: reduce) { .side { transition: none; } }
</style>
