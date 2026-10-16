<!--
  Ajustes: alertas (activas o no, y una de prueba), la zona horaria de las tareas, buscar
  actualizaciones de andamio, tus servidores (copias) y un resumen de la configuración. Cada
  cambio corre su comando de la CLI en la terminal; activar alertas o aplicar una actualización
  siguen en tu terminal, a propósito (necesitan tu celular o resolver conflictos).
-->
<script lang="ts">
  import PageHead from "./PageHead.svelte";
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import Skeleton from "./Skeleton.svelte";
  import { job } from "../lib/job.svelte";
  import TelegramDialog from "./TelegramDialog.svelte";
  import NtfyDialog from "./NtfyDialog.svelte";
  import { theme, type Theme } from "../lib/theme.svelte";

  let data = $state<api.Settings | null>(null);
  let copies = $state<api.Copy[]>([]);
  let error = $state("");
  let tz = $state("");
  let switching = $state("");
  let switchErr = $state("");
  let tgOpen = $state(false);
  let ntfyOpen = $state(false);
  let copied = $state(false);
  const topic = $derived(data?.ntfy_url ? data.ntfy_url.replace(/\/+$/, "").split("/").pop() ?? "" : "");
  const ownServer = $derived(Boolean(data?.ntfy_url && !data.ntfy_url.startsWith("https://ntfy.sh/")));
  async function copyTopic() {
    try { await navigator.clipboard.writeText(data?.ntfy_url ?? ""); copied = true; setTimeout(() => (copied = false), 1500); } catch { /* sin portapapeles */ }
  }

  // La contraseña de sudo: cuánto se recuerda en esta máquina, y olvidarla ya.
  let sudoBusy = $state(false);
  const fmtMin = (m: number) => (m >= 60 ? `${m / 60} h` : `${m} min`);
  async function setSudo(m: number) {
    if (!data) return;
    sudoBusy = true;
    try { await api.sudoMinutes(m); data.sudo_minutes = m; } catch { /* se ve al recargar */ } finally { sudoBusy = false; }
  }
  async function forgetSudo() {
    if (!data) return;
    sudoBusy = true;
    try { await api.sudoForget(); data.sudo_remembered = false; } catch { /* nada */ } finally { sudoBusy = false; }
  }

  async function load() {
    try {
      const [s, c] = await Promise.all([api.settings(), api.copies().catch(() => ({ copies: [] }))]);
      data = s;
      copies = c.copies;
      tz = s.timezone || s.local_timezone;
      error = s.error;
    } catch (e) {
      error = String((e as Error).message);
    }
  }
  onMount(() => void load());

  const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const tzValid = $derived(Boolean(data?.timezones.includes(tz)));
  const tzChanged = $derived(tzValid && tz !== data?.timezone);

  const test = () => job.arm({ action: "alert-test" });
  const setTz = () => job.arm({ action: "timezone", timezone: tz }, () => void load());
  const check = () => job.arm({ action: "update-check" });

  async function open(c: api.Copy) {
    switchErr = "";
    switching = c.path;
    // La pestaña se abre ya (con el clic); el link llega después: así el navegador no la bloquea.
    const w = window.open("", "_blank");
    try {
      const { url } = await api.switchTo(c.path);
      if (w) { w.opener = null; w.location.href = url; } else location.href = url;
    } catch (e) {
      w?.close();
      switchErr = String((e as Error).message);
    } finally {
      switching = "";
    }
  }
</script>

<PageHead title={t().settings} desc={t().settingsDesc} />

{#if !data}
  {#if error}<p class="muted pad">{error}</p>{:else}<div class="pad"><Skeleton rows={4} /></div>{/if}
{:else}
  <section aria-labelledby="s-look">
    <div class="shead"><div><h2 id="s-look">{t().appearance}</h2><p class="desc">{t().appearanceDesc}</p></div></div>
    <div class="box rows">
      <div class="row">
        <span class="grow" id="theme-label">{t().themeLabel}</span>
        <div class="seg" role="radiogroup" aria-labelledby="theme-label">
          {#each [["system", t().themeSystem], ["light", t().themeLight], ["dark", t().themeDark]] as [v, label] (v)}
            <button type="button" role="radio" aria-checked={theme.value === v} class:on={theme.value === v}
              onclick={() => theme.set(v as Theme)}>{label}</button>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section aria-labelledby="s-sudo">
    <div class="shead"><div><h2 id="s-sudo">{t().sudoTitle}</h2><p class="desc">{t().sudoDesc}</p></div></div>
    <div class="box rows">
      <div class="row">
        <span class="grow" id="sudo-label">{t().sudoRemember}</span>
        <div class="seg" role="radiogroup" aria-labelledby="sudo-label">
          {#each data.sudo_choices as m (m)}
            <button type="button" role="radio" aria-checked={data.sudo_minutes === m} class:on={data.sudo_minutes === m}
              disabled={data.sudo_env || sudoBusy} onclick={() => setSudo(m)}>{fmtMin(m)}</button>
          {/each}
        </div>
      </div>
      {#if data.sudo_env}<p class="row note">{t().sudoEnv(fmtMin(data.sudo_minutes))}</p>{/if}
      <div class="row">
        <div class="grow">
          <strong>{data.sudo_remembered ? t().sudoNow : t().sudoNone}</strong>
          <p class="note">{t().sudoRisk}</p>
        </div>
        <button type="button" class="btn small" disabled={!data.sudo_remembered || sudoBusy || job.locked} onclick={forgetSudo}>{t().sudoForget}</button>
      </div>
    </div>
  </section>

  <section aria-labelledby="s-alerts">
    <div class="shead"><div><h2 id="s-alerts">{t().alerts}</h2><p class="desc">{t().alertsDesc}</p></div></div>
    <div class="box rows">
      <div class="row">
        <div class="grow">
          <div class="chans">
            {#each [["Telegram", data.alerts?.telegram], ["ntfy", data.alerts?.ntfy]] as [name, on] (name)}
              <span class="chan"><span class={`dot ${on ? "ok" : ""}`}></span>{name} <span class="muted">· {data.alerts === null ? "?" : on ? t().on : t().off}</span></span>
            {/each}
          </div>
        </div>
        <button type="button" class="btn small" onclick={test} disabled={job.locked || !(data.alerts?.ntfy || data.alerts?.telegram)}>{t().sendTest}</button>
      </div>
      <div class="row">
        <div class="grow">
          <strong>Telegram</strong>
          <p class="note">{data.telegram_on ? t().tgOnDesc : t().tgOffDesc}</p>
        </div>
        <div class="acts">
          {#if data.telegram_on}
            <button type="button" class="btn small quiet" disabled={job.locked} onclick={() => job.arm({ action: "telegram-off" }, () => void load())}>{t().tgOff}</button>
          {/if}
          <button type="button" class="btn small" disabled={job.locked} onclick={() => (tgOpen = true)}>{data.telegram_on ? t().tgChange : t().tgSetup}</button>
        </div>
      </div>
      <div class="row">
        <div class="grow">
          <strong>ntfy</strong>
          {#if data.ntfy_url}
            <p class="note">{t().ntfyOnDesc}</p>
            <div class="topic">
              <code>{data.ntfy_url}</code>
              <button type="button" class="btn small quiet" onclick={copyTopic}>{copied ? t().copied : t().copy}</button>
            </div>
            <p class="note">{ownServer ? t().ntfySubscribeOwn(topic) : t().ntfySubscribe(topic)}
              <a href={data.ntfy_url} target="_blank" rel="noopener noreferrer">{t().ntfyOpenWeb}</a></p>
          {:else}
            <p class="note">{t().ntfyOffDesc}</p>
          {/if}
        </div>
        <div class="acts">
          {#if data.ntfy_url}
            <button type="button" class="btn small quiet" disabled={job.locked} onclick={() => job.arm({ action: "ntfy", ntfy: "quitar" }, () => void load())}>{t().tgOff}</button>
          {/if}
          <button type="button" class="btn small" disabled={job.locked} onclick={() => (ntfyOpen = true)}>{data.ntfy_url ? t().ntfyChangeShort : t().ntfySetup}</button>
        </div>
      </div>
    </div>
  </section>

  <section aria-labelledby="s-tz">
    <div class="shead"><div><h2 id="s-tz">{t().tzTitle}</h2><p class="desc">{t().tzDesc(data.tasks)}</p></div></div>
    <div class="box rows">
      <div class="row">
        <label class="grow tzf">
          <span class="lbl">{t().tzNow(data.timezone || t().tzNone)}</span>
          <input list="tz-list" bind:value={tz} spellcheck="false" autocomplete="off" aria-invalid={tz && !tzValid ? "true" : undefined} />
          <datalist id="tz-list">{#each data.timezones as z (z)}<option value={z}></option>{/each}</datalist>
          {#if tz && !tzValid}<span class="err">{t().tzBad}</span>{/if}
        </label>
        <div class="acts">
          {#if browserTz && browserTz !== tz && data.timezones.includes(browserTz)}
            <button type="button" class="btn small quiet" onclick={() => (tz = browserTz)}>{t().tzUseMine(browserTz)}</button>
          {/if}
          <button type="button" class="btn small primary" onclick={setTz} disabled={job.locked || !tzChanged}>{t().tzApply}</button>
        </div>
      </div>
    </div>
  </section>

  <section aria-labelledby="s-up">
    <div class="shead"><div><h2 id="s-up">{t().updates}</h2><p class="desc">{t().updatesDesc}</p></div></div>
    <div class="box rows">
      <div class="row">
        {#if data.updatable}
          <p class="grow note">{t().updatesHow} <code>andamio update</code></p>
          <button type="button" class="btn small" onclick={check} disabled={job.locked}>{t().checkUpdates}</button>
        {:else}
          <p class="grow note">{t().sourceCopy}</p>
        {/if}
      </div>
    </div>
  </section>

  <section aria-labelledby="s-servers">
    <div class="shead"><div><h2 id="s-servers">{t().servers}</h2><p class="desc">{t().serversDesc}</p></div></div>
    <ul class="box rows">
      {#each copies as c (c.path)}
        <li class="row">
          <div class="grow">
            <strong>{c.domain}</strong>
            <div class="muted path"><code>{c.path}</code></div>
          </div>
          {#if c.current}
            <span class="tag">{t().thisPanel}</span>
          {:else}
            <button type="button" class="btn small" onclick={() => open(c)} disabled={switching !== ""} aria-busy={switching === c.path}>
              {switching === c.path ? t().opening : t().openPanel}
            </button>
          {/if}
        </li>
      {/each}
    </ul>
    {#if switchErr}<p class="err">{switchErr}</p>{/if}
    <p class="note">{t().serversHow} <code>andamio init</code> · <code>andamio use</code></p>
  </section>

  <section aria-labelledby="s-sum">
    <div class="shead"><div><h2 id="s-sum">{t().summary}</h2></div></div>
    <dl class="box sum">
      <dt>{t().domain}</dt><dd>{data.domain}</dd>
      <dt>{t().server}</dt><dd><code>{data.server}</code></dd>
      <dt>{t().copyFolder}</dt><dd><code>{data.copy}</code></dd>
      <dt>{t().monitoringLevel}</dt><dd>{data.monitoring}</dd>
      <dt>{t().backups}</dt><dd>{data.backups ? t().on : t().off}</dd>
      <dt>{t().forgeName}</dt><dd>{data.forge}</dd>
    </dl>
  </section>
{/if}

<TelegramDialog bind:open={tgOpen} ondone={() => void load()} />
<NtfyDialog bind:open={ntfyOpen} current={data?.ntfy_url ?? ""} ondone={() => void load()} />

<style>
  .topic { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); margin-top: 6px; }
  .topic code { font-size: 12.5px; padding: 4px 8px; border-radius: 6px; background: var(--sunken); overflow-wrap: anywhere; }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); }
  .seg button {
    font: 500 13px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px;
    padding: 7px 12px; cursor: pointer; transition: background-color 150ms var(--ease), color 150ms var(--ease);
  }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }
  section { margin-top: var(--space-7); }
  .muted { color: var(--muted); }
  .pad { padding: var(--space-6) 0; }
  .rows { list-style: none; margin: 0; padding: 0; }
  .row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3) var(--space-5); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); }
  .row:last-child { border-bottom: 0; }
  .grow { flex: 1; min-width: 240px; }
  .chans { display: flex; flex-wrap: wrap; gap: var(--space-5); }
  .chan { display: inline-flex; align-items: center; gap: 8px; font-weight: 500; }
  .note { margin: 6px 0 0; font-size: 13.5px; color: var(--muted); }
  .grow.note { margin: 0; }
  .tzf { display: grid; gap: 6px; }
  .lbl { font-size: 13.5px; color: var(--muted); }
  .tzf input {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line);
    border-radius: 8px; padding: 8px 12px; max-width: 320px;
  }
  .tzf input:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 22%, transparent); border-color: var(--accent); }
  .err { color: var(--bad-text); font-size: 13px; }
  .acts { display: flex; flex-wrap: wrap; gap: var(--space-2); }
  .path { font-size: 12.5px; margin-top: 2px; overflow-wrap: anywhere; }
  .tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: color-mix(in oklch, var(--accent) 12%, var(--surface)); color: var(--accent); }
  .sum { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: var(--space-2) var(--space-4); margin: 0; padding: var(--space-4); }
  .sum dt { color: var(--muted); font-size: 14px; }
  .sum dd { margin: 0; overflow-wrap: anywhere; }
  @media (max-width: 600px) { .sum { grid-template-columns: 1fr; } .sum dd { margin-bottom: var(--space-2); } }
</style>
