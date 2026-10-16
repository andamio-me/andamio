<!--
  La base de la app, de SOLO LECTURA (lo mismo que `andamio app sql`). A la izquierda sus tablas
  (con buscador, filas reales y sus columnas al abrirlas); a la derecha el editor y el resultado.
  El resultado vive en su propia caja con scroll (encabezado y primera columna fijos): la página no
  se mueve. Dos vistas: tabla, o registro (campo por campo; sola si hay una fila). Las columnas
  sensibles (contraseñas, hashes, secretos, tokens) van ocultas hasta que pidas verlas. Clic en una
  celda: su valor completo, con copiar. Corre como <rol>_ro: solo SELECT, 5 s, hasta 500 filas.
-->
<script lang="ts">
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import Modal from "./Modal.svelte";

  let { app, engine = "postgres" }: { app: string; engine?: api.SqlEngine } = $props();
  const my = $derived(engine === "mysql");

  // ---- Tablas ----
  let tables = $state<api.SqlTable[] | null>(null);
  let tablesErr = $state("");
  let filter = $state("");
  let openTable = $state("");   // la que muestra sus columnas
  $effect(() => {
    const a = app;
    tables = null;
    api.sqlTables(a, engine).then((r) => { tables = r.tables; tablesErr = r.error; }).catch((e) => { tables = []; tablesErr = String(e.message); });
  });
  // En MariaDB la base es una sola (la de la app): su nombre no hace falta.
  const full = (tb: api.SqlTable) => `${tb.schema === "public" || my ? "" : `${tb.schema}.`}${tb.name}`;
  const shown = $derived((tables ?? []).filter((tb) => full(tb).toLowerCase().includes(filter.trim().toLowerCase())));
  const ident = (s: string) => (/^[a-z_][a-z0-9_]*$/.test(s) ? s : my ? `\`${s.replaceAll("`", "``")}\`` : `"${s.replaceAll('"', '""')}"`);
  const rowsLabel = (tb: api.SqlTable) => (tb.rows < 0 ? "—" : `${tb.exact ? "" : "≈"}${tb.rows.toLocaleString()}`);

  function browse(tb: api.SqlTable) {
    query = `SELECT * FROM ${tb.schema === "public" || my ? "" : `${ident(tb.schema)}.`}${ident(tb.name)} LIMIT 50;`;
    void run();
  }

  // ---- Consulta e historial (en tu navegador, por app) ----
  let query = $state("");
  let result = $state<api.SqlResult | null>(null);
  let running = $state(false);
  let lastQuery = $state("");
  const histKey = $derived(`andamio.sql.${app}${my ? ".mysql" : ""}`);
  let history = $state<string[]>([]);
  let histOpen = $state(false);
  $effect(() => {
    try { history = JSON.parse(localStorage.getItem(histKey) ?? "[]"); } catch { history = []; }
  });
  function remember(q: string) {
    history = [q, ...history.filter((h) => h !== q)].slice(0, 12);
    try { localStorage.setItem(histKey, JSON.stringify(history)); } catch { /* sin almacenamiento */ }
  }

  async function run() {
    const q = query.trim();
    if (!q || running) return;
    running = true;
    histOpen = false;
    try {
      result = await api.sql(app, q, engine);
      lastQuery = q;
      if (!result.error) remember(q);
      reveal = false;
      record = 0;
      view = result.rows.length === 1 ? "record" : "table";
    } catch (e) {
      result = { columns: [], rows: [], error: String((e as Error).message) };
    } finally {
      running = false;
    }
  }
  function key(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void run();
    }
  }
  function download() {
    if (!result?.columns.length) return;
    const cell = (v: string) => (/[",\n]/.test(v) ? `"${v.replaceAll('"', '""')}"` : v);
    // Las columnas sensibles salen en el CSV solo si las tienes a la vista ("Mostrar sensibles").
    const rows = result.rows.map((r) => r.map((v, i) => (secret[i] && !reveal && v !== "" ? "[oculto]" : v)));
    const text = [result.columns, ...rows].map((r) => r.map(cell).join(",")).join("\n") + "\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = `${app}-consulta.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---- Resultado: tipos, sensibles, vistas ----
  let view = $state<"table" | "record">("table");
  let record = $state(0);
  let reveal = $state(false);
  const SENSITIVE = /pass(word)?|hash|secret|token|two_?factor|api_?key|private|otp|salt|recovery/i;
  type Kind = "bool" | "num" | "date" | "json" | "text";
  // El CSV no trae tipos: se deducen de los valores de cada columna (vacío = null).
  const kinds = $derived.by(() => {
    if (!result?.columns.length) return [] as Kind[];
    return result.columns.map((_, i) => {
      const vals = result!.rows.map((r) => r[i] ?? "").filter((v) => v !== "");
      if (!vals.length) return "text";
      if (vals.every((v) => v === "t" || v === "f")) return "bool";
      if (vals.every((v) => /^-?\d+(\.\d+)?$/.test(v))) return "num";
      if (vals.every((v) => /^\d{4}-\d\d-\d\d([ T]\d\d:\d\d(:\d\d(\.\d+)?)?([+-]\d\d(:?\d\d)?|Z)?)?$/.test(v))) return "date";
      if (vals.every((v) => /^[[{]/.test(v))) return "json";
      return "text";
    });
  });
  // Sensible: por el nombre, y solo si guarda texto (tokenVersion, un número, no es secreto).
  const secret = $derived((result?.columns ?? []).map((c, i) => SENSITIVE.test(c) && (kinds[i] === "text" || kinds[i] === "json")));
  const anySecret = $derived(secret.some(Boolean));
  const fmtDate = (v: string) => v.replace("T", " ").replace(/(\d\d:\d\d:\d\d)\.\d+/, "$1");

  // Una celda, completa: con JSON formateado y copiar.
  let cellOpen = $state(false);
  let cell = $state<{ col: string; value: string; kind: Kind }>({ col: "", value: "", kind: "text" });
  let copied = $state(false);
  function openCell(i: number, value: string) {
    if (secret[i] && !reveal) return;
    cell = { col: result!.columns[i]!, value, kind: kinds[i] ?? "text" };
    copied = false;
    cellOpen = true;
  }
  const pretty = (v: string, k: Kind) => {
    if (k !== "json") return v;
    try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return v; }
  };
  async function copy() {
    try { await navigator.clipboard.writeText(cell.value); copied = true; } catch { copied = false; }
  }
</script>

{#snippet value(v: string, i: number)}
  {#if v === ""}<span class="null">null</span>
  {:else if secret[i] && !reveal}<span class="masked" title={t().sqlHidden}>••••••••</span>
  {:else if kinds[i] === "bool"}<span class={v === "t" ? "yes" : "no"}>{v === "t" ? "✓ true" : "✗ false"}</span>
  {:else if kinds[i] === "date"}<span title={v}>{fmtDate(v)}</span>
  {:else}{v}{/if}
{/snippet}

<section class="sql" aria-labelledby="sql-title">
  <div class="shead">
    <div><h2 id="sql-title">{t().sqlTitle}</h2><p class="desc">{t().sqlDesc}</p></div>
    <span class="ro" title={t().sqlLimits}>
      <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4" /><path d="M5.5 7V5a2.5 2.5 0 015 0v2" fill="none" stroke="currentColor" stroke-width="1.4" /></svg>
      {t().readOnly}
    </span>
  </div>

  <div class="layout">
    <!-- Tablas -->
    <nav class="box side" aria-label={t().sqlTables}>
      <div class="find">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
        <input type="search" bind:value={filter} placeholder={t().sqlFind(tables?.length ?? 0)} aria-label={t().sqlFind(tables?.length ?? 0)} spellcheck="false" />
      </div>
      {#if tables === null}
        <ul class="tlist" aria-hidden="true">{#each Array(8) as _, i (i)}<li class="sk"></li>{/each}</ul>
      {:else if tablesErr}
        <p class="err pad">{tablesErr}</p>
      {:else if !tables.length}
        <p class="muted pad">{t().sqlNoTables}</p>
      {:else}
        <ul class="tlist">
          {#each shown as tb (full(tb))}
            {@const isOpen = openTable === full(tb)}
            <li class:open={isOpen}>
              <button type="button" class="trow" aria-expanded={isOpen} onclick={() => (openTable = isOpen ? "" : full(tb))}>
                <svg class="chev" viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
                <span class="tn">{full(tb)}</span>
                <span class="rows" class:zero={tb.rows === 0} title={tb.exact ? t().sqlRowsExact : t().sqlRowsApprox}>{rowsLabel(tb)}</span>
              </button>
              {#if isOpen}
                <div class="tdetail">
                  <ul class="cols">
                    {#each tb.columns as c (c.name)}
                      <li><span class="cn" class:sens={SENSITIVE.test(c.name)}>{c.name}</span><span class="ct" title={c.type}>{c.type}</span></li>
                    {/each}
                  </ul>
                  <button type="button" class="btn small" onclick={() => browse(tb)} disabled={running}>{t().sqlBrowse}</button>
                </div>
              {/if}
            </li>
          {:else}
            <li class="muted pad">{t().sqlNoMatch}</li>
          {/each}
        </ul>
      {/if}
    </nav>

    <!-- Editor y resultado -->
    <div class="main">
      <div class="editor">
        <label for="sql-q" class="sr-only">{t().sqlQuery}</label>
        <textarea id="sql-q" bind:value={query} onkeydown={key} rows="4" spellcheck="false" placeholder="SELECT * FROM … LIMIT 50;"></textarea>
        <div class="bar">
          <div class="hist">
            <button type="button" class="btn small quiet" onclick={() => (histOpen = !histOpen)} aria-expanded={histOpen} disabled={!history.length}>
              {t().sqlHistory}{history.length ? ` (${history.length})` : ""}
            </button>
            {#if histOpen}
              <ul class="hmenu" role="menu">
                {#each history as h (h)}
                  <li><button type="button" role="menuitem" onclick={() => { query = h; histOpen = false; }}>{h}</button></li>
                {/each}
              </ul>
            {/if}
          </div>
          <span class="muted hint">{t().sqlLimits}</span>
          <span class="spacer"></span>
          <button type="button" class="btn small primary" onclick={run} disabled={running || !query.trim()} aria-busy={running}>
            {running ? t().sqlRunning : t().sqlRun} <kbd>Ctrl ↵</kbd>
          </button>
        </div>
      </div>

      <div class="result" aria-live="polite">
        {#if result?.error}
          <p class="box errbox" role="alert">{result.error}</p>
        {:else if result && !result.columns.length}
          <p class="box empty">{t().sqlEmpty}</p>
        {:else if result}
          <div class="rbar">
            <span class="meta">{t().sqlCount(result.count ?? result.rows.length, result.ms ?? 0)}{#if result.truncated} · {t().sqlTruncated}{/if}</span>
            <span class="spacer"></span>
            {#if anySecret}
              <button type="button" class="btn small quiet" aria-pressed={reveal} onclick={() => (reveal = !reveal)}>
                {reveal ? t().sqlHideSecrets : t().sqlShowSecrets}
              </button>
            {/if}
            <div class="seg" role="radiogroup" aria-label={t().sqlView}>
              <button type="button" role="radio" aria-checked={view === "table"} class:on={view === "table"} onclick={() => (view = "table")}>{t().sqlViewTable}</button>
              <button type="button" role="radio" aria-checked={view === "record"} class:on={view === "record"} onclick={() => (view = "record")}>{t().sqlViewRecord}</button>
            </div>
            <button type="button" class="btn small quiet" onclick={download}>{t().downloadCsv}</button>
          </div>

          {#if view === "table"}
            <div class="grid-wrap box">
              <table>
                <thead>
                  <tr>
                    <th class="rn" scope="col">#</th>
                    {#each result.columns as c, i (i)}
                      <th scope="col" class:num={kinds[i] === "num"}>{c}{#if secret[i]}<span class="lock" title={t().sqlHidden}>●</span>{/if}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each result.rows as row, r (r)}
                    <tr>
                      <td class="rn"><button type="button" class="rlink" onclick={() => { record = r; view = "record"; }} title={t().sqlViewRecord}>{r + 1}</button></td>
                      {#each row as v, i (i)}
                        <td class:num={kinds[i] === "num"} class:click={v !== "" && !(secret[i] && !reveal)} onclick={() => openCell(i, v)}>{@render value(v, i)}</td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            {@const row = result.rows[record] ?? []}
            <div class="box recordbox">
              {#if result.rows.length > 1}
                <div class="rnav">
                  <button type="button" class="btn small quiet" disabled={record === 0} onclick={() => record--} aria-label={t().sqlPrev}>‹</button>
                  <span class="meta">{t().sqlRecordOf(record + 1, result.rows.length)}</span>
                  <button type="button" class="btn small quiet" disabled={record >= result.rows.length - 1} onclick={() => record++} aria-label={t().sqlNext}>›</button>
                </div>
              {/if}
              <dl class="rec">
                {#each result.columns as c, i (i)}
                  <dt>{c}</dt>
                  <dd class:click={(row[i] ?? "") !== "" && !(secret[i] && !reveal)} class:mono={kinds[i] !== "bool"}>
                    <button type="button" class="cellbtn" onclick={() => openCell(i, row[i] ?? "")} disabled={(row[i] ?? "") === "" || (secret[i] && !reveal)}>
                      {@render value(row[i] ?? "", i)}
                    </button>
                  </dd>
                {/each}
              </dl>
            </div>
          {/if}
        {:else}
          <div class="box empty start">
            <p>{t().sqlStart}</p>
          </div>
        {/if}
      </div>
    </div>
  </div>
</section>

<Modal bind:open={cellOpen} id="sql-cell" wide>
  {#snippet heading()}<span class="mono">{cell.col}</span>{/snippet}
  <div class="m-body">
    <pre class="cellval">{pretty(cell.value, cell.kind)}</pre>
  </div>
  <div class="m-foot">
    <span class="muted small">{t().sqlChars(cell.value.length)}</span>
    <span class="spacer"></span>
    <button type="button" class="btn" onclick={copy}>{copied ? t().copied : t().copy}</button>
  </div>
</Modal>

<style>
  .sql { min-width: 0; }
  .ro { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; padding: 3px 10px; border-radius: 999px;
    background: color-mix(in oklch, var(--ok) 12%, var(--surface)); color: var(--ok-text); white-space: nowrap; }
  .layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: var(--space-4); align-items: start; margin-top: var(--space-3); min-width: 0; }
  .muted { color: var(--muted); }
  .small { font-size: 12.5px; }
  .mono { font-family: var(--mono); }
  .spacer { flex: 1; }
  .err { color: var(--bad-text); }
  .pad { padding: var(--space-3); margin: 0; font-size: 13.5px; }

  /* Tablas */
  .side { position: sticky; top: 72px; display: flex; flex-direction: column; max-height: calc(100vh - 110px); overflow: hidden; }
  .find { display: flex; align-items: center; gap: 8px; padding: 0 var(--space-3); border-bottom: 1px solid var(--line); color: var(--muted); }
  .find input { flex: 1; min-width: 0; font: 13.5px var(--sans); color: var(--ink); background: transparent; border: 0; padding: 10px 0; outline: none; }
  .tlist { list-style: none; margin: 0; padding: var(--space-1); overflow: auto; }
  .tlist li.sk { height: 26px; margin: 6px 8px; border-radius: 6px; background: var(--sunken); }
  .trow {
    display: flex; align-items: center; gap: 6px; width: 100%; text-align: left; border: 0; background: transparent;
    padding: 6px 8px; border-radius: 6px; cursor: pointer; color: var(--ink); font: 13px var(--mono);
  }
  .trow:hover { background: var(--sunken); }
  .open > .trow { background: color-mix(in oklch, var(--accent) 9%, transparent); }
  .chev { color: var(--muted); flex: none; transition: transform 150ms var(--ease); }
  .open .chev { transform: rotate(90deg); }
  .tn { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rows { color: var(--muted); font: 12px var(--sans); font-variant-numeric: tabular-nums; }
  .rows.zero { opacity: 0.55; }
  .tdetail { padding: 4px 8px 10px 25px; display: grid; gap: 8px; justify-items: start; }
  .cols { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; width: 100%; }
  .cols li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-2); font: 12px var(--mono); }
  .cn { color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cn.sens::after { content: " ●"; color: var(--warn-text); font-size: 9px; }
  .ct { color: var(--muted); white-space: nowrap; font-size: 11px; max-width: 110px; overflow: hidden; text-overflow: ellipsis; }

  /* Editor */
  .main { display: grid; gap: var(--space-3); min-width: 0; }
  .editor { display: grid; gap: var(--space-2); }
  textarea {
    width: 100%; resize: vertical; min-height: 96px; font: 13.5px/1.55 var(--mono); color: var(--term-ink); background: var(--term);
    border: 1px solid var(--line); border-radius: 10px; padding: var(--space-3) var(--space-4);
  }
  textarea:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 25%, transparent); border-color: var(--accent); }
  textarea::placeholder { color: var(--term-muted); }
  .bar, .rbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
  .hint { font-size: 12.5px; }
  kbd { font: 11px var(--mono); opacity: 0.8; margin-left: 4px; }
  .hist { position: relative; }
  .hmenu {
    position: absolute; z-index: 20; top: calc(100% + 4px); left: 0; width: min(560px, 80vw); max-height: 320px; overflow: auto;
    list-style: none; margin: 0; padding: 4px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
    box-shadow: 0 16px 40px -20px oklch(0.1 0.02 262 / 0.5);
  }
  .hmenu button {
    display: block; width: 100%; text-align: left; border: 0; background: transparent; padding: 7px 10px; border-radius: 6px;
    font: 12.5px var(--mono); color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;
  }
  .hmenu button:hover { background: var(--sunken); }

  /* Resultado */
  .result { min-width: 0; display: grid; gap: var(--space-2); }
  .meta { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .empty { padding: var(--space-5); color: var(--muted); font-size: 14px; margin: 0; }
  .start { text-align: center; }
  .start p { margin: 0; }
  .errbox { margin: 0; padding: var(--space-3) var(--space-4); color: var(--bad-text); font: 13px var(--mono);
    border-color: color-mix(in oklch, var(--bad) 35%, var(--line)); background: color-mix(in oklch, var(--bad) 6%, var(--surface)); }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); }
  .seg button { font: 500 12.5px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px; padding: 6px 10px; cursor: pointer; }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }

  /* La tabla vive en su caja: scroll propio, encabezado y primera columna fijos. */
  .grid-wrap { overflow: auto; max-height: min(62vh, 640px); padding: 0; max-width: 100%; }
  table { border-collapse: separate; border-spacing: 0; font: 12.5px var(--mono); min-width: 100%; }
  th { position: sticky; top: 0; z-index: 2; background: var(--sunken); text-align: left; font-weight: 600; color: var(--ink); }
  th, td { padding: 7px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; max-width: 320px; overflow: hidden; text-overflow: ellipsis; }
  th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .rn { position: sticky; left: 0; z-index: 1; background: var(--surface); color: var(--muted); text-align: right; min-width: 44px; border-right: 1px solid var(--line); }
  th.rn { z-index: 3; background: var(--sunken); }
  tbody tr:hover td { background: color-mix(in oklch, var(--accent) 5%, var(--surface)); }
  tbody tr:hover td.rn { background: color-mix(in oklch, var(--accent) 8%, var(--surface)); }
  td.click { cursor: pointer; }
  .rlink { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
  .rlink:hover { color: var(--accent); text-decoration: underline; }
  .lock { color: var(--warn-text); font-size: 9px; margin-left: 4px; vertical-align: middle; }
  .null { color: var(--muted); font-style: italic; opacity: 0.7; }
  .masked { color: var(--muted); letter-spacing: 1px; }
  .yes { color: var(--ok-text); }
  .no { color: var(--muted); }

  /* Registro: campo por campo */
  .recordbox { padding: 0; overflow: hidden; }
  .rnav { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--line); background: var(--sunken); }
  .rec { display: grid; grid-template-columns: minmax(140px, 240px) minmax(0, 1fr); margin: 0; max-height: min(62vh, 640px); overflow: auto; }
  .rec dt, .rec dd { padding: 7px var(--space-4); border-bottom: 1px solid var(--line); margin: 0; font-size: 13px; }
  .rec dt { font: 12.5px var(--mono); color: var(--muted); background: color-mix(in oklch, var(--sunken) 50%, var(--surface)); overflow-wrap: anywhere; }
  .rec dd { min-width: 0; }
  .rec dd.mono { font-family: var(--mono); font-size: 12.5px; }
  .cellbtn { all: unset; display: block; width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
  .cellbtn:disabled { cursor: default; }
  .cellbtn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }

  .cellval { margin: 0; max-height: 55vh; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font: 12.5px/1.6 var(--mono);
    background: var(--sunken); border-radius: 8px; padding: var(--space-3) var(--space-4); }

  @media (max-width: 900px) {
    .layout { grid-template-columns: minmax(0, 1fr); }
    .side { position: static; max-height: 280px; }
  }
</style>
