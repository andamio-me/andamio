<!--
  Ctrl+K (⌘K en Mac): ir a cualquier app o página, o lanzar una acción, escribiendo. Todo con el
  teclado: flechas, Enter, Esc. Las acciones no corren solas: se arman en la terminal, con su
  comando a la vista, como cualquier botón del panel.
-->
<script lang="ts">
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import { prefetchApp } from "../lib/cache.svelte";
  import { theme } from "../lib/theme.svelte";
  import { appHref, SECTIONS, type Section } from "../lib/nav";

  let { open = $bindable(false), oncheck }: { open?: boolean; oncheck: () => void } = $props();

  type Item = { id: string; group: "go" | "do"; label: string; hint?: string; run: () => void };

  let dialog: HTMLDialogElement | undefined = $state();
  let input: HTMLInputElement | undefined = $state();
  let query = $state("");
  let active = $state(0);
  let names = $state<{ name: string; url: string; stopped: boolean }[]>([]);

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) {
      query = "";
      active = 0;
      dialog.showModal();
      queueMicrotask(() => input?.focus());
      api.names().then((r) => (names = r.apps)).catch(() => {});
    }
    if (!open && dialog.open) dialog.close();
  });

  const go = (hash: string) => () => { location.hash = hash; };
  const sectionLabel = (sec: Section) => ({ overview: t().secOverview, deploys: t().secDeploys, logs: t().secLogs,
    metrics: t().secMetrics, variables: t().secVariables, tasks: t().secTasks, database: t().secDatabase, settings: t().secSettings })[sec];
  const items = $derived.by((): Item[] => {
    const s = t();
    const list: Item[] = [
      { id: "home", group: "go", label: s.home, run: go("#/") },
      ...names.map((a) => ({ id: `app-${a.name}`, group: "go" as const, label: a.name, hint: a.url.replace("https://", ""), run: go(`#/app/${a.name}`) })),
      // Cada sección de cada app ("web logs"): solo cuando escribes algo, para no llenar la lista.
      ...(query.trim() ? names.flatMap((a) => SECTIONS.filter((sec) => sec !== "overview").map((sec) => ({
        id: `app-${a.name}-${sec}`, group: "go" as const, label: `${a.name} · ${sectionLabel(sec)}`,
        run: go(appHref(a.name, sec)) }))) : []),
      { id: "new", group: "go", label: s.newApp, run: go("#/new") },
      { id: "backups", group: "go", label: s.backups, run: go("#/backups") },
      { id: "history", group: "go", label: s.history, run: go("#/history") },
      { id: "settings", group: "go", label: s.settings, run: go("#/settings") },
      { id: "backup-now", group: "do", label: s.backupNow, hint: "andamio backups now", run: () => job.arm({ action: "backup-now" }) },
      { id: "estado", group: "do", label: s.checkNow, hint: "andamio estado", run: oncheck },
      ...(["light", "dark", "system"] as const).filter((v) => v !== theme.value).map((v) => ({
        id: `theme-${v}`, group: "do" as const, label: s.themeTo(v), run: () => theme.set(v) })),
      ...names.map((a) => ({
        id: `toggle-${a.name}`, group: "do" as const, label: a.stopped ? s.start(a.name) : s.stop(a.name),
        hint: `andamio app ${a.stopped ? "start" : "stop"} ${a.name}`,
        run: () => job.arm({ action: a.stopped ? "start" : "stop", app: a.name }),
      })),
    ];
    return list;
  });

  // Coincide si cada palabra que escribes está en el nombre (sin tildes ni mayúsculas).
  const plain = (v: string) => v.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const shown = $derived.by(() => {
    const words = plain(query).split(/\s+/).filter(Boolean);
    return words.length ? items.filter((i) => words.every((w) => plain(`${i.label} ${i.hint ?? ""}`).includes(w))) : items;
  });
  $effect(() => {
    void query;
    active = 0;
  });
  // La app elegida se va trayendo mientras decides: al dar Enter ya está.
  $effect(() => {
    const id = shown[active]?.id ?? "";
    if (open && id.startsWith("app-")) prefetchApp(id.slice(4).replace(/-(deploys|logs|metrics|variables|tasks|database|settings)$/, ""));
  });

  function pick(i: Item | undefined) {
    if (!i || (i.group === "do" && job.locked && !i.id.startsWith("theme-"))) return;
    open = false;
    i.run();
  }
  function key(e: KeyboardEvent) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const n = shown.length;
      if (n) active = (active + (e.key === "ArrowDown" ? 1 : n - 1)) % n;
      document.getElementById(`pal-${shown[active]?.id}`)?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(shown[active]);
    }
  }
  const backdrop = (e: MouseEvent) => { if (e.target === dialog) open = false; };
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dialog} onclick={backdrop} onclose={() => (open = false)} aria-label={t().palette}>
  <div class="card">
    <div class="field">
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
      <input bind:this={input} bind:value={query} onkeydown={key} placeholder={t().palettePh} spellcheck="false" autocomplete="off"
        role="combobox" aria-expanded="true" aria-controls="pal-list" aria-activedescendant={shown[active] ? `pal-${shown[active]!.id}` : undefined} />
      <kbd>Esc</kbd>
    </div>
    <ul id="pal-list" role="listbox" aria-label={t().palette}>
      {#each shown as it, i (it.id)}
        {#if i === 0 || shown[i - 1]!.group !== it.group}
          <li class="grp" role="presentation">{it.group === "go" ? t().goTo : t().actions}</li>
        {/if}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <li id={`pal-${it.id}`} role="option" aria-selected={i === active} class:on={i === active}
          class:off={it.group === "do" && job.locked} onclick={() => pick(it)} onmousemove={() => (active = i)}>
          <span class="ic" aria-hidden="true">{it.group === "go" ? "→" : "$"}</span>
          <span class="lbl">{it.label}</span>
          {#if it.hint}<span class="hint">{it.hint}</span>{/if}
        </li>
      {:else}
        <li class="none" role="presentation">{t().paletteNone}</li>
      {/each}
    </ul>
  </div>
</dialog>

<style>
  dialog {
    padding: 0; border: 0; background: transparent; color: var(--ink); margin: 12vh auto auto;
    width: min(600px, calc(100vw - 2 * var(--space-4))); max-width: none;
  }
  dialog::backdrop { background: oklch(0.14 0.02 262 / 0.45); }
  @media (prefers-reduced-motion: no-preference) {
    dialog[open] .card { animation: pop 150ms var(--ease); }
  }
  @keyframes pop { from { opacity: 0; transform: translateY(-6px) scale(0.99); } }
  .card {
    background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
    box-shadow: 0 32px 64px -24px oklch(0.15 0.05 262 / 0.6);
  }
  .field { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); color: var(--muted); }
  .field input { flex: 1; border: 0; outline: 0; background: transparent; color: var(--ink); font: 16px var(--sans); padding: 6px 0; }
  kbd { font: 11.5px var(--mono); color: var(--muted); border: 1px solid var(--line); border-radius: 5px; padding: 2px 6px; }
  ul { list-style: none; margin: 0; padding: var(--space-2); max-height: min(420px, 60vh); overflow: auto; }
  .grp { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); padding: var(--space-2) var(--space-3) 4px; }
  li[role="option"] {
    display: flex; align-items: center; gap: var(--space-3); padding: 9px var(--space-3); border-radius: 8px; cursor: pointer; font-size: 14.5px;
  }
  li.on { background: color-mix(in oklch, var(--accent) 12%, var(--surface)); }
  li.off { opacity: 0.45; cursor: not-allowed; }
  .ic { width: 16px; text-align: center; color: var(--muted); font-family: var(--mono); }
  li.on .ic { color: var(--accent); }
  .lbl { font-weight: 500; }
  .hint { margin-left: auto; color: var(--muted); font-size: 12.5px; font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 55%; }
  .none { padding: var(--space-4); color: var(--muted); font-size: 14px; }
</style>
