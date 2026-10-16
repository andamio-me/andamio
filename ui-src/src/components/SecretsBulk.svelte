<!--
  Varias variables de una vez: pegas un .env (o eliges el archivo) y ves, línea por línea, cuáles
  son nuevas, cuáles reemplazan y cuáles tienen un problema, sin que se lea ningún valor (el texto
  va oculto, con un botón para verlo). Guardar corre `andamio app secret import <app> -`: los
  valores entran por stdin, un commit con solo los nombres y un solo reinicio.
-->
<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import { guard } from "../lib/guard.svelte";

  let { app, secrets, onclose, ondone }: { app: string; secrets: string[]; onclose: () => void; ondone: () => void } = $props();

  const RESERVED = ["DOMAIN", "DATABASE_URL", "REDIS_URL", "TAG"];
  let text = $state("");
  let show = $state(false);
  let area: HTMLTextAreaElement | undefined = $state();
  $effect(() => { area?.focus(); });
  $effect(() => guard(() => text.trim() !== "" && !job.locked));

  type Line = { n: number; key: string; value: string; error: string | null; replaces: boolean; dup: boolean };
  // Como un .env: CLAVE=valor, "export" opcional, comillas alrededor del valor, # comentarios.
  const lines = $derived.by(() => {
    const out: Line[] = [];
    const s = t();
    text.split(/\r?\n/).forEach((raw, i) => {
      const l = raw.trim();
      if (!l || l.startsWith("#")) return;
      const body = l.replace(/^export\s+/, "");
      const eq = body.indexOf("=");
      const key = (eq < 0 ? body : body.slice(0, eq)).trim();
      let value = eq < 0 ? "" : body.slice(eq + 1).trim();
      if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) value = value.slice(1, -1);
      const error = eq < 0 || !/^[A-Z][A-Z0-9_]*$/.test(key) ? s.bulkBadLine
        : RESERVED.includes(key) ? s.reservedSecret(key)
        : !value ? s.bulkEmpty
        : value.length > 4096 ? s.bulkTooLong : null;
      out.push({ n: i + 1, key: key.slice(0, 60), value, error, replaces: secrets.includes(key), dup: false });
    });
    // Una clave repetida: vale la última (como en un .env).
    const last = new Map(out.map((l, i) => [l.key, i]));
    out.forEach((l, i) => { if (!l.error && last.get(l.key) !== i) l.dup = true; });
    return out;
  });
  const good = $derived(lines.filter((l) => !l.error && !l.dup));
  const bad = $derived(lines.filter((l) => l.error).length);

  async function pickFile(e: Event) {
    const f = (e.currentTarget as HTMLInputElement).files?.[0];
    (e.currentTarget as HTMLInputElement).value = "";
    if (f && f.size < 256 * 1024) text = (text.trim() ? text.replace(/\s*$/, "\n") : "") + (await f.text());
  }

  function save() {
    if (bad || !good.length) return;
    job.arm({ action: "secret-import", app, pairs: good.map((l) => ({ key: l.key, value: l.value })) }, (ok) => ok && ondone());
    text = "";   // los valores ya están en la acción; aquí no se quedan
    onclose();
  }
  function cancel() {
    text = "";
    onclose();
  }
</script>

<div class="bulk">
  <div class="top">
    <label for="bulk-text" class="lbl">{t().bulkLabel}</label>
    <div class="tools">
      <label class="btn small quiet file">
        {t().bulkFromFile}
        <input type="file" accept=".env,text/plain,.txt" onchange={pickFile} />
      </label>
      <button type="button" class="btn small quiet" onclick={() => (show = !show)} aria-pressed={show}>{show ? t().bulkHide : t().bulkShow}</button>
    </div>
  </div>
  <textarea id="bulk-text" bind:this={area} bind:value={text} class:hidden={!show} rows="6" spellcheck="false" autocomplete="off"
    placeholder={"API_KEY=…\nSMTP_PASSWORD=…"} aria-describedby="bulk-help"></textarea>
  <p id="bulk-help" class="help">{t().bulkHint}</p>

  {#if lines.length}
    <ul class="preview" aria-label={t().bulkPreview}>
      {#each lines as l (l.n)}
        <li class:err={l.error} class:dup={l.dup}>
          <span class="ln num">{l.n}</span>
          <code>{l.key || "—"}</code>
          {#if l.error}<span class="st bad">{l.error}</span>
          {:else if l.dup}<span class="st">{t().bulkDup}</span>
          {:else if l.replaces}<span class="st warn">{t().bulkReplace}</span>
          {:else}<span class="st ok">{t().bulkNew}</span>{/if}
        </li>
      {/each}
    </ul>
  {/if}

  <div class="foot">
    <span class="help">{bad ? t().bulkFix(bad) : good.length ? t().secretRestart : ""}</span>
    <div class="acts">
      <button type="button" class="btn small quiet" onclick={cancel}>{t().cancel}</button>
      <button type="button" class="btn small primary" onclick={save} disabled={job.locked || bad > 0 || !good.length}>{t().bulkSave(good.length)}</button>
    </div>
  </div>
</div>

<style>
  .bulk { display: grid; gap: var(--space-2); padding: var(--space-4); background: var(--sunken); border-bottom: 1px solid var(--line); }
  .top { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--space-2); }
  .tools { display: flex; gap: var(--space-1); }
  .lbl { font-size: 12.5px; color: var(--muted); }
  .file { position: relative; cursor: pointer; }
  .file input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
  .file:focus-within { outline: 3px solid color-mix(in oklch, var(--accent) 28%, transparent); }
  textarea {
    font: 13px/1.55 var(--mono); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 8px 10px; width: 100%; resize: vertical; min-height: 120px;
  }
  textarea.hidden { -webkit-text-security: disc; }
  textarea:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 28%, transparent); outline-offset: 0; border-color: var(--accent); }
  .help { font-size: 12.5px; color: var(--muted); margin: 0; }
  .preview { list-style: none; margin: 0; padding: 0; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); max-height: 240px; overflow: auto; }
  .preview li { display: flex; align-items: center; gap: var(--space-3); padding: 6px var(--space-3); border-bottom: 1px solid var(--line); font-size: 13px; }
  .preview li:last-child { border-bottom: 0; }
  .preview li.dup { opacity: 0.6; }
  .ln { width: 24px; color: var(--muted); font-size: 12px; text-align: right; flex: none; }
  .num { font-variant-numeric: tabular-nums; }
  .preview code { font-weight: 600; font-size: 12.5px; min-width: 160px; overflow-wrap: anywhere; }
  .st { margin-left: auto; font-size: 12.5px; color: var(--muted); text-align: right; }
  .st.ok { color: var(--ok-text); }
  .st.warn { color: var(--warn-text); }
  .st.bad { color: var(--bad-text); }
  .foot { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--space-2); }
  .acts { display: flex; gap: var(--space-1); margin-left: auto; }
</style>
