<!--
  Ajustes → Código: de dónde sale la app. El repo y la rama (cada push a main despliega), y si
  comparte el repo con otras (dir:), su carpeta, si se construye desde la raíz y qué rutas
  disparan su deploy. Cambiarlo corre `andamio app source`: reescribe su pipeline en el repo de
  la app; no toca el servidor.
-->
<script lang="ts">
  import type { App } from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";

  let { app: a, ondone }: { app: App; ondone: () => void } = $props();

  const repoUrl = $derived(`https://github.com/${a.repo}`);
  const wfile = $derived(a.dir ? `andamio-${a.name}.yml` : "andamio.yml");
  let editingDir = $state(false);
  let dirValue = $state("");
  let adding = $state(false);
  let watchValue = $state("");
  const dirOk = $derived(/^[A-Za-z0-9._-]+(\/[A-Za-z0-9._-]+)*$/.test(dirValue.replace(/\/$/, "")) && !dirValue.includes(".."));
  const watchOk = $derived(/^[A-Za-z0-9._*/-]+$/.test(watchValue.replace(/^\//, "")) && !watchValue.includes("..")
    && !a.watch.includes(watchValue.replace(/^\//, "")));
  const run = (body: Record<string, string>) => job.arm({ action: "source", app: a.name, ...body }, (ok) => ok && ondone());
  const ROOT_FILES = "package.json, lockfiles, pnpm-workspace.yaml";
</script>

<dl class="kv box pad">
  <dt>{t().srcRepo}</dt>
  <dd><a class="mono" href={repoUrl} target="_blank" rel="noopener noreferrer">{a.repo}</a></dd>
  <dt>{t().srcBranch}</dt>
  <dd><code>{a.branch || "main"}</code> <span class="muted small">{t().srcBranchHint}</span></dd>
  <dt>{t().srcFolder}</dt>
  <dd>
    {#if !a.dir}
      <span>{t().srcRoot}</span> <span class="muted small">{t().srcRootHint}</span>
    {:else if editingDir}
      <form class="inline" onsubmit={(e) => { e.preventDefault(); if (dirOk) { run({ dir: dirValue.replace(/\/$/, "") }); editingDir = false; } }}>
        <input bind:value={dirValue} class="mono" spellcheck="false" aria-label={t().srcFolder} aria-invalid={dirValue && !dirOk ? "true" : undefined} />
        <button type="submit" class="btn small primary" disabled={!dirOk || dirValue.replace(/\/$/, "") === a.dir || job.locked}>{t().save}</button>
        <button type="button" class="btn small quiet" onclick={() => (editingDir = false)}>{t().cancel}</button>
      </form>
      <p class="muted small">{t().srcFolderHint}</p>
    {:else}
      <code>{a.dir}/</code>
      <button type="button" class="btn small quiet" disabled={job.locked} onclick={() => { dirValue = a.dir; editingDir = true; }}>{t().changeShort}</button>
    {/if}
  </dd>
  {#if a.dir}
    <dt>{t().srcBuild}</dt>
    <dd>
      <label class="check">
        <input type="checkbox" checked={a.context === "."} disabled={job.locked}
          onchange={(e) => run({ context: (e.currentTarget as HTMLInputElement).checked ? "." : "-" })} />
        {t().buildFromRoot}
      </label>
    </dd>
    <dt>{t().srcWatch}</dt>
    <dd>
      <ul class="watch">
        <li><code>{a.dir}/</code><span class="muted small">{t().srcWatchOwn}</span></li>
        {#each a.watch as w (w)}
          <li><code>{w}</code>
            <button type="button" class="btn small quiet danger" disabled={job.locked} aria-label={t().removeX(w)}
              onclick={() => run({ watch_rm: w })}>{t().remove}</button></li>
        {/each}
        {#if a.context === "."}<li><code class="muted">{ROOT_FILES}</code><span class="muted small">{t().srcWatchRoot}</span></li>{/if}
      </ul>
      {#if adding}
        <form class="inline" onsubmit={(e) => { e.preventDefault(); if (watchOk) { run({ watch_add: watchValue.replace(/^\//, "") }); adding = false; watchValue = ""; } }}>
          <input bind:value={watchValue} class="mono" placeholder="packages/" spellcheck="false" aria-label={t().srcWatch} />
          <button type="submit" class="btn small primary" disabled={!watchOk || job.locked}>{t().add}</button>
          <button type="button" class="btn small quiet" onclick={() => (adding = false)}>{t().cancel}</button>
        </form>
        <p class="muted small">{t().srcWatchHint}</p>
      {:else}
        <button type="button" class="btn small quiet" disabled={job.locked} onclick={() => (adding = true)}>{t().srcWatchAdd}</button>
      {/if}
    </dd>
  {/if}
  <dt>Pipeline</dt>
  <dd><a class="mono small" href={`${repoUrl}/blob/${a.branch || "main"}/.github/workflows/${wfile}`} target="_blank" rel="noopener noreferrer">.github/workflows/{wfile}</a></dd>
</dl>

<style>
  .kv { display: grid; grid-template-columns: 170px minmax(0, 1fr); gap: var(--space-3) var(--space-4); margin: 0; align-items: baseline; }
  .pad { padding: var(--space-4) var(--space-5); }
  dt { color: var(--muted); font-size: 14px; }
  dd { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px var(--space-2); }
  dd > p { flex-basis: 100%; margin: 0; }
  .mono { font-family: var(--mono); font-size: 0.9em; }
  .muted { color: var(--muted); }
  .small { font-size: 12.5px; }
  .inline { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
  .inline input {
    font: 13px var(--mono); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 6px 9px; min-width: 200px;
  }
  .inline input:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 28%, transparent); outline-offset: 0; border-color: var(--accent); }
  .inline input[aria-invalid="true"] { border-color: var(--bad); }
  .check { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
  .watch { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; flex-basis: 100%; }
  .watch li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
  @media (max-width: 720px) { .kv { grid-template-columns: minmax(0, 1fr); } dt { margin-top: var(--space-2); } }
</style>
