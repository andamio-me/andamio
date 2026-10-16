<!--
  Logs en vivo de la app: las últimas 200, 1000 o 5000 líneas y lo que vaya saliendo. Cada línea
  con su hora (la de Docker, en tu zona), una etiqueta de nivel con color (como Railway) y los
  colores del programa (ver lib/logline.ts). Sigue sola al final; si subes para leer, deja de
  seguir y un botón te dice cuántas líneas nuevas hay. Se buscan mientras escribes, se filtran por
  nivel, se ajustan las líneas largas y se descargan (lo que estás viendo, como .txt).
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import { parseLog, type LogLine, type Seg } from "../lib/logline";

  let { app, worker = false, tall = false }: { app: string; worker?: boolean; tall?: boolean } = $props();
  let service = $state<"app" | "worker">("app");

  type L = LogLine;
  const TAILS = [200, 1000, 5000] as const;
  const MAX = 6000;
  const BADGE = { error: "ERR", warn: "WARN", info: "INFO", debug: "DBG", "": "" } as const;

  let lines = $state<L[]>([]);
  let status = $state<"connecting" | "live" | "ended" | "lost">("connecting");
  let tail = $state<(typeof TAILS)[number]>(200);
  let query = $state("");
  let minLevel = $state<"all" | "warn" | "error">("all");
  let wrap = $state(true);
  let follow = $state(true);      // pegado al final
  let unseen = $state(0);         // líneas nuevas mientras lees más arriba
  let box: HTMLElement | undefined = $state();

  $effect(() => {
    const a = app, n = tail, svc = service;
    lines = [];
    status = "connecting";
    unseen = 0;
    follow = true;
    const es = new EventSource(`/api/logs/${encodeURIComponent(a)}?tail=${n}&service=${svc}`);
    const add = (l: L) => {
      status = "live";
      lines.push(l);
      if (lines.length > MAX) lines.splice(0, lines.length - MAX);
      if (!follow) unseen++;
    };
    es.onmessage = (e) => add(parseLog(JSON.parse(e.data), lines[lines.length - 1]));
    es.addEventListener("end", () => { status = "ended"; es.close(); });
    es.onerror = () => { if (es.readyState !== EventSource.CLOSED) status = "lost"; };
    es.onopen = () => { if (status === "lost") status = "live"; };
    return () => es.close();
  });

  const needle = $derived(query.trim().toLowerCase());
  const filtering = $derived(Boolean(needle) || minLevel !== "all");
  const levelOk = (l: L) => minLevel === "all" || l.level === "error" || (minLevel === "warn" && l.level === "warn");
  const shown = $derived(filtering
    ? lines.filter((l) => (!needle || l.text.toLowerCase().includes(needle)) && levelOk(l))
    : lines);
  const errorCount = $derived(lines.filter((l) => l.level === "error").length);
  const warnCount = $derived(lines.filter((l) => l.level === "warn").length);

  /** La línea en partes (sus colores), con lo que buscas marcado. Sin HTML: cada parte es texto. */
  function parts(segs: Seg[]): (Seg & { hit: boolean })[] {
    if (!needle) return segs.map((x) => ({ ...x, hit: false }));
    const out: (Seg & { hit: boolean })[] = [];
    for (const { s, c } of segs) {
      const low = s.toLowerCase();
      let i = 0;
      for (let j = low.indexOf(needle); j !== -1; j = low.indexOf(needle, i)) {
        if (j > i) out.push({ s: s.slice(i, j), c, hit: false });
        out.push({ s: s.slice(j, j + needle.length), c, hit: true });
        i = j + needle.length;
      }
      if (i < s.length) out.push({ s: s.slice(i), c, hit: false });
    }
    return out;
  }

  // Pegado al final mientras sigues; al subir para leer, deja de seguir.
  $effect(() => {
    void shown.length;
    if (follow && box) box.scrollTop = box.scrollHeight;
  });
  function onScroll() {
    if (!box) return;
    const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 24;
    if (atEnd !== follow) follow = atEnd;
    if (atEnd) unseen = 0;
  }
  function toEnd() {
    follow = true;
    unseen = 0;
    if (box) box.scrollTop = box.scrollHeight;
  }

  const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  const fullFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" });

  function download() {
    const text = shown.map((l) => (l.ts ? `${new Date(l.ts).toISOString()} ` : "") + l.text).join("\n") + "\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = `${app}-logs-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.txt`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  const statusText = $derived(status === "live" ? t().logsLive : status === "connecting" ? t().connecting : status === "ended" ? t().logsEnded : t().logsLost);
</script>

<section class="logs" aria-labelledby="logs-title">
  <div class="bar">
    <h2 id="logs-title">{t().logs}</h2>
    <span class={`live ${status}`} role="status"><span class="ldot" aria-hidden="true"></span>{statusText}</span>
    {#if worker}
      <div class="seg" role="radiogroup" aria-label={t().logService}>
        {#each [["app", "web"], ["worker", "worker"]] as [v, label] (v)}
          <button type="button" role="radio" aria-checked={service === v} class:on={service === v}
            onclick={() => (service = v as "app" | "worker")}>{label}</button>
        {/each}
      </div>
    {/if}
    <span class="spacer"></span>
    <div class="seg" role="radiogroup" aria-label={t().logLines}>
      {#each TAILS as n (n)}
        <button type="button" role="radio" aria-checked={tail === n} class:on={tail === n} onclick={() => (tail = n)}>{n}</button>
      {/each}
    </div>
    <button type="button" class="btn small quiet" onclick={() => (wrap = !wrap)} aria-pressed={wrap} title={t().logsWrapHint}>{wrap ? t().logsNoWrap : t().logsWrap}</button>
    <button type="button" class="btn small quiet" onclick={download} disabled={!shown.length}>{t().download}</button>
    <button type="button" class="btn small quiet" onclick={() => { lines = []; unseen = 0; }}>{t().clear}</button>
  </div>
  <div class="find">
    <label class="search">
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
      <span class="sr-only">{t().searchLogs}</span>
      <input type="search" bind:value={query} placeholder={t().searchLogs} spellcheck="false" autocomplete="off"
        onkeydown={(e) => { if (e.key === "Escape") query = ""; }} />
    </label>
    <div class="seg" role="radiogroup" aria-label={t().logLevel}>
      <button type="button" role="radio" aria-checked={minLevel === "all"} class:on={minLevel === "all"} onclick={() => (minLevel = "all")}>{t().logAll}</button>
      <button type="button" role="radio" aria-checked={minLevel === "warn"} class:on={minLevel === "warn"} onclick={() => (minLevel = "warn")}>
        {t().logWarnsUp}{#if warnCount + errorCount}<span class="ncount warn">{warnCount + errorCount}</span>{/if}
      </button>
      <button type="button" role="radio" aria-checked={minLevel === "error"} class:on={minLevel === "error"} onclick={() => (minLevel = "error")}>
        {t().logErrors}{#if errorCount}<span class="ncount bad">{errorCount}</span>{/if}
      </button>
    </div>
    {#if filtering}<span class="count" aria-live="polite">{t().logMatches(shown.length, lines.length)}</span>{/if}
  </div>

  <div class="term" class:tall>
    <!-- Con teclado se puede enfocar para desplazarse por los logs (una región que se desplaza). -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="out" class:nowrap={!wrap} bind:this={box} onscroll={onScroll} tabindex="0" role="log" aria-label={t().logs}>
      {#each shown as l, i (i)}
        <div class={`ln ${l.level}`} class:cont={l.cont}>
          <span class="ts" title={l.ts ? fullFmt.format(l.ts) : undefined}>{l.ts ? timeFmt.format(l.ts) : ""}</span>
          <span class={`lv ${l.level}`}>{l.cont ? "" : BADGE[l.level]}</span>
          <span class="tx">{#each parts(l.segs) as p, k (k)}{#if p.hit}<mark class={p.c}>{p.s}</mark>{:else if p.c}<span class={p.c}>{p.s}</span>{:else}{p.s}{/if}{/each}</span>
        </div>
      {:else}
        <p class="sys">{status === "connecting" ? t().connecting : filtering ? t().noLogMatches : status === "ended" ? t().ended : t().logsEmpty}</p>
      {/each}
    </div>
    {#if !follow}
      <button type="button" class="jump" onclick={toEnd}>
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M8 3v10M3.5 8.5L8 13l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {unseen ? t().logsNew(unseen) : t().logsToEnd}
      </button>
    {/if}
  </div>
</section>

<style>
  .logs { margin-top: 0; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
  .bar h2 { margin: 0; }
  .spacer { flex: 1; }
  .live { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted); padding: 3px 9px; border-radius: 999px; background: var(--sunken); }
  .ldot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
  .live.live { color: var(--ok-text); background: color-mix(in oklch, var(--ok) 12%, var(--surface)); }
  .live.live .ldot { background: var(--ok); }
  .live.lost { color: var(--warn-text); background: color-mix(in oklch, var(--warn) 12%, var(--surface)); }
  .live.lost .ldot { background: var(--warn); }
  @media (prefers-reduced-motion: no-preference) {
    .live.live .ldot, .live.connecting .ldot { animation: beat 1.6s ease-in-out infinite; }
  }
  @keyframes beat { 50% { opacity: 0.3; } }
  .find { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-4); margin-bottom: var(--space-2); }
  .search {
    flex: 1; min-width: 220px; display: flex; align-items: center; gap: var(--space-2); padding: 0 var(--space-3);
    border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--muted);
  }
  .search:focus-within { border-color: var(--accent); outline: 3px solid color-mix(in oklch, var(--accent) 22%, transparent); }
  .search input { flex: 1; border: 0; outline: 0; background: transparent; color: var(--ink); font: 14px var(--sans); padding: 8px 0; min-width: 0; }
  .ncount { margin-left: 6px; font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 999px; }
  .ncount.warn { background: color-mix(in oklch, var(--warn) 18%, var(--surface)); color: var(--warn-text); }
  .ncount.bad { background: color-mix(in oklch, var(--bad) 15%, var(--surface)); color: var(--bad-text); }
  .count { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); }
  .seg button {
    font: 500 12.5px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px;
    padding: 6px 9px; cursor: pointer; font-variant-numeric: tabular-nums;
  }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }

  .term { position: relative; }
  .out {
    height: 380px; overflow: auto; background: var(--term); color: var(--term-ink); border-radius: 12px;
    padding: var(--space-3) 0; font: 12.5px/1.65 var(--mono);
  }
  .tall .out { height: max(380px, calc(100vh - 300px)); }
  .ln { display: grid; grid-template-columns: 76px 40px minmax(0, 1fr); gap: var(--space-3); padding: 0 var(--space-5) 0 var(--space-3); }
  .ln:hover { background: oklch(1 0 0 / 0.04); }
  .ts { color: var(--term-muted); text-align: right; font-variant-numeric: tabular-nums; user-select: none; }
  .tx { white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; }
  .nowrap .tx { white-space: pre; overflow-wrap: normal; }
  .nowrap .ln { width: max-content; min-width: 100%; }
  .ln.error { background: oklch(0.6 0.2 25 / 0.12); }
  .ln.error .tx { color: var(--term-bad); }
  .ln.warn { background: oklch(0.8 0.14 80 / 0.06); }
  .ln.warn .tx { color: var(--term-warn); }
  .ln.debug .tx { color: var(--term-muted); }
  /* Nivel: una etiqueta corta con color, como Railway. */
  .lv { font: 600 10.5px/1.65 var(--mono); letter-spacing: 0.04em; text-align: center; align-self: start; margin-top: 2px;
    border-radius: 4px; user-select: none; }
  .lv:empty { visibility: hidden; }
  .lv.info { color: var(--term-info); background: oklch(0.7 0.12 245 / 0.14); }
  .lv.warn { color: var(--term-warn); background: oklch(0.8 0.14 80 / 0.16); }
  .lv.error { color: oklch(0.2 0.02 262); background: var(--term-bad); }
  .lv.debug { color: var(--term-debug); background: oklch(0.7 0.1 300 / 0.14); }
  /* Las partes: el contexto de Nest y los colores ANSI del programa. */
  .ctx { color: var(--term-ctx); }
  .a-b { font-weight: 700; }
  .a-d { opacity: 0.65; }
  .a-black { color: var(--term-muted); }
  .a-red { color: var(--term-bad); }
  .a-green { color: var(--term-ok); }
  .a-yellow { color: var(--term-warn); }
  .a-blue { color: var(--term-info); }
  .a-magenta { color: var(--term-debug); }
  .a-cyan { color: var(--term-ctx); }
  .a-white { color: var(--term-ink); }
  .sys { color: var(--term-muted); margin: 0; padding: 0 var(--space-5); }
  mark { background: oklch(0.83 0.13 85 / 0.35); color: inherit; border-radius: 2px; padding: 0 1px; }
  .jump {
    position: absolute; left: 50%; bottom: 14px; transform: translateX(-50%); display: inline-flex; align-items: center; gap: 6px;
    font: 500 13px var(--sans); color: var(--accent-ink); background: var(--accent); border: 0; border-radius: 999px;
    padding: 7px 14px; cursor: pointer; box-shadow: 0 10px 24px -12px oklch(0.1 0.02 262 / 0.7);
  }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
