<!--
  Una lista de app.yml que se edita desde el panel: dominios, orígenes CORS o carpetas
  persistentes. Una caja con su título y "Agregar" arriba; cada valor es una fila con Quitar.
  Agregar valida antes de correr nada; un dominio revisa primero su DNS.
-->
<script lang="ts">
  import { dns, type ListKind } from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";

  // fixed: un valor que siempre está y no se quita (la dirección que andamio le da a la app).
  let { app, kind, title, items, placeholder, ondone, fixed = "", note = "" }: {
    app: string; kind: ListKind; title: string; items: string[]; placeholder: string; ondone: () => void;
    fixed?: string; note?: string;
  } = $props();

  let adding = $state(false);
  let value = $state("");
  let error = $state<string | null>(null);
  let dnsState = $state<{ checking: boolean; ok?: boolean; ip?: string } | null>(null);
  let anyway = $state(false);
  let input: HTMLInputElement | undefined = $state();
  const id = $derived(`le-${kind}`);

  const SYSTEM = /^\/(bin|boot|dev|etc|lib|lib64|proc|root|run|sbin|sys|usr|var\/run)(\/|$)/;
  function check(v: string): string | null {
    if (kind === "domain") return /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/.test(v) ? null : t().badDomain;
    if (kind === "cors") {
      if (v === "*") return t().starOrigin;
      return /^https?:\/\/[a-z0-9.-]+(:[0-9]{1,5})?$/.test(v) ? null : t().badOrigin;
    }
    if (!/^(\/[A-Za-z0-9._-]+)+$/.test(v) || v.includes("..")) return t().badFolder;
    return SYSTEM.test(v) ? t().systemFolder : null;
  }
  const norm = (v: string) => (kind === "volume" ? v.trim().replace(/\/$/, "") : v.trim().toLowerCase().replace(/\/$/, ""));

  function open() {
    adding = true;
    value = "";
    error = null;
    dnsState = null;
    anyway = false;
    queueMicrotask(() => input?.focus());
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    const v = norm(value);
    error = check(v);
    if (error) return;
    if (kind === "domain" && !anyway) {
      dnsState = { checking: true };
      const r = await dns(v).catch(() => ({ ok: false, ip: "" }));
      dnsState = { checking: false, ok: r.ok, ip: r.ip };
      if (!r.ok) return;   // primero el aviso; sigue con "Agregarlo igual"
    }
    job.arm({ action: `${kind}-add`, app, value: v, ...(kind === "domain" && anyway ? { dns_ok: true } : {}) }, (ok) => ok && ondone());
    adding = false;
  }
</script>

<div class="box le">
  <div class="top">
    <h3 id={`${id}-title`}>{title}</h3>
    {#if !adding}
      <button type="button" class="btn small quiet" onclick={open} disabled={job.locked} aria-label={`${t().add}: ${title}`}>{t().add}</button>
    {/if}
  </div>

  {#if adding}
    <form class="form flat" onsubmit={submit} autocomplete="off" aria-labelledby={`${id}-title`}>
      <input {id} bind:this={input} bind:value class="mono" {placeholder} spellcheck="false" required
        oninput={() => { dnsState = null; anyway = false; error = null; }}
        aria-invalid={error ? "true" : undefined} aria-describedby={`${id}-help`} aria-label={title} />
      {#if error}
        <span id={`${id}-help`} class="help error">{error}</span>
      {:else if dnsState?.checking}
        <span id={`${id}-help`} class="help" aria-live="polite">{t().checkingDns}</span>
      {:else if dnsState && !dnsState.ok}
        <p class="warnbox" role="status" id={`${id}-help`}>{t().dnsMissing(norm(value), dnsState.ip ?? "")}</p>
        <label class="check"><input type="checkbox" bind:checked={anyway} /> {t().dnsAnyway}</label>
      {/if}
      <div class="actions">
        <button type="submit" class="btn small primary" disabled={job.locked || (dnsState !== null && !dnsState.ok && !anyway)}>{t().add}</button>
        <button type="button" class="btn small quiet" onclick={() => (adding = false)}>{t().cancel}</button>
      </div>
    </form>
  {/if}

  {#if fixed}
    <div class="row" title={t().mainDomainHint}><code>{fixed}</code><span class="tag">{t().mainDomain}</span></div>
  {/if}
  {#each items as it (it)}
    <div class="row">
      <code>{it}</code>
      <button type="button" class="btn small quiet danger" disabled={job.locked} aria-label={t().removeX(it)}
        onclick={() => job.arm({ action: `${kind}-rm`, app, value: it }, (ok) => ok && ondone())}>{t().remove}</button>
    </div>
  {:else}
    {#if !fixed && !adding}<p class="row empty">{t().emptyList}</p>{/if}
  {/each}
  {#if note && items.length}<p class="row note">{note}</p>{/if}
</div>

<style>
  .le { display: flex; flex-direction: column; }
  .top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4); border-bottom: 1px solid var(--line); background: var(--sunken); }
  h3 { margin: 0; font-size: 13.5px; font-weight: 600; }
  .row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); min-height: 44px; padding: 6px var(--space-2) 6px var(--space-4); border-bottom: 1px solid var(--line); margin: 0; }
  .row:last-child { border-bottom: 0; }
  .row code { font-size: 13px; overflow-wrap: anywhere; }
  .empty, .note { color: var(--muted); font-size: 13.5px; }
  .note { font-size: 12.5px; }
</style>
