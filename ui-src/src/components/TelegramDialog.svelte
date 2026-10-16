<!--
  Telegram, guiado (lo mismo que `andamio telegram`): 1) el token del bot (oculto; se comprueba
  con Telegram), 2) le escribes a tu bot y el panel encuentra tu chat solo, 3) activar: se
  cifra en tu repo, se aplica en el servidor y llega un mensaje de prueba. El token va de esta
  página a tu panel local y entra al comando por stdin: nunca en la línea de comandos.
-->
<script lang="ts">
  import { SECRET_TYPE, noSave } from "../lib/secret";
  import { tick } from "svelte";
  import { untrack } from "svelte";
  import * as api from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";
  import Modal from "./Modal.svelte";

  let { open = $bindable(false), ondone }: { open?: boolean; ondone: () => void } = $props();

  let step = $state<1 | 2 | 3>(1);
  let token = $state("");
  let bot = $state<{ bot: string; name: string } | null>(null);
  let chats = $state<api.TgChat[]>([]);
  let chat = $state("");
  let manual = $state(false);
  let busy = $state(false);
  let error = $state("");
  let tokenInput: HTMLInputElement | undefined = $state();

  $effect(() => {
    if (!open) return;
    untrack(() => {
      step = 1; token = ""; bot = null; chats = []; chat = ""; manual = false; error = "";
      void tick().then(() => tokenInput?.focus());
    });
  });
  // Al cerrar, el token no se queda en la página.
  $effect(() => { if (!open) untrack(() => (token = "")); });

  async function check(e: SubmitEvent) {
    e.preventDefault();
    busy = true; error = "";
    try {
      const r = await api.telegramCheck(token.trim());
      if (r.error) error = r.error;
      else { bot = { bot: r.bot!, name: r.name! }; step = 2; }
    } catch (err) { error = String((err as Error).message); } finally { busy = false; }
  }
  async function find() {
    busy = true; error = "";
    try {
      const r = await api.telegramChats(token.trim(), 15);
      chats = r.chats.filter((c) => c.type === "private").length ? r.chats.filter((c) => c.type === "private") : r.chats;
      if (r.error) { error = r.error; manual = true; }
      else if (!chats.length) error = t().tgNoMessage;
      if (chats.length === 1) chat = chats[0]!.id;
    } catch (err) { error = String((err as Error).message); } finally { busy = false; }
  }
  const chatOk = $derived(/^-?\d{1,20}$/.test(chat));
  const chosen = $derived(chats.find((c) => c.id === chat));

  function activate() {
    job.arm({ action: "telegram", token: token.trim(), chat }, () => ondone());
    void job.run();
    open = false;
  }
</script>

<Modal bind:open id="telegram" wide dirty={token.trim().length > 0}>
  {#snippet heading()}{t().tgTitle}{/snippet}
  <ol class="steps" aria-label={t().tgSteps}>
    {#each [t().tgStep1, t().tgStep2, t().tgStep3] as s, i (i)}
      <li class:on={step === i + 1} class:done={step > i + 1} aria-current={step === i + 1 ? "step" : undefined}><span>{i + 1}</span>{s}</li>
    {/each}
  </ol>

  {#if step === 1}
    <form class="m-body" onsubmit={check} autocomplete="off">
      <p class="m-note">{t().tgHow1} <strong>@BotFather</strong> {t().tgHow2} <code>/newbot</code>. {t().tgHow3}</p>
      <label for="tg-token">{t().tgToken}</label>
      <input id="tg-token" bind:this={tokenInput} bind:value={token} type={SECRET_TYPE} {...noSave} class="mono field secret-field" spellcheck="false"
        autocomplete="off" placeholder="123456789:AA…" aria-describedby="tg-token-note" />
      <p id="tg-token-note" class="m-note">{t().tgTokenNote}</p>
      {#if error}<p class="err" role="alert">{error}</p>{/if}
      <div class="foot">
        <button type="button" class="btn quiet" onclick={() => (open = false)}>{t().cancel}</button>
        <button type="submit" class="btn primary" disabled={busy || !token.trim()} aria-busy={busy}>{busy ? t().checking : t().tgCheck}</button>
      </div>
    </form>
  {:else if step === 2 && bot}
    <div class="m-body">
      <p class="ok">✓ {t().tgBotOk(bot.bot, bot.name)}</p>
      <p>{t().tgOpen} <a href={`https://t.me/${bot.bot}`} target="_blank" rel="noopener noreferrer">t.me/{bot.bot}</a> {t().tgOpen2}</p>
      {#if chats.length}
        <fieldset>
          <legend>{t().tgWhich}</legend>
          {#each chats as c (c.id)}
            <label class="opt" class:on={chat === c.id}>
              <input type="radio" name="tg-chat" value={c.id} bind:group={chat} />
              <span class="nm">{c.name || c.id}</span>{#if c.username}<span class="muted">@{c.username}</span>{/if}
            </label>
          {/each}
        </fieldset>
      {/if}
      {#if manual}
        <label for="tg-chat">{t().tgChatId}</label>
        <input id="tg-chat" bind:value={chat} class="mono field" inputmode="numeric" spellcheck="false" autocomplete="off" />
      {/if}
      {#if error}<p class="err" role="alert">{error}</p>{/if}
    </div>
    <div class="m-foot">
      {#if !manual}<button type="button" class="btn quiet" onclick={() => (manual = true)}>{t().tgManual}</button>{/if}
      <button type="button" class="btn" onclick={find} disabled={busy} aria-busy={busy}>{busy ? t().tgWaiting : t().tgFind}</button>
      <button type="button" class="btn primary" onclick={() => (step = 3)} disabled={!chatOk}>{t().nextStep}</button>
    </div>
  {:else if step === 3 && bot}
    <div class="m-body">
      <dl class="sum">
        <dt>{t().tgBot}</dt><dd>@{bot.bot}</dd>
        <dt>{t().tgChat}</dt><dd>{chosen ? `${chosen.name}${chosen.username ? ` (@${chosen.username})` : ""}` : chat}</dd>
      </dl>
      <ul class="m-list kept">
        <li>{t().tgWill1}</li><li>{t().tgWill2}</li><li>{t().tgWill3}</li>
      </ul>
    </div>
    <div class="m-foot">
      <button type="button" class="btn quiet" onclick={() => (step = 2)}>{t().backStep}</button>
      <button type="button" class="btn primary" onclick={activate} disabled={job.locked}>{t().tgActivate}</button>
    </div>
  {/if}
</Modal>

<style>
  .steps { list-style: none; display: flex; gap: var(--space-4); margin: 0; padding: var(--space-3) var(--space-5) 0; font-size: 13px; color: var(--muted); }
  .steps li { display: inline-flex; align-items: center; gap: 6px; }
  .steps span { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; border: 1px solid var(--line); font-size: 12px; }
  .steps li.on { color: var(--ink); font-weight: 600; }
  .steps li.on span { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
  .steps li.done span { border-color: var(--ok); color: var(--ok-text); }
  label[for] { font-size: 14px; font-weight: 500; }
  .field {
    font: 14px var(--mono); color: var(--ink); background: var(--canvas); border: 1px solid var(--line);
    border-radius: 8px; padding: 9px 12px; width: 100%;
  }
  .field:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 22%, transparent); outline-offset: 0; border-color: var(--accent); }
  .err { margin: 0; color: var(--bad-text); font-size: 13.5px; }
  .ok { margin: 0; color: var(--ok-text); font-weight: 500; }
  .foot { display: flex; justify-content: flex-end; gap: var(--space-2); padding-top: var(--space-2); }
  fieldset { border: 0; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
  legend { font-size: 13px; color: var(--muted); margin-bottom: var(--space-2); padding: 0; }
  .opt { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); border: 1px solid var(--line); border-radius: 8px; cursor: pointer; }
  .opt.on { border-color: var(--accent); background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .opt input { accent-color: var(--accent); margin: 0; }
  .nm { font-weight: 600; }
  .muted { color: var(--muted); font-size: 13px; }
  .sum { display: grid; grid-template-columns: 90px 1fr; gap: 6px var(--space-4); margin: 0; }
  .sum dt { color: var(--muted); }
  .sum dd { margin: 0; font-weight: 500; }
</style>
