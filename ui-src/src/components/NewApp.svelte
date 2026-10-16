<!--
  Nueva app: cuatro pasos en la misma página (sin ventanas encima). 1) el repo, de tus repos de
  GitHub o desde la plantilla; 2) la revisión: lo que diría `app create` (lenguaje, Dockerfile,
  comando de arranque, revisión previa), sin cambiar nada; 3) la configuración, con lo detectado
  ya puesto; 4) el comando exacto y qué va a pasar. Crear corre ese mismo comando en la terminal.
-->
<script lang="ts">
  import PageHead from "./PageHead.svelte";
  import { SECRET_TYPE, noSave } from "../lib/secret";
  import { onMount } from "svelte";
  import * as api from "../lib/api";
  import { ago, since } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { commandFor, job } from "../lib/job.svelte";
  import { guard } from "../lib/guard.svelte";
  import { parseDotenv } from "../lib/dotenv";

  let { meta }: { meta: api.Meta | null } = $props();

  // Varias apps en un repo (front y back): la carpeta de esta, si se construye desde la raíz
  // (archivos compartidos) y, opcional, una ruta bajo la dirección de otra (/api).
  let dir = $state("");
  let fromRoot = $state(false);
  let path = $state("");
  let custom = $state(false);   // "Personalizar": el formulario completo (si no, el camino rápido)
  // Dominio propio (opcional): se revisa su DNS mientras escribes; si aún no apunta, "agregarlo igual".
  let ownDomain = $state("");
  let dnsInfo = $state<{ checking: boolean; ok?: boolean; ip?: string } | null>(null);
  let dnsAnyway = $state(false);
  const ownOk = $derived(!ownDomain || /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/.test(ownDomain.trim()));
  let dnsTimer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    const d = ownDomain.trim();
    clearTimeout(dnsTimer);
    dnsInfo = null;
    dnsAnyway = false;
    if (!d || !ownOk) return;
    dnsTimer = setTimeout(async () => {
      dnsInfo = { checking: true };
      const r = await api.dns(d).catch(() => ({ ok: false, ip: "" }));
      if (ownDomain.trim() === d) dnsInfo = { checking: false, ok: r.ok, ip: r.ip };
    }, 600);
  });
  // Lo que la revisión de la raíz encontró: se queda mientras se revisa otra carpeta.
  let folders = $state<api.Folder[]>([]);
  // Muchas carpetas: un buscador; las librerías (no se despliegan) van escondidas; y otra a mano.
  let folderQuery = $state("");
  let showLibs = $state(false);
  let otherDir = $state("");
  const matches = (f: api.Folder) => !folderQuery.trim() || `${f.dir} ${f.framework} ${f.label}`.toLowerCase().includes(folderQuery.trim().toLowerCase());
  const appFolders = $derived(folders.filter((f) => !f.lib && matches(f)));
  const libFolders = $derived(folders.filter((f) => f.lib && matches(f)));
  const otherOk = $derived(/^\/?[A-Za-z0-9._-]+(\/[A-Za-z0-9._-]+)*\/?$/.test(otherDir.trim()) && !otherDir.includes(".."));
  let rootApp = $state(false);   // la raíz también es una app (tiene Dockerfile o un proyecto)

  // Paso 1: el repo.
  let mode = $state<"repo" | "template">("repo");
  let repos = $state<api.RepoItem[] | null>(null);
  let query = $state("");
  let repo = $state("");   // elegido
  const typed = $derived(/^[A-Za-z0-9-]+\/[A-Za-z0-9._-]+$/.test(query.trim()) ? query.trim() : "");
  const shown = $derived((repos ?? []).filter((r) => r.repo.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8));

  // Paso 2: la revisión.
  let preview = $state<api.Preview | null>(null);
  let reviewing = $state(false);
  let start = $state("");
  let precheckOk = $state(false);

  // Paso 3: la configuración.
  let name = $state("");
  let host = $state("");
  let root = $state(false);
  let access = $state<"vpn" | "public">("vpn");
  let port = $state("3000");
  let health = $state("");
  let mem = $state("256m");
  let db = $state(false);
  let mysql = $state(false);   // MariaDB (compatible con MySQL)
  let redis = $state(false);
  let volume = $state("");
  // Paso 4: las variables de entorno (las que el código usa ya vienen; los valores, ocultos).
  // required: el código falla sin ella; example: el valor del .env.example (se usa solo si lo pides).
  type Var = { key: string; value: string; where: string; required?: boolean; example?: string };
  let vars = $state<Var[]>([]);
  let taken = $state<{ names: string[]; hosts: string[] }>({ names: [], hosts: [] });

  // Una app a medio armar: antes de irte, el panel pregunta (no después de crearla).
  let created = $state(false);   // la app ya existe (aunque el último paso, p. ej. subir el pipeline, fallara)
  $effect(() => guard(() => !created && (repo !== "" || (mode === "template" && name !== "")) && job.kind !== "create"));

  onMount(async () => {
    try { repos = (await api.repos()).repos; } catch { repos = []; }
    try {
      const a = await api.apps();
      taken = { names: a.apps.map((x) => x.name), hosts: a.apps.map((x) => (x.host ?? "") + (x.path ?? "")) };
    } catch { /* la revisión también los trae */ }
  });

  async function pick(r: string, sub = "") {
    if (r !== repo) { folders = []; rootApp = false; fromRoot = false; folderQuery = ""; showLibs = false; otherDir = ""; }
    repo = r;
    dir = sub;
    preview = null;
    reviewing = true;
    precheckOk = false;
    try {
      preview = await api.createPreview(r, sub);
      if (preview.folders?.length) folders = preview.folders;
      if (!sub) rootApp = Boolean(preview.kind || preview.has_dockerfile);
      taken = { names: preview.taken, hosts: preview.hosts };
      name = preview.name || name;
      host = "";
      start = preview.start ?? "";
      port = preview.port ?? port;
      // Lo que el código pide se enciende solo: MariaDB si declara MySQL (un driver, DB_CONNECTION=mysql,
      // Prisma con mysql), si no PostgreSQL si usa DATABASE_URL; Redis si usa REDIS_*.
      const keys = (preview.env ?? []).map((e) => e.key);
      mysql = Boolean(preview.mysql);
      db = !mysql && keys.includes("DATABASE_URL");
      // Las que pone andamio para MariaDB no se piden (las de Laravel incluidas).
      vars = (preview.env ?? []).filter((e) => !(mysql && MYSQL_KEYS.includes(e.key)))
        .map((e) => ({ key: e.key, value: "", where: e.where, required: e.required, example: e.example }));
      redis = keys.some((k) => k === "REDIS_URL" || k === "REDIS_HOST");
      custom = false;
      // Otra app de este repo ya tiene dirección: el back va bajo ella, en /api (si es la que eligió).
      const sib = preview.siblings?.find((x) => !x.path && x.dir !== sub);
      if (sub && sib && /(^|\/)(api|back|backend|server)$/.test(sub)) { root = sib.host === "@"; host = root ? "" : sib.host; path = "/api"; }
      else path = "";
    } catch (e) {
      preview = { repo: r, private: false, instance: "", blocked: false, name: "", taken: [], hosts: [], dir: sub, error: String((e as Error).message) };
    } finally {
      reviewing = false;
    }
  }
  function useTemplate() {
    mode = "template";
    repo = "";
    preview = null;
  }

  // Validación (la misma que la CLI; el panel y la CLI la repiten antes de correr nada).
  const effHost = $derived(root ? "@" : host || name);
  const errors = $derived({
    name: !/^[a-z][a-z0-9-]{1,28}[a-z0-9]$/.test(name) ? t().appNameHint : taken.names.includes(name) ? t().nameTaken : "",
    host: root ? (taken.hosts.includes("@" + path) ? t().hostTaken : "") :
      !/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(effHost) ? t().badHost : taken.hosts.includes(effHost + path) ? t().hostTaken : "",
    path: !path || /^\/[a-z0-9._-]+(\/[a-z0-9._-]+)*$/.test(path) ? "" : t().badPath,
    domain: !ownOk ? t().badDomain : ownDomain.trim() && dnsInfo !== null && !dnsInfo.checking && !dnsInfo.ok && !dnsAnyway ? t().dnsPending : "",
    port: /^[0-9]{2,5}$/.test(port) && Number(port) <= 65535 ? "" : t().badPort,
    mem: /^[0-9]+[mg]$/.test(mem) ? "" : t().badMem,
    health: !health || /^\/[A-Za-z0-9._/-]*$/.test(health) ? "" : t().badHealth,
    // Una ruta de la web (la de salud) en el campo de carpeta: casi seguro es un error de campo.
    volume: volume && volume.replace(/\/$/, "") === health.replace(/\/$/, "") ? t().volumeIsHealth :
      !volume || (/^(\/[A-Za-z0-9._-]+)+$/.test(volume) && !volume.includes("..") &&
      !/^\/(bin|boot|dev|etc|lib|lib64|proc|root|run|sbin|sys|usr|var\/run)(\/|$)/.test(volume)) ? "" : t().badFolder,
    start: /[\r\n]/.test(start) ? t().badCommand : "",
  });
  const serious = $derived(Boolean(preview?.findings?.some((f) => f.serious)));
  const reviewOk = $derived(mode === "template" || Boolean(preview && !preview.error && !preview.blocked && (preview.kind || preview.has_dockerfile)));
  // Un repo con varias apps (carpetas con Dockerfile o proyecto) y nada en la raíz: hay que elegir una.
  const mustPick = $derived(Boolean(preview && !preview.error && !dir && !rootApp && folders.length));
  // Las pone andamio: no se pueden escribir. Con MariaDB, también las DB_* de Laravel.
  const MYSQL_KEYS = ["MYSQL_URL", "DB_CONNECTION", "DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USERNAME", "DB_PASSWORD"];
  const RESERVED = $derived(["DOMAIN", "DATABASE_URL", "MYSQL_URL", "REDIS_URL", "TAG", ...(mysql ? MYSQL_KEYS : [])]);
  const varErrors = $derived(vars.map((v, i) =>
    !/^[A-Z][A-Z0-9_]*$/.test(v.key) || RESERVED.includes(v.key) || vars.findIndex((w) => w.key === v.key) !== i ? t().badVarName :
    /[\r\n]/.test(v.value) ? t().badSecretValue : ""));
  const filled = $derived(vars.filter((v) => v.key && v.value));
  // Modo "Pegar .env" (como el editor en bruto de Railway): se pega todo y pasa a las filas de abajo.
  let rawOpen = $state(false);
  let raw = $state("");
  let rawShow = $state(false);
  const rawLines = $derived(parseDotenv(raw));
  const rawBad = $derived(rawLines.filter((l) => !l.hasEq || !/^[A-Z][A-Z0-9_]*$/.test(l.key)));
  function applyRaw() {
    for (const l of rawLines) {
      if (!l.hasEq || !/^[A-Z][A-Z0-9_]*$/.test(l.key) || RESERVED.includes(l.key)) continue;
      const row = vars.find((v) => v.key === l.key);
      if (row) row.value = l.value;
      else vars.push({ key: l.key, value: l.value, where: "" });
    }
    vars = vars.filter((v) => v.key || v.value);   // las filas vacías sobran
    raw = "";
    rawOpen = false;
  }
  const missing = $derived(vars.filter((v) => v.key && !v.value).length);
  const reqMissing = $derived(vars.filter((v) => v.required && !v.value).map((v) => v.key));
  const examples = $derived(vars.filter((v) => v.example && !v.value));
  function useExamples() { for (const v of examples) v.value = v.example!; }
  const configOk = $derived(Object.values(errors).every((e) => !e) && (!serious || precheckOk) && varErrors.every((e) => !e));
  const body = $derived<api.CreateBody>({
    name, repo: mode === "template" ? "" : repo, host: effHost, port, mem, health, access, db, mysql, redis,
    volume: volume.replace(/\/$/, ""), start: preview?.has_dockerfile ? "" : start, precheck_ok: precheckOk,
    dir: mode === "template" ? "" : dir, context: dir && fromRoot ? "." : "", path,
    branch: mode === "template" ? "" : preview?.branch ?? "",
    domain: ownDomain.trim(), dns_ok: dnsAnyway,
    secrets: filled.map((v) => ({ key: v.key, value: v.value })),
  });
  const command = $derived(commandFor({ action: "create", create: body }));
  const domain = $derived(meta?.domain ?? "");

  function create() {
    if (!configOk || !reviewOk) return;
    const n = name;
    job.arm({ action: "create", create: body }, async (ok) => {
      // Un paso del final puede fallar (la rama protegida rechaza el pipeline) con la app ya
      // registrada: entonces también se va a ella, donde se ve qué falta.
      let exists = ok;
      if (!ok) {
        try { exists = (await api.apps()).apps.some((x) => x.name === n); } catch { exists = false; }
      }
      if (exists) { created = true; location.hash = `#/app/${n}`; }
    });
  }
  // La revisión dice que el código guarda archivos: un clic agrega la carpeta.
  const suggestVolume = () => (volume = volume || "/data");
  // El Dockerfile propuesto, con el comando de arranque que elegiste.
  const dockerfileShown = $derived(preview?.dockerfile && preview.start && start
    ? preview.dockerfile.replace(`exec ${preview.start.replaceAll('"', '\\"')}`, `exec ${start.replaceAll('"', '\\"')}`) : preview?.dockerfile ?? "");
</script>

<PageHead title={t().newApp} desc={t().newAppDesc} />

<!-- 1 · El repo -->
<section class="step" aria-labelledby="s1">
  <div class="shead">
    <div><span class="num">1</span><h2 id="s1">{t().stepRepo}</h2></div>
    {#if (repo || mode === "template") && !reviewing}
      <button type="button" class="btn small quiet" onclick={() => { repo = ""; preview = null; mode = "repo"; dir = ""; path = ""; }}>{t().changeStep}</button>
    {/if}
  </div>
  {#if repo}
    <p class="chosen"><code>{repo}</code></p>
  {:else if mode === "template"}
    <p class="chosen">{t().fromTemplate(meta?.template ?? "")}</p>
    <p class="desc">{t().templateNote(meta?.owner ?? "", meta?.template ?? "")}</p>
  {:else}
    <div class="box">
      <div class="search">
        <!-- svelte-ignore a11y_autofocus -->
        <input bind:value={query} placeholder={t().searchRepos} aria-label={t().searchRepos} spellcheck="false" autofocus />
        {#if typed && !shown.some((r) => r.repo === typed)}
          <button type="button" class="btn small" onclick={() => pick(typed)}>{t().useRepo} {typed}</button>
        {/if}
      </div>
      {#if repos === null}
        <p class="row muted">{t().loadingRepos}</p>
      {:else if shown.length}
        <ul>
          {#each shown as r (r.repo)}
            <li>
              <button type="button" class="pick" onclick={() => pick(r.repo)}>
                <span class="rname">{r.repo}</span>
                <span class="tag" class:public={!r.private}>{r.private ? t().privateRepo : t().publicRepo}</span>
                {#if r.description}<span class="rdesc">{r.description}</span>{/if}
                <span class="rwhen">{t().updatedAgo(ago(since(r.updated)))}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="row muted">{t().noRepos} {t().orType}</p>
      {/if}
    </div>
    {#if meta?.template}
      <button type="button" class="btn small quiet tpl" onclick={useTemplate}>{t().fromTemplate(meta.template)}</button>
    {/if}
  {/if}
</section>

<!-- 2 · Revisión -->
{#if repo}
  <section class="step" aria-labelledby="s2" aria-busy={reviewing}>
    <div class="shead"><div><span class="num">2</span><h2 id="s2">{t().stepReview}</h2></div></div>
    {#if folders.length}{@render folderPick()}{/if}
    {#if reviewing}
      <p class="box row muted" aria-live="polite"><span class="pulse"></span>{t().reviewing(repo)}</p>
    {:else if mustPick}
      <p class="help">{t().pickFolderFirst}</p>
    {:else if preview?.error}
      <p class="box row bad" role="alert">{preview.error}</p>
    {:else if preview?.blocked}
      <p class="box row bad" role="alert">{t().blocked(repo, preview.instance)}</p>
    {:else if preview}
      <div class="box">
        {#if preview.branch}
          <div class="row kv"><span class="k">{t().srcBranch}</span><span><code>{preview.branch}</code> <span class="muted">{t().branchHint}</span></span></div>
        {/if}
        <div class="row kv"><span class="k">{t().language}</span><span>{preview.label || t().unknownLang}</span></div>
        {#if preview.kind || preview.has_dockerfile}
          <div class="row kv">
            <span class="k">{t().dockerfile}</span>
            <div class="grow">
              <span>{preview.has_dockerfile ? t().hasDockerfile : t().proposedDockerfile}</span>
              {#if dockerfileShown}
                <details><summary>{t().showDockerfile}</summary><pre class="code">{dockerfileShown}</pre></details>
              {/if}
            </div>
          </div>
        {/if}
        {#if !preview.has_dockerfile && preview.start}
          <label class="row kv">
            <span class="k">{t().startCmd}</span>
            <span class="grow field">
              <input bind:value={start} class="mono" spellcheck="false" aria-invalid={errors.start ? "true" : undefined} aria-describedby="start-help" />
              <span id="start-help" class="help" class:error={errors.start}>{errors.start || t().startHint}</span>
            </span>
          </label>
        {/if}
        <div class="row kv">
          <span class="k">{t().precheck}</span>
          <div class="grow">
            {#if !preview.findings?.length}
              <span class="ok">✓ {t().precheckClean}</span>
            {:else}
              <ul class="findings">
                {#each preview.findings as f, i (i)}
                  <li><span class={`dot ${f.serious ? "bad" : "warn"}`}></span>
                    <div>{f.msg}
                      {#if f.volume && !volume}<button type="button" class="btn small" onclick={suggestVolume}>{t().addVolume("/data")}</button>{/if}
                    </div>
                  </li>
                {/each}
              </ul>
              {#if serious}
                <label class="check"><input type="checkbox" bind:checked={precheckOk} /> {t().createAnyway}</label>
              {/if}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </section>
{/if}

<!-- Camino rápido (como Railway): con la revisión limpia, desplegar con lo detectado; el
     formulario completo queda en "Personalizar". -->
{#if reviewOk && repo && !custom && !mustPick}
  <section class="step" aria-labelledby="sfast">
    <div class="shead"><div><span class="num">3</span><h2 id="sfast">{t().fastTitle}</h2></div></div>
    <div class="box fast">
      <dl class="fsum">
        <dt>{t().appName}</dt><dd><code>{name}</code></dd>
        <dt>{t().address}</dt><dd><code>https://{root ? domain : `${effHost}.${domain}`}{path}</code></dd>
        <dt>{t().port}</dt><dd><code>{port}</code></dd>
        <dt>{t().services}</dt><dd>{[db && "PostgreSQL", mysql && "MariaDB", redis && "Redis"].filter(Boolean).join(" · ") || t().fastNone}</dd>
        <dt id="facc">{t().access}</dt>
        <dd>
          <div class="seg" role="radiogroup" aria-labelledby="facc">
            {#each [["vpn", t().accessVpn], ["public", t().accessPublic]] as [v, text]}
              <button type="button" role="radio" aria-checked={access === v} class:on={access === v} onclick={() => (access = v as "vpn" | "public")}>{text}</button>
            {/each}
          </div>
        </dd>
      </dl>
      {#if vars.length}
        <p class="fwarn" class:bad={reqMissing.length}>{reqMissing.length ? t().fastReq(reqMissing.length, reqMissing.slice(0, 3).join(", ")) : t().fastVars(vars.length, vars.slice(0, 3).map((v) => v.key).join(", "))}
          <button type="button" class="btn small quiet" onclick={() => { custom = true; rawOpen = true; }}>{t().fastAddVars}</button></p>
      {/if}
      {#if serious && !precheckOk}<p class="fwarn bad">{t().fastSerious}</p>{/if}
      <div class="go">
        <button type="button" class="btn primary" onclick={create} disabled={!configOk || job.locked}>{t().fastDeploy}</button>
        <button type="button" class="btn quiet" onclick={() => (custom = true)}>{t().fastCustom}</button>
        {#if !configOk && !(serious && !precheckOk)}<span class="help error">{Object.values(errors).find(Boolean)}</span>{/if}
      </div>
    </div>
  </section>
{/if}

<!-- 3 · Configuración -->
{#if reviewOk && (repo || mode === "template") && (custom || !repo || mustPick)}
  <section class="step" aria-labelledby="s3">
    <div class="shead"><div><span class="num">3</span><h2 id="s3">{t().stepConfig}</h2></div></div>
    <div class="box grid">
      <label class="f">
        <span class="lbl">{t().appName}</span>
        <input bind:value={name} class="mono" spellcheck="false" aria-invalid={errors.name ? "true" : undefined} aria-describedby="n-help"
          oninput={() => (name = name.toLowerCase().replace(/[^a-z0-9-]/g, "-"))} />
        <span id="n-help" class="help" class:error={errors.name && name}>{(name && errors.name) || t().appNameHint}</span>
      </label>
      <div class="f wide">
        <span class="lbl" id="addr-l">{t().address}</span>
        {#if root}
          <code class="url">https://{domain}</code>
        {:else}
          <div class="addr">
            <span class="pre">https://</span>
            <input bind:value={host} placeholder={name || "app"} class="mono" spellcheck="false" aria-labelledby="addr-l"
              aria-invalid={errors.host ? "true" : undefined} aria-describedby="h-help"
              oninput={() => (host = host.toLowerCase().replace(/[^a-z0-9-]/g, "-"))} />
            <span class="post">.{domain}</span>
          </div>
        {/if}
        <label class="check small"><input type="checkbox" bind:checked={root} /> {t().rootDomain}</label>
        {#if errors.host}<span id="h-help" class="help error">{errors.host}</span>{/if}
        <div class="owndom">
          <label class="f">
            <span class="lbl">{t().ownDomain}</span>
            <input bind:value={ownDomain} class="mono" placeholder="api.tuempresa.com" spellcheck="false" autocomplete="off"
              aria-invalid={errors.domain && ownDomain ? "true" : undefined}
              oninput={() => (ownDomain = ownDomain.toLowerCase().replace(/\s/g, ""))} />
          </label>
          {#if ownDomain && !ownOk}<span class="help error">{t().badDomain}</span>
          {:else if dnsInfo?.checking}<span class="help">{t().checkingDns}</span>
          {:else if dnsInfo?.ok}<span class="help okt">✓ {t().dnsOk(dnsInfo.ip ?? "")}</span>
          {:else if dnsInfo}
            <p class="help warn">{t().dnsMissing(ownDomain.trim(), dnsInfo.ip ?? "")} {t().dnsCname(root ? domain : `${effHost}.${domain}`)}</p>
            <label class="check small"><input type="checkbox" bind:checked={dnsAnyway} /> {t().dnsAnyway}</label>
          {:else}<span class="help">{t().ownDomainHint}</span>{/if}
        </div>
        {#if dir}
          <div class="pathrow">
            <label class="f">
              <span class="lbl">{t().pathOpt}</span>
              <input bind:value={path} class="mono" placeholder="/api" spellcheck="false" aria-invalid={errors.path ? "true" : undefined}
                oninput={() => (path = path.toLowerCase().replace(/[^a-z0-9._/-]/g, ""))} />
            </label>
            <span class="help" class:error={errors.path}>{errors.path || t().pathHint}</span>
            {#each (preview?.siblings ?? []).filter((x) => !x.path && x.dir !== dir) as sib (sib.name)}
              <button type="button" class="btn small quiet" onclick={() => { root = sib.host === "@"; host = root ? "" : sib.host; path = path || "/api"; }}>
                {t().shareWith(sib.name)}</button>
            {/each}
          </div>
        {/if}
      </div>
      <div class="f">
        <span class="lbl" id="acc-l">{t().access}</span>
        <div class="seg" role="radiogroup" aria-labelledby="acc-l">
          {#each [["vpn", t().accessVpn], ["public", t().accessPublic]] as [v, text]}
            <button type="button" role="radio" aria-checked={access === v} class:on={access === v} onclick={() => (access = v as "vpn" | "public")}>{text}</button>
          {/each}
        </div>
        {#if access === "public"}<span class="help warn">{t().publicWarn}</span>{/if}
      </div>
      <label class="f">
        <span class="lbl">{t().port}</span>
        <input bind:value={port} class="mono" inputmode="numeric" aria-invalid={errors.port ? "true" : undefined} />
        {#if errors.port}<span class="help error">{errors.port}</span>{/if}
      </label>
      <label class="f">
        <span class="lbl">{t().health}</span>
        <input bind:value={health} class="mono" placeholder="/healthz" spellcheck="false" aria-invalid={errors.health ? "true" : undefined} />
        <span class="help" class:error={errors.health}>{errors.health || t().healthHint}</span>
      </label>
      <label class="f">
        <span class="lbl">{t().ram}</span>
        <input bind:value={mem} class="mono" aria-invalid={errors.mem ? "true" : undefined} />
        <span class="help" class:error={errors.mem}>{errors.mem || t().memHint}</span>
      </label>
      <div class="f">
        <span class="lbl">{t().services}</span>
        <label class="check"><input type="checkbox" bind:checked={db} /> {t().postgresOpt}</label>
        <label class="check"><input type="checkbox" bind:checked={mysql} /> {t().mysqlOpt}</label>
        <label class="check"><input type="checkbox" bind:checked={redis} /> {t().redisOpt}</label>
      </div>
      <label class="f">
        <span class="lbl">{t().folderOpt}</span>
        <input bind:value={volume} class="mono" placeholder="/data" spellcheck="false" aria-invalid={errors.volume ? "true" : undefined} />
        <span class="help" class:error={errors.volume}>{errors.volume || t().folderOptHint}</span>
      </label>
    </div>
  </section>

  <!-- 4 · Variables de entorno -->
  <section class="step" aria-labelledby="s4">
    <div class="shead">
      <div><span class="num">4</span><h2 id="s4">{t().stepEnv}</h2></div>
      <div class="envacts">
        {#if examples.length}<button type="button" class="btn small quiet" onclick={useExamples}>{t().useExamples(examples.length)}</button>{/if}
        <button type="button" class="btn small quiet" onclick={() => (rawOpen = !rawOpen)} aria-expanded={rawOpen}>{t().pasteEnv}</button>
        <button type="button" class="btn small" onclick={() => vars.push({ key: "", value: "", where: "" })}>{t().addVar}</button>
      </div>
    </div>
    <p class="desc envdesc">{t().envDesc}</p>
    {#if rawOpen}
      <div class="box rawbox">
        <div class="rawtop">
          <label for="raw-env" class="muted">{t().bulkLabel}</label>
          <button type="button" class="btn small quiet" onclick={() => (rawShow = !rawShow)} aria-pressed={rawShow}>{rawShow ? t().bulkHide : t().bulkShow}</button>
        </div>
        <!-- svelte-ignore a11y_autofocus -->
        <textarea id="raw-env" bind:value={raw} class:hidden={!rawShow} rows="8" spellcheck="false" autocomplete="off" autofocus
          placeholder={"API_KEY=…\nSMTP_PASSWORD=…"}></textarea>
        <div class="rawfoot">
          <span class="help" class:error={rawBad.length}>
            {rawBad.length ? t().rawBad(rawBad.map((l) => l.n).join(", ")) : rawLines.length ? t().rawCount(rawLines.length) : t().bulkHint}
          </span>
          <button type="button" class="btn small quiet" onclick={() => { raw = ""; rawOpen = false; }}>{t().cancel}</button>
          <button type="button" class="btn small primary" disabled={!rawLines.length} onclick={applyRaw}>{t().rawApply}</button>
        </div>
      </div>
    {/if}
    <div class="box">
      {#each vars as v, i (i)}
        <div class="row var">
          <label class="vf">
            <span class="sr-only">{t().varName}</span>
            <input bind:value={v.key} class="mono" placeholder="API_KEY" spellcheck="false" aria-invalid={varErrors[i] ? "true" : undefined}
              oninput={() => (v.key = v.key.toUpperCase().replace(/[^A-Z0-9_]/g, "_"))} />
          </label>
          <label class="vf grow">
            <span class="sr-only">{t().varValue} {v.key}</span>
            <input bind:value={v.value} type={SECRET_TYPE} {...noSave} class="secret-field" placeholder={t().varValue} spellcheck="false" />
          </label>
          <button type="button" class="btn small quiet danger" onclick={() => vars.splice(i, 1)} aria-label={t().removeX(v.key || t().varName)}>{t().remove}</button>
          {#if varErrors[i]}<span class="vnote error">{varErrors[i]}</span>
          {:else if v.where || v.required || v.example}
            <span class="vnote">
              {#if v.required}<span class="req" class:done={v.value}>{t().varRequired}</span>{/if}
              {#if v.where}{t().envFound(v.where)}{/if}
              {#if v.example && !v.value}
                {v.where ? " · " : ""}{t().varExample} <code>{v.example}</code>
                <button type="button" class="linkbtn" onclick={() => (v.value = v.example!)}>{t().useIt}</button>
              {/if}
            </span>
          {/if}
        </div>
      {:else}
        <p class="row muted">{t().noVars}</p>
      {/each}
    </div>
    {#if reqMissing.length}<p class="help error">{t().envReqMissing(reqMissing.length, reqMissing.slice(0, 4).join(", "))}</p>
    {:else if missing}<p class="help warn">{t().envMissing(missing)}</p>{/if}
  </section>

  <!-- 5 · Crear -->
  <section class="step" aria-labelledby="s5">
    <div class="shead"><div><span class="num">5</span><h2 id="s5">{t().stepCreate}</h2></div></div>
    <div class="box final">
      <code class="cmd"><span class="prompt" aria-hidden="true">$ </span>{command}</code>
      {#if filled.length}<p class="help">{t().envStdin}</p>{/if}
      <h3>{t().willHappen}</h3>
      <ol>
        {#if mode === "template"}<li>{t().happen3tpl}</li>{/if}
        <li>{t().happen1}</li>
        <li>{t().happen2}</li>
        {#if dir}<li>{t().happenDir(dir, `andamio-${name}.yml`)}</li>{/if}
        {#if filled.length}<li>{t().happenEnv(filled.length)}</li>{/if}
        {#if mode !== "template"}<li>{t().happen3(repo)}</li>{/if}
      </ol>
      <div class="go">
        <button type="button" class="btn primary" onclick={create} disabled={!configOk || job.locked}>{t().createApp}</button>
        {#if !configOk}<span class="help error">{t().fixFirst}</span>{/if}
      </div>
    </div>
  </section>
{/if}

{#snippet folderRow(f: api.Folder)}
  <button type="button" role="radio" aria-checked={dir === f.dir} class="frow" class:on={dir === f.dir} disabled={reviewing}
    onclick={() => dir !== f.dir && pick(repo, f.dir)}>
    <span class="fdot" aria-hidden="true"></span><code>{f.dir}/</code>
    {#if f.role && !f.lib}<span class={`role ${f.role}`}>{t().folderRole[f.role]}</span>{/if}
    <span class="muted">{[f.framework || f.label, f.dockerfile && "Dockerfile", f.lib && t().folderLib].filter(Boolean).join(" · ")}</span>
  </button>
{/snippet}

{#snippet folderPick()}
  <div class="box folders" role="radiogroup" aria-label={t().pickFolder}>
    <div class="row fhead">
      <span>{rootApp ? t().foldersFound : t().foldersPick}</span>
      {#if folders.length > 8}
        <input type="search" bind:value={folderQuery} placeholder={t().folderSearch} aria-label={t().folderSearch} spellcheck="false" />
      {/if}
    </div>
    {#if rootApp && !folderQuery}
      <button type="button" role="radio" aria-checked={!dir} class="frow" class:on={!dir} disabled={reviewing}
        onclick={() => dir && pick(repo, "")}>
        <span class="fdot" aria-hidden="true"></span><code>/</code><span class="muted">{t().repoRoot}</span>
      </button>
    {/if}
    {#each appFolders as f (f.dir)}{@render folderRow(f)}{/each}
    {#if libFolders.length}
      {#if showLibs || folderQuery}
        {#each libFolders as f (f.dir)}{@render folderRow(f)}{/each}
      {:else}
        <button type="button" class="row more" onclick={() => (showLibs = true)}>{t().folderMoreLibs(libFolders.length)}</button>
      {/if}
    {/if}
    {#if folderQuery && !appFolders.length && !libFolders.length}<p class="row muted">{t().folderNone}</p>{/if}
    <form class="row other" onsubmit={(e) => { e.preventDefault(); if (otherOk) pick(repo, otherDir.replace(/^\/|\/$/g, "")); }}>
      <label for="other-dir" class="muted">{t().folderOther}</label>
      <input id="other-dir" bind:value={otherDir} class="mono" placeholder="services/pagos/api" spellcheck="false" />
      <button type="submit" class="btn small" disabled={!otherOk || reviewing}>{t().folderReview}</button>
    </form>
    {#if dir}
      <label class="row check small"><input type="checkbox" bind:checked={fromRoot} /> {t().buildFromRoot}</label>
    {/if}
  </div>
{/snippet}

<style>
  .folders { margin-bottom: var(--space-3); }
  .fhead { font-size: 13.5px; color: var(--muted); justify-content: space-between; }
  .fhead input, .other input {
    font: 13px var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 6px 9px; min-width: 200px;
  }
  .other input { font-family: var(--mono); flex: 1; }
  .other label { font-size: 13.5px; }
  .more { width: 100%; text-align: left; font: 13.5px var(--sans); color: var(--accent); background: none; border: 0; border-bottom: 1px solid var(--line); cursor: pointer; }
  .role { font-size: 11.5px; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: var(--sunken); color: var(--muted); }
  .role.web, .role.site { background: color-mix(in oklch, var(--chart-1) 14%, var(--surface)); color: var(--accent); }
  .role.api { background: color-mix(in oklch, var(--chart-2) 16%, var(--surface)); color: var(--warn-text); }
  .role.worker { background: color-mix(in oklch, var(--ok) 14%, var(--surface)); color: var(--ok-text); }
  .frow {
    width: 100%; display: flex; align-items: center; gap: var(--space-3); text-align: left; font: inherit; color: var(--ink);
    background: transparent; border: 0; border-bottom: 1px solid var(--line); padding: var(--space-3) var(--space-4); cursor: pointer;
  }
  .frow:hover:not(:disabled), .frow:focus-visible { background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .frow.on { background: color-mix(in oklch, var(--accent) 9%, var(--surface)); }
  .frow code { font-weight: 600; min-width: 120px; }
  .frow .muted { font-size: 13px; }
  .fdot { width: 14px; height: 14px; border-radius: 50%; border: 1.5px solid var(--line); flex: none; display: grid; place-items: center; }
  .frow.on .fdot { border-color: var(--accent); background: radial-gradient(circle, var(--accent) 0 3.5px, transparent 4px); }
  .fast { padding: var(--space-4) var(--space-5); display: grid; gap: var(--space-3); }
  .fsum { display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 8px var(--space-4); margin: 0; align-items: center; }
  .fsum dt { color: var(--muted); font-size: 14px; }
  .fsum dd { margin: 0; overflow-wrap: anywhere; }
  .fwarn { margin: 0; font-size: 13.5px; color: var(--warn-text); display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
  .fwarn.bad { color: var(--bad-text); }
  .owndom { display: grid; gap: 4px; margin-top: var(--space-3); }
  .okt { color: var(--ok-text); }
  .pathrow { display: flex; flex-wrap: wrap; align-items: end; gap: var(--space-2) var(--space-3); margin-top: var(--space-2); }
  .pathrow .f { width: 160px; }
  .step { margin-top: var(--space-6); }
  .shead > div { display: flex; align-items: center; gap: var(--space-3); }
  .num {
    width: 24px; height: 24px; border-radius: 50%; display: inline-grid; place-items: center; flex: none;
    font: 600 12px/1 var(--sans); color: var(--chalk); background: var(--print);
  }
  .chosen { margin: 0; font-size: 15px; }
  .row { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2) var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); margin: 0; }
  .row:last-child { border-bottom: 0; }
  .muted { color: var(--muted); }
  .bad { color: var(--bad-text); }
  .ok { color: var(--ok-text); }
  .search { display: flex; gap: var(--space-2); padding: var(--space-3); border-bottom: 1px solid var(--line); background: var(--sunken); }
  .search input, .f input:not([type="checkbox"]) {
    flex: 1; font: 14px var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 8px 10px; min-width: 0;
  }
  input.mono { font-family: var(--mono); font-size: 13px; }
  input:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent) 28%, transparent); outline-offset: 0; border-color: var(--accent); }
  input[aria-invalid="true"] { border-color: var(--bad); }
  ul { list-style: none; margin: 0; padding: 0; }
  .pick {
    width: 100%; display: flex; align-items: center; flex-wrap: wrap; gap: 4px var(--space-3); text-align: left;
    font: inherit; color: var(--ink); background: transparent; border: 0; border-bottom: 1px solid var(--line);
    padding: var(--space-3) var(--space-4); cursor: pointer;
  }
  li:last-child .pick { border-bottom: 0; }
  .pick:hover, .pick:focus-visible { background: color-mix(in oklch, var(--accent) 6%, var(--surface)); }
  .rname { font-weight: 600; }
  .rdesc { color: var(--muted); font-size: 13px; flex-basis: 100%; }
  .rwhen { color: var(--muted); font-size: 12.5px; margin-left: auto; }
  .tpl { margin-top: var(--space-2); margin-left: calc(-1 * var(--space-2)); }
  .kv { align-items: flex-start; }
  .k { width: 130px; flex: none; color: var(--muted); font-size: 14px; padding-top: 2px; }
  .grow { flex: 1; min-width: 240px; }
  .field { display: grid; gap: 5px; }
  details { margin-top: var(--space-2); }
  summary { cursor: pointer; color: var(--accent); font-size: 14px; }
  .code {
    margin: var(--space-2) 0 0; max-height: 340px; overflow: auto; background: var(--term); color: var(--term-ink);
    border-radius: 8px; padding: var(--space-3) var(--space-4); font: 12px/1.6 var(--mono); white-space: pre;
  }
  .findings { display: grid; gap: var(--space-2); }
  .findings li { display: flex; gap: var(--space-3); align-items: baseline; font-size: 14px; }
  .findings .btn { margin-top: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--space-4) var(--space-5); padding: var(--space-4) var(--space-5); }
  .f { display: grid; gap: 6px; align-content: start; }
  .lbl { font-size: 13px; color: var(--muted); }
  .help { font-size: 12.5px; color: var(--muted); }
  .help.error { color: var(--bad-text); }
  .help.warn { color: var(--warn-text); }
  .f.wide { grid-column: span 2; }
  @media (max-width: 640px) { .f.wide { grid-column: auto; } }
  .addr { display: flex; align-items: center; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); overflow: hidden; }
  .addr input { border: 0; border-radius: 0; padding: 8px 4px; }
  .addr .pre, .addr .post { color: var(--muted); font: 13px var(--mono); padding: 0 6px; white-space: nowrap; }
  .url { font-size: 13px; padding: 8px 0; }
  .check { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink); cursor: pointer; }
  .check.small { font-size: 13px; color: var(--muted); }
  .seg { display: inline-flex; padding: 3px; gap: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--sunken); width: max-content; }
  .seg button { font: 500 13px/1 var(--sans); color: var(--muted); background: transparent; border: 0; border-radius: 6px; padding: 7px 12px; cursor: pointer; }
  .seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px oklch(0.2 0.02 262 / 0.12); }
  .envdesc { margin: -4px 0 var(--space-3); }
  .envacts { display: flex; gap: var(--space-2); }
  .rawbox { padding: var(--space-3) var(--space-4); display: grid; gap: var(--space-2); margin-bottom: var(--space-3); }
  .rawtop, .rawfoot { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); justify-content: space-between; }
  .rawfoot .help { flex: 1; }
  .rawtop label { font-size: 13px; }
  .rawbox textarea {
    font: 13px/1.55 var(--mono); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 8px 10px; width: 100%; resize: vertical; min-height: 140px;
  }
  .rawbox textarea.hidden { -webkit-text-security: disc; }
  .var { flex-wrap: wrap; }
  .vf { display: flex; }
  .vf input {
    font: 14px var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 8px 10px; width: 100%;
  }
  .vf input.mono { font-family: var(--mono); font-size: 13px; width: 220px; }
  .vnote { flex-basis: 100%; font-size: 12.5px; color: var(--muted); }
  .vnote.error { color: var(--bad-text); }
  .vnote code { font-size: 12px; }
  .req { display: inline-block; margin-right: 6px; padding: 0 6px; border-radius: 999px; font-size: 11.5px; font-weight: 600;
    color: var(--bad-text); background: color-mix(in oklch, var(--bad) 12%, var(--surface)); }
  .req.done { color: var(--ok-text); background: color-mix(in oklch, var(--ok) 12%, var(--surface)); }
  .linkbtn { font: inherit; color: var(--accent); background: none; border: 0; padding: 0 2px; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
  p.help { margin: var(--space-2) 0 0; }
  .final { padding: var(--space-4) var(--space-5); display: grid; gap: var(--space-3); }
  .final .cmd { display: block; white-space: pre-wrap; background: var(--term); color: var(--term-ink); border-radius: 8px; padding: var(--space-3) var(--space-4); font-size: 13px; overflow-wrap: anywhere; }
  .prompt { color: var(--term-muted); }
  .final h3 { margin: var(--space-2) 0 0; font-size: 14px; }
  .final ol { margin: 0; padding-left: 1.2em; color: var(--muted); display: grid; gap: 4px; font-size: 14px; }
  .go { display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-2); }
  .pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); display: inline-block; }
  @media (prefers-reduced-motion: no-preference) { .pulse { animation: pulse 1.2s ease-in-out infinite; } }
  @keyframes pulse { 50% { opacity: 0.25; } }
</style>
