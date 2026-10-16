<!--
  Los secretos de una app, en su propia sección: cada uno es una fila con su nombre (el valor
  no se muestra nunca), Cambiar y Quitar. Agregar o cambiar abre una fila con el nombre y el
  valor en un campo oculto; el valor entra al comando por stdin.
-->
<script lang="ts">
  import { SECRET_TYPE, noSave } from "../lib/secret";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import { guard } from "../lib/guard.svelte";

  import * as api from "../lib/api";
  import SecretsBulk from "./SecretsBulk.svelte";

  // autoCheck: el último deploy falló (lo típico: falta una variable); se revisa solo.
  let { app, secrets, ondone, autoCheck = false }: { app: string; secrets: string[]; ondone: () => void; autoCheck?: boolean } = $props();

  // Variables que usa el código y no tiene como secreto (clona su repo: tarda unos segundos).
  let check = $state<api.EnvCheck | null>(null);
  let checking = $state(false);
  async function runCheck() {
    checking = true;
    try { check = await api.envCheck(app); } catch (e) { check = { used: [], missing: [], have: [], error: String((e as Error).message) }; }
    finally { checking = false; }
  }
  $effect(() => { if (autoCheck && !check && !checking) void runCheck(); });

  const RESERVED = ["DOMAIN", "DATABASE_URL", "REDIS_URL", "TAG"];
  let open = $state(false);
  let bulk = $state(false);   // varias de una vez (un .env)
  let fixedKey = $state(false);   // Cambiar: el nombre ya está y no se edita
  let key = $state("");
  let value = $state("");
  let keyError = $state<string | null>(null);
  let valueError = $state<string | null>(null);
  let keyInput: HTMLInputElement | undefined = $state();
  let valueInput: HTMLInputElement | undefined = $state();
  // Un valor escrito y sin guardar: antes de irte, el panel pregunta.
  $effect(() => guard(() => open && value !== "" && !job.locked));

  function start(k = "") {
    key = k;
    fixedKey = Boolean(k);
    value = "";
    keyError = valueError = null;
    open = true;
    queueMicrotask(() => (k ? valueInput : keyInput)?.focus());
  }
  function close() {
    open = false;
    value = "";
  }

  const checkKey = () =>
    (keyError = !/^[A-Z][A-Z0-9_]*$/.test(key) ? t().badSecretName : RESERVED.includes(key) ? t().reservedSecret(key) : null);
  const checkValue = () => (valueError = !value || /[\r\n]/.test(value) ? t().badSecretValue : null);

  function submit(e: SubmitEvent) {
    e.preventDefault();
    if (checkKey() || checkValue()) return;
    job.arm({ action: "secret-set", app, key, value }, (ok) => ok && ondone());
    close();   // el valor ya está en la acción; aquí no se queda
  }
</script>

<section class="sec" aria-labelledby="secrets-title">
  <div class="shead">
    <div>
      <h2 id="secrets-title">{t().secrets}</h2>
      <p class="desc">{t().secretsDesc}</p>
    </div>
    {#if !open && !bulk}
      <div class="hb">
        <button type="button" class="btn small quiet" onclick={runCheck} disabled={checking} aria-busy={checking}
          title={t().envCheckHint}>{checking ? t().envChecking : t().envCheck}</button>
        <button type="button" class="btn small quiet" onclick={() => (bulk = true)} disabled={job.locked} title={t().bulkTitle}>{t().bulkOpen}</button>
        <button type="button" class="btn small" onclick={() => start()} disabled={job.locked}>{t().addSecret}</button>
      </div>
    {/if}
  </div>
  {#if check}
    <div class={`envres ${check.error ? "" : check.missing.length ? "bad" : "ok"}`} role="status">
      {#if check.error}
        <p>{check.error}</p>
      {:else if check.missing.length}
        <p><strong>{t().envMissingN(check.missing.length)}</strong> {t().envMissingHow}</p>
        <ul>
          {#each check.missing as m (m.key)}
            <li><code>{m.key}</code> <span class="muted">{t().envFound(m.where)}</span>
              <button type="button" class="btn small" onclick={() => start(m.key)} disabled={job.locked || open}>{t().add}</button></li>
          {/each}
        </ul>
      {:else}
        <p>{t().envAllGood(check.used.length)}</p>
      {/if}
      <button type="button" class="x" onclick={() => (check = null)} aria-label={t().close}>×</button>
    </div>
  {/if}

  <div class="box">
    {#if bulk}
      <SecretsBulk {app} {secrets} onclose={() => (bulk = false)} {ondone} />
    {/if}
    {#if open}
      <form class="row form-row" onsubmit={submit} autocomplete="off">
        <label class="f">
          <span class="lbl">{t().secretName}</span>
          <input bind:this={keyInput} bind:value={key} class="mono" readonly={fixedKey}
            oninput={() => (key = key.toUpperCase().replace(/[^A-Z0-9_]/g, "_"))} onblur={() => !fixedKey && key && checkKey()}
            aria-invalid={keyError ? "true" : undefined} aria-describedby="sk-help" spellcheck="false" required />
          <span id="sk-help" class="help" class:error={keyError}>
            {keyError ?? (secrets.includes(key) ? t().secretReplace(key) : t().secretNameHint)}
          </span>
        </label>
        <label class="f grow">
          <span class="lbl">{t().secretValue}</span>
          <input bind:this={valueInput} bind:value={value} type={SECRET_TYPE} {...noSave} class="secret-field" onblur={() => value && checkValue()}
            aria-invalid={valueError ? "true" : undefined} aria-describedby="sv-help" spellcheck="false" required />
          <span id="sv-help" class="help" class:error={valueError}>{valueError ?? t().secretValueHint}</span>
        </label>
        <div class="acts">
          <button type="submit" class="btn small primary" disabled={job.locked}>{t().save}</button>
          <button type="button" class="btn small quiet" onclick={close}>{t().cancel}</button>
        </div>
      </form>
    {/if}
    {#each secrets as s (s)}
      <div class="row">
        <code class="name">{s}</code>
        <span class="dots" aria-hidden="true">••••••••</span>
        <span class="acts">
          <button type="button" class="btn small quiet" onclick={() => start(s)} disabled={job.locked} aria-label={t().change(s)}>{t().changeShort}</button>
          <button type="button" class="btn small quiet danger" disabled={job.locked} aria-label={t().removeX(s)}
            onclick={() => job.arm({ action: "secret-rm", app, key: s }, (ok) => ok && ondone())}>{t().remove}</button>
        </span>
      </div>
    {:else}
      {#if !open && !bulk}
        <div class="emptyst">
          <p>{t().secretsEmptyLead}</p>
          <div class="eacts">
            <button type="button" class="btn small" onclick={() => (bulk = true)} disabled={job.locked}>{t().bulkOpen}</button>
            <button type="button" class="btn small quiet" onclick={() => start()} disabled={job.locked}>{t().addSecret}</button>
            <button type="button" class="btn small quiet" onclick={runCheck} disabled={checking}>{checking ? t().envChecking : t().envCheck}</button>
          </div>
        </div>
      {/if}
    {/each}
  </div>
</section>

<style>
  .hb { display: flex; gap: var(--space-2); }
  .envres { position: relative; margin-bottom: var(--space-3); padding: var(--space-3) var(--space-5) var(--space-3) var(--space-4); border-radius: 10px; font-size: 14px;
    border: 1px solid var(--line); background: var(--surface); }
  .envres.ok { border-color: color-mix(in oklch, var(--ok) 35%, var(--line)); background: color-mix(in oklch, var(--ok) 7%, var(--surface)); }
  .envres.bad { border-color: color-mix(in oklch, var(--warn) 45%, var(--line)); background: color-mix(in oklch, var(--warn) 8%, var(--surface)); }
  .envres p { margin: 0; }
  .envres ul { list-style: none; margin: var(--space-2) 0 0; padding: 0; display: grid; gap: 6px; }
  .envres li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
  .envres .muted { color: var(--muted); font-size: 13px; }
  .envres .x { position: absolute; top: 6px; right: 8px; border: 0; background: transparent; color: var(--muted); font-size: 18px; cursor: pointer; line-height: 1; }
  .row { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2) var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); margin: 0; }
  .row:last-child { border-bottom: 0; }
  .name { font-size: 13px; font-weight: 600; min-width: 180px; }
  .dots { color: var(--muted); letter-spacing: 2px; flex: 1; }
  .acts { display: flex; gap: var(--space-1); margin-left: auto; }
  .empty { color: var(--muted); font-size: 14px; }
  .form-row { align-items: flex-start; background: var(--sunken); }
  .f { display: grid; gap: 5px; min-width: 220px; }
  .f.grow { flex: 1; }
  .lbl { font-size: 12.5px; color: var(--muted); }
  .f input {
    font: 14px var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 7px 10px; width: 100%;
  }
  .f input.mono { font-family: var(--mono); font-size: 13px; }
  .f input[readonly] { color: var(--muted); background: var(--sunken); }
  .f input:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 28%, transparent); outline-offset: 0; border-color: var(--accent); }
  .f input[aria-invalid="true"] { border-color: var(--bad); }
  .help { font-size: 12.5px; color: var(--muted); }
  .help.error { color: var(--bad-text); }
  .form-row .acts { align-self: center; margin-top: 18px; }
  .emptyst { padding: var(--space-5); display: grid; gap: var(--space-3); }
  .emptyst p { margin: 0; color: var(--muted); max-width: 64ch; font-size: 14px; }
  .eacts { display: flex; flex-wrap: wrap; gap: var(--space-2); }
</style>
