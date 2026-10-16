<!--
  Nueva tarea programada (o editar una: con `edit`, viene llena y solo cambia horario y comando). Mientras escribes el horario, debajo aparece cuándo correrá la
  próxima vez (con el mismo conversor que usa la CLI) o qué está mal.
-->
<script lang="ts">
  import { cronPreview } from "../lib/api";
  import { t } from "../lib/i18n.svelte";
  import { job } from "../lib/job.svelte";

  import type { Cron } from "../lib/api";

  let { app, taken, timezoneSet, onclose, ondone, edit = null, preset = "" }: {
    app: string; taken: string[]; timezoneSet: boolean; onclose: () => void; ondone: () => void; edit?: Cron | null;
    preset?: string;   // un horario de ejemplo para empezar (tarea nueva)
  } = $props();

  // svelte-ignore state_referenced_locally
  let schedule = $state(edit?.schedule ?? (preset || "0 3 * * *"));
  // svelte-ignore state_referenced_locally
  let command = $state(edit?.command ?? "");
  let name = $state("");
  let tz = $state(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  let preview = $state<{ next?: string; error?: string; timezone?: string } | null>(null);
  let commandError = $state<string | null>(null);
  let nameError = $state<string | null>(null);
  let first: HTMLInputElement | undefined = $state();

  $effect(() => { first?.focus(); });

  // La próxima vez, mientras escribes (con una pausa corta para no pedirla en cada tecla).
  $effect(() => {
    const s = schedule, zone = timezoneSet ? "" : tz;
    const timer = setTimeout(async () => {
      try { preview = s.trim() ? await cronPreview(s, zone) : null; } catch { preview = null; }
    }, 250);
    return () => clearTimeout(timer);
  });

  const checkCommand = () => (commandError = !command.trim() || /[\r\n]/.test(command) ? t().badCommand : null);
  const checkName = () =>
    (nameError = name && (!/^[a-z][a-z0-9-]{0,29}$/.test(name) || taken.includes(name)) ? t().badTaskName : null);

  function submit(e: SubmitEvent) {
    e.preventDefault();
    if (preview?.error || checkCommand() || checkName()) return;
    if (edit) {
      const s = schedule.trim(), c = command.trim();
      if (s === edit.schedule && c === edit.command) return onclose();
      job.arm({ action: "cron-edit", app, task: edit.name, ...(s !== edit.schedule ? { schedule: s } : {}),
        ...(c !== edit.command ? { command: c } : {}) }, (ok) => ok && ondone());
      onclose();
      return;
    }
    job.arm({ action: "cron-add", app, schedule: schedule.trim(), command: command.trim(), task: name,
      ...(timezoneSet ? {} : { timezone: tz }) }, (ok) => ok && ondone());
    onclose();
  }
</script>

<form class="form flat" onsubmit={submit} autocomplete="off">
  <div class="fields">
    <label>
      {t().taskSchedule}
      <input bind:this={first} bind:value={schedule} class="mono" spellcheck="false" required
        aria-invalid={preview?.error ? "true" : undefined} aria-describedby="tf-sched" />
      <span id="tf-sched" class="help" class:error={preview?.error} class:ok={preview?.next} aria-live="polite">
        {preview?.error ?? (preview?.next ? t().nextRun(preview.next) : t().scheduleHint)}
      </span>
    </label>
    <label>
      {t().taskCommand}
      <input bind:value={command} class="mono" placeholder="python limpiar.py" spellcheck="false" required onblur={checkCommand}
        aria-invalid={commandError ? "true" : undefined} aria-describedby="tf-cmd" />
      <span id="tf-cmd" class="help" class:error={commandError}>{commandError ?? t().taskCommandHint}</span>
    </label>
    {#if !edit}<label>
      {t().taskName}
      <input bind:value={name} class="mono" spellcheck="false" onblur={checkName}
        aria-invalid={nameError ? "true" : undefined} aria-describedby="tf-name" />
      <span id="tf-name" class="help" class:error={nameError}>{nameError ?? t().taskNameHint}</span>
    </label>{/if}
    {#if !timezoneSet}
      <label>
        {t().timezone}
        <input bind:value={tz} spellcheck="false" aria-describedby="tf-tz" />
        <span id="tf-tz" class="help">{t().timezoneHint}</span>
      </label>
    {/if}
  </div>
  <div class="actions">
    <button type="submit" class="btn small primary" disabled={Boolean(preview?.error) || job.locked}>{edit ? t().save : t().add}</button>
    <button type="button" class="btn small quiet" onclick={onclose}>{t().cancel}</button>
  </div>
</form>
