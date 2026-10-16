<!--
  La terminal de acciones. Primero el comando exacto con su $ (antes de correrlo, para que sepas
  qué va a pasar), después la salida real en vivo y, si andamio necesita tu contraseña de sudo,
  la pide aquí mismo, como tu terminal.
  Acciones cortas: sube desde abajo y la página se puede seguir mirando (sin lanzar otra acción).
  Acciones largas o delicadas (crear, borrar, restaurar…): va al centro, en una ventana nativa
  (el resto de la página queda inerte) y no se cierra hasta que termina.
-->
<script lang="ts">
  import { SECRET_TYPE, noSave } from "../lib/secret";
  import { job } from "../lib/job.svelte";
  import { t } from "../lib/i18n.svelte";

  let { user }: { user: string } = $props();

  let body: HTMLElement | undefined = $state();
  let pwInput: HTMLInputElement | undefined = $state();
  let runBtn: HTMLButtonElement | undefined = $state();
  let dialog: HTMLDialogElement | undefined = $state();
  let password = $state("");

  // Etapas de una acción larga (crear): progreso arriba; la salida completa, plegada.
  const STAGES: Record<string, string[]> = { create: ["review", "register", "server", "pipeline", "deploy"] };
  const stageList = $derived(STAGES[job.kind] ?? []);
  const seen = $derived(job.stages);
  let showLog = $state(false);
  let clock = $state(Date.now());
  $effect(() => {
    if (!job.busy) return;
    const i = setInterval(() => (clock = Date.now()), 1000);
    return () => clearInterval(i);
  });
  function stageState(k: string): "done" | "run" | "bad" | "todo" | "skip" {
    const i = seen.indexOf(k), last = seen[seen.length - 1];
    if (i < 0) return job.phase === "done" && job.rc === 0 ? "skip" : "todo";
    if (k !== last) return "done";
    if (job.phase === "done") return job.rc === 0 ? "done" : "bad";
    return "run";
  }
  function stageTime(k: string): string {
    const start = job.stageAt[k];
    if (!start) return "";
    const next = stageList.slice(stageList.indexOf(k) + 1).map((x) => job.stageAt[x]).find(Boolean);
    const end = next ?? (job.phase === "done" ? (job.endedAt || clock) : clock);
    const s = Math.max(0, (end - start) / 1000);
    return s < 60 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
  }

  // Modo centrado: una ventana modal mientras dure (y hasta que la cierres).
  $effect(() => {
    if (!dialog) return;
    if (job.open && job.critical && !job.minimized && !dialog.open) dialog.showModal();
    if (!(job.open && job.critical && !job.minimized) && dialog.open) dialog.close();
  });
  // Esc no la cierra a medias: solo cuando terminó o si todavía no corrió.
  const reopen = () => setTimeout(() => { if (dialog && !dialog.open && job.open && job.critical && !job.minimized) dialog.showModal(); }, 0);
  const oncancel = (e: Event) => {
    e.preventDefault();
    if (job.phase === "armed" || job.phase === "done") job.close();
    else reopen();   // si el navegador la cierra igual (Esc sin un clic antes), vuelve a abrirse
    // (para dejar de verla mientras corre está "Minimizar")
  };
  // Algunos navegadores cierran la ventana con Esc aunque se pida que no (un segundo Esc): si la
  // acción sigue, vuelve a abrirse; si ya terminó, eso es cerrarla.
  const onclose = () => {
    if (!(job.open && job.critical) || job.minimized) return;
    if (job.phase === "armed" || job.phase === "done") job.close();
    else reopen();
  };

  const phaseText = $derived.by(() => {
    switch (job.phase) {
      case "armed": return t().ready;
      case "starting": case "running": return t().workingNow;
      case "password": return t().waitingPw;
      case "done": return job.rc === 0 ? t().done : job.rc === 130 ? t().cancelled : t().failed(job.rc ?? 1);
      default: return "";
    }
  });
  const tone = $derived(job.phase === "done" ? (job.rc === 0 ? "ok" : "bad") : job.phase === "password" ? "warn" : "");

  // La salida sigue bajando sola; el foco va a lo que espera una respuesta.
  $effect(() => {
    void job.lines.length;
    if (body) body.scrollTop = body.scrollHeight;
  });
  $effect(() => {
    if (job.phase === "password") pwInput?.focus();
    if (job.phase === "armed") runBtn?.focus();
  });

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    const pw = password;
    password = "";
    if (pw) await job.password(pw);
  }

  // Esc cierra la terminal de abajo solo si no hay una ventana abierta encima (esa se cierra primero).
  function onkey(e: KeyboardEvent) {
    if (e.key !== "Escape" || job.critical || e.defaultPrevented || document.querySelector("dialog[open]")) return;
    if (job.phase === "armed" || job.phase === "done") job.close();
  }
  // Cerrar o recargar la pestaña mientras corre: el navegador pregunta (la acción seguiría en el
  // servidor; al volver, el panel se reconecta).
  const unload = (e: BeforeUnloadEvent) => {
    if (job.busy) e.preventDefault();
  };
</script>

<svelte:window onkeydown={onkey} onbeforeunload={unload} />

{#snippet content()}
    <header>
      <span class="title">{t().terminal}</span>
      <span class={`phase ${tone}`}>
        {#if job.busy}<span class="pulse" aria-hidden="true"></span>{/if}
        {phaseText}
      </span>
      {#key job.nudges}{#if job.nudges}<span class="nudge" role="status">{t().nudge}</span>{/if}{/key}
      <span class="spacer"></span>
      {#if job.busy && job.phase !== "password"}
        <button type="button" class="btn small quiet" onclick={() => job.minimize()} title={t().minimizeHint}>
          <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M3.5 12.5h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
          {t().minimize}
        </button>
      {/if}
      {#if job.phase === "armed"}
        <button type="button" class="btn small quiet" onclick={() => job.cancel()}>{t().cancel}</button>
        <button type="button" class="btn small primary" bind:this={runBtn} onclick={() => job.run()}>{t().run}</button>
      {:else if job.phase === "password"}
        <button type="button" class="btn small quiet" onclick={() => job.cancel()}>{t().cancel}</button>
      {:else if job.phase === "done"}
        <button type="button" class="btn small" onclick={() => job.close()}>{t().close}</button>
      {/if}
    </header>

    {#if stageList.length && seen.length}
      <ol class="stages">
        {#each stageList as k (k)}
          {@const st = stageState(k)}
          <li class={st}>
            <span class="sicon" aria-hidden="true">{#if st === "done"}✓{:else if st === "bad"}✗{:else if st === "run"}<span class="pulse"></span>{:else}○{/if}</span>
            <span class="sname">{t().stageName[k] ?? k}</span>
            <span class="stime">{stageTime(k)}</span>
          </li>
        {/each}
      </ol>
      <button type="button" class="logtoggle" onclick={() => (showLog = !showLog)} aria-expanded={showLog}>{showLog ? t().hideLog : t().showLog}</button>
    {/if}
    <div class="body" class:folded={stageList.length && seen.length && !showLog && job.phase !== "password"} bind:this={body}>
      <!-- Cada línea es un bloque: sin saltos de línea sueltos en el <pre> (darían líneas vacías). -->
      <pre>{#if job.phase === "armed"}<span class="line cmd"><span class="prompt" aria-hidden="true">$ </span>{job.command}</span><span class="line note">{t().sameAsCli}</span>{:else}{#each job.lines.filter((x) => x.kind !== "stage") as l, i (i)}<span class={`line ${l.kind}`}>{#if l.kind === "cmd"}<span class="prompt" aria-hidden="true">$ </span>{/if}{l.text || " "}</span>{/each}{/if}</pre>
      {#if job.phase === "password"}
        <form class="pw" onsubmit={submit}>
          <label for="sudo-pw">{job.prompt || t().pwLabel(user)}:</label>
          <input id="sudo-pw" bind:this={pwInput} bind:value={password} type={SECRET_TYPE} {...noSave} class="secret-field" spellcheck="false" required />
          <button type="submit" class="btn small">{t().pwSend}</button>
          <p class="hint">{t().pwNote}</p>
        </form>
      {/if}
    </div>
{/snippet}

{#if job.open && !job.critical && !job.minimized}
  <section class="sheet" aria-label={t().terminal} aria-live="polite">{@render content()}</section>
{/if}
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dialog} class="sheet center" aria-label={t().terminal} oncancel={oncancel} onclose={onclose}>
  {#if job.open && job.critical && !job.minimized}
    <div class="inner" aria-live="polite">{@render content()}</div>
    {#if job.phase === "done"}
      <p class="after">{job.rc === 0 ? t().criticalDone : job.rc === 130 ? t().criticalCancelled : t().criticalFailed}</p>
    {:else if job.busy}
      <p class="after">{t().criticalWait}</p>
    {/if}
  {/if}
</dialog>

<style>
  .sheet.center {
    position: fixed; inset: 0; margin: auto; padding: 0; border: 0; transform: none; height: fit-content;
    width: min(860px, calc(100vw - 2 * var(--space-4))); max-height: min(78vh, 720px);
  }
  .sheet.center:not([open]) { display: none; }
  .center::backdrop { background: oklch(0.12 0.02 262 / 0.62); }
  @supports (backdrop-filter: blur(2px)) { .center::backdrop { backdrop-filter: blur(2px); } }
  .center .inner { display: flex; flex-direction: column; min-height: 0; flex: 1; }
  .after { margin: 0; padding: var(--space-3) var(--space-5); border-top: 1px solid oklch(1 0 0 / 0.08); color: var(--term-muted); font-size: 13px; }
  @media (prefers-reduced-motion: no-preference) {
    .sheet.center[open] { animation: pop 200ms var(--ease); }
  }
  @keyframes pop { from { opacity: 0; transform: scale(0.98); } }
  .sheet {
    position: fixed; z-index: 30; left: 50%; bottom: var(--space-4);
    width: min(940px, calc(100vw - 2 * var(--space-4)));
    transform: translateX(-50%);
    background: var(--term); color: var(--term-ink); border-radius: 12px;
    box-shadow: 0 28px 64px -24px oklch(0.15 0.05 262 / 0.6), 0 0 0 1px oklch(1 0 0 / 0.06);
    display: flex; flex-direction: column; max-height: min(60vh, 560px);
  }
  @media (prefers-reduced-motion: no-preference) {
    .sheet { animation: rise 220ms var(--ease); }
  }
  @keyframes rise { from { transform: translate(-50%, 16px); opacity: 0; } }
  header {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-3) var(--space-3) var(--space-3) var(--space-5);
    border-bottom: 1px solid oklch(1 0 0 / 0.08);
  }
  .title { font-weight: 600; font-size: 14px; }
  .phase { display: inline-flex; align-items: center; gap: 7px; color: var(--term-muted); font-size: 13px; }
  .phase.ok { color: var(--term-ok); }
  .phase.bad { color: var(--term-bad); }
  .phase.warn { color: var(--term-warn); }
  .pulse { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
  @media (prefers-reduced-motion: no-preference) {
    .pulse { animation: pulse 1.2s ease-in-out infinite; }
  }
  @keyframes pulse { 50% { opacity: 0.25; } }
  .spacer { flex: 1; }
  .nudge { color: var(--term-warn); font-size: 13px; animation: nudge 3.5s var(--ease) forwards; }
  @keyframes nudge { 0%, 80% { opacity: 1; } 100% { opacity: 0; } }
  header :global(.btn) { background: oklch(1 0 0 / 0.06); border-color: oklch(1 0 0 / 0.12); color: var(--term-ink); }
  header :global(.btn.quiet) { background: transparent; border-color: transparent; color: var(--term-muted); }
  header :global(.btn.primary) { background: var(--chalk); border-color: var(--chalk); color: var(--print-deep); }
  .body { overflow: auto; padding: var(--space-4) var(--space-5) var(--space-5); }
  .body.folded pre { display: none; }
  .body.folded { padding: 0; }
  .stages { list-style: none; margin: 0; padding: var(--space-3) var(--space-5) var(--space-2); display: grid; gap: 6px; }
  .stages li { display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; align-items: center; gap: var(--space-3); font-size: 14px; color: var(--term-muted); }
  .stages li.done, .stages li.run { color: var(--term-ink); }
  .stages li.done .sicon { color: var(--term-ok); }
  .stages li.bad { color: var(--term-bad); }
  .stages li.run { font-weight: 600; }
  .stages li.run .sicon { color: var(--chalk); }
  .stages li.skip { opacity: 0.55; }
  .sicon { text-align: center; font-weight: 700; display: inline-grid; place-items: center; }
  .stime { font: 12.5px var(--mono); color: var(--term-muted); font-variant-numeric: tabular-nums; }
  .logtoggle { align-self: flex-start; margin: 0 var(--space-5) var(--space-2); font: 12.5px var(--sans); color: var(--term-muted); background: none; border: 0; padding: 4px 0; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
  .logtoggle:hover { color: var(--term-ink); }
  pre { margin: 0; font: 13px/1.75 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; }
  .line { display: block; color: var(--term-muted); }
  .line.cmd { color: var(--term-ink); margin-bottom: 4px; }
  .line.cmd:not(:first-child) { margin-top: var(--space-3); }
  .prompt { color: var(--term-muted); user-select: none; }
  .line.ok { color: var(--term-ok); }
  .line.bad { color: var(--term-bad); }
  .line.warn { color: var(--term-warn); }
  .line.step { color: var(--term-ink); font-weight: 600; margin-top: var(--space-2); }
  .line.note { color: var(--term-muted); font-family: var(--sans); font-size: 13px; margin-top: var(--space-2); }
  .pw { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); margin-top: var(--space-3); font: 13px var(--mono); }
  .pw label { color: var(--term-ink); }
  .pw input {
    font: 13px var(--mono); color: var(--term-ink); background: oklch(1 0 0 / 0.06);
    border: 1px solid oklch(1 0 0 / 0.16); border-radius: 6px; padding: 6px 10px; min-width: 220px;
  }
  .pw input:focus-visible { outline: 2px solid var(--chalk); outline-offset: 2px; }
  .pw :global(.btn) { background: oklch(1 0 0 / 0.08); border-color: oklch(1 0 0 / 0.16); color: var(--term-ink); }
  .hint { flex-basis: 100%; margin: 0; color: var(--term-muted); font: 12.5px/1.5 var(--sans); }
</style>
