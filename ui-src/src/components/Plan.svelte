<!--
  El plano vivo de tu servidor, en cianotipia como el de ejemplo.com: Internet y tu VPN entran por
  Traefik, que reparte a tus apps (públicas y solo por VPN); las que usan base o Redis tienen su
  flecha. Cada app muestra su estado y su RAM, y abre su detalle. Al lado, la cartela del plano
  con los datos del servidor. En pantallas chicas, el mismo contenido en texto.
-->
<script lang="ts">
  import type { App, Platform as PlatformData, Security, Server } from "../lib/api";
  import { bytes, mib, status, uptime } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import Platform from "./Platform.svelte";

  let { apps, server, domain, alias, loading = false, offline = false, platform = null, security = null, oncheck }: {
    apps: App[]; server: Server | null; domain: string; alias: string; loading?: boolean; offline?: boolean;
    platform?: PlatformData | null; security?: Security | null; oncheck: () => void;
  } = $props();

  const NODE_H = 54, GAP = 10, PAD = 14, GROUP_GAP = 56;
  const X = { entry: 24, traefik: 214, group: 422, data: 712 };
  const W = { entry: 142, traefik: 150, group: 236, data: 140 };

  const pub = $derived(apps.filter((a) => a.access === "public"));
  const vpn = $derived(apps.filter((a) => a.access !== "public"));
  const usesDb = $derived(apps.some((a) => a.db));
  const usesRedis = $derived(apps.some((a) => a.redis));
  const width = $derived(usesDb || usesRedis ? 876 : 682);

  const groupH = (n: number) => PAD * 2 + Math.max(n, 1) * NODE_H + (Math.max(n, 1) - 1) * GAP;
  const layout = $derived.by(() => {
    const pubY = 44, pubH = groupH(pub.length);
    const vpnY = pubY + pubH + GROUP_GAP, vpnH = groupH(vpn.length);
    const pubMid = pubY + pubH / 2, vpnMid = vpnY + vpnH / 2;
    const trMid = (pubMid + vpnMid) / 2;
    const nodeY = (y0: number, i: number) => y0 + PAD + i * (NODE_H + GAP);
    const nodes = [
      ...pub.map((a, i) => ({ a, y: nodeY(pubY, i) })),
      ...vpn.map((a, i) => ({ a, y: nodeY(vpnY, i) })),
    ];
    const mids = (f: (a: App) => boolean) => nodes.filter((n) => f(n.a)).map((n) => n.y + NODE_H / 2);
    const avg = (xs: number[]) => xs.reduce((s, x) => s + x, 0) / Math.max(xs.length, 1);
    let pgY = Math.max(24, avg(mids((a) => a.db)) - 34);
    let rdY = Math.max(24, avg(mids((a) => a.redis)) - 34);
    if (usesDb && usesRedis && Math.abs(rdY - pgY) < 84) rdY = pgY + 84;
    const height = Math.max(vpnY + vpnH + 28, rdY + 100, pgY + 100);
    return { pubY, pubH, vpnY, vpnH, pubMid, vpnMid, trMid, nodes, pgY, rdY, height };
  });

  // Apps que comparten dirección por rutas (el back en /api bajo el front): un lazo entre las dos.
  const shared = $derived(layout.nodes.flatMap((n) => {
    if (!n.a.path) return [];
    const base = layout.nodes.find((m) => m.a.host === n.a.host && !m.a.path);
    return base ? [{ y1: base.y + NODE_H / 2, y2: n.y + NODE_H / 2, path: n.a.path }] : [];
  }));

  const curve = (x1: number, y1: number, x2: number, y2: number) => {
    const m = (x1 + x2) / 2;
    return `M${x1} ${y1} C${m} ${y1} ${m} ${y2} ${x2 - 2} ${y2}`;
  };

  // Las líneas se dibujan una sola vez, al abrir el panel (no en cada actualización).
  let drawn = $state(false);
  $effect(() => {
    if (!loading && !drawn) setTimeout(() => (drawn = true), 1600);
  });

  const now = new Date();
  const stamp = now.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const pct = (a: number, b: number) => (b ? Math.min(100, (a / b) * 100) : 0);
</script>

<figure class="plan blueprint" aria-labelledby="plan-title">
  <figcaption id="plan-title" class="sr-only">{t().planAlt}</figcaption>

  <div class="drawing">
    <svg viewBox={`0 0 ${width} ${layout.height}`} role="group" aria-labelledby="plan-svg-title" class="svg">
      <title id="plan-svg-title">{t().planAlt}</title>
      <defs>
        <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M1 1 L9 5 L1 9" fill="none" class="chalk-stroke" stroke-width="1.5" />
        </marker>
      </defs>

      <!-- Grupos: públicas y solo por VPN. -->
      {#each [{ y: layout.pubY, h: layout.pubH, label: t().publicGroup, list: pub }, { y: layout.vpnY, h: layout.vpnH, label: t().vpnGroup, list: vpn }] as g}
        <rect x={X.group} y={g.y} width={W.group} height={g.h} rx="10" class="group" />
        <text x={X.group + 12} y={g.y - 9} class="label">{g.label}</text>
        {#if !g.list.length}
          <text x={X.group + W.group / 2} y={g.y + g.h / 2 + 4} class="label" text-anchor="middle">{loading ? t().loading : t().noneInGroup}</text>
        {/if}
      {/each}

      <!-- Flechas: se dibujan una vez. -->
      {#each [
        { d: curve(X.entry + W.entry, layout.pubMid, X.traefik, layout.trMid - 12) },
        { d: curve(X.entry + W.entry, layout.vpnMid, X.traefik, layout.trMid + 12), label: t().tunnel, ly: (layout.vpnMid + layout.trMid) / 2 + 14 },
        { d: curve(X.traefik + W.traefik, layout.trMid - 8, X.group, layout.pubMid) },
        { d: curve(X.traefik + W.traefik, layout.trMid + 8, X.group, layout.vpnMid) },
        ...layout.nodes.filter((n) => n.a.db).map((n) => ({ d: curve(X.group + PAD + W.group - PAD * 2, n.y + NODE_H / 2, X.data, layout.pgY + 34) })),
        ...layout.nodes.filter((n) => n.a.redis).map((n) => ({ d: curve(X.group + PAD + W.group - PAD * 2, n.y + NODE_H / 2 + 6, X.data, layout.rdY + 34) })),
      ] as e, i (e.d)}
        <path d={e.d} pathLength="1" fill="none" class="edge" class:draw={!drawn} style:--i={i} marker-end="url(#flecha)" />
        {#if e.label}
          <text x={X.entry + W.entry + 10} y={e.ly} class="label small">{e.label}</text>
        {/if}
      {/each}

      <!-- Entradas y Traefik. -->
      {#each [
        { x: X.entry, y: layout.pubMid - 28, w: W.entry, h: 56, title: t().internet, sub: t().visitors },
        { x: X.entry, y: layout.vpnMid - 28, w: W.entry, h: 56, title: t().vpn, sub: t().vpnSub },
        { x: X.traefik, y: layout.trMid - 38, w: W.traefik, h: 76, title: t().traefik, sub: t().traefikSub },
        ...(usesDb ? [{ x: X.data, y: layout.pgY, w: W.data, h: 68, title: t().postgres, sub: t().postgresSub }] : []),
        ...(usesRedis ? [{ x: X.data, y: layout.rdY, w: W.data, h: 68, title: t().redis, sub: t().redisSub }] : []),
      ] as n (n.title)}
        <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="6" class="node" />
        <text x={n.x + 14} y={n.y + n.h / 2 - 3} class="title">{n.title}</text>
        <text x={n.x + 14} y={n.y + n.h / 2 + 15} class="sub">{n.sub}</text>
      {/each}

      <!-- Mismo dominio, otra ruta: el lazo por la izquierda, con la ruta. -->
      {#each shared as s (s.y2)}
        {@const lx = X.group + PAD}
        <path d={`M${lx} ${s.y1} C${lx - 16} ${s.y1} ${lx - 16} ${s.y2} ${lx} ${s.y2}`} fill="none" class="edge shared" />
      {/each}

      <!-- Tus apps: cada una abre su detalle. -->
      {#each layout.nodes as { a, y } (a.name)}
        {@const st = status(a)}
        {@const ghost = a.stopped || !a.live}
        <a href={`#/app/${a.name}`} aria-label={`${a.name}: ${offline ? t().noData : st.text}`} class="app-link">
          <rect x={X.group + PAD} y={y} width={W.group - PAD * 2} height={NODE_H} rx="6" class="node app" class:ghost />
          <text x={X.group + PAD + 14} y={y + 23} class="title" class:dim={ghost}>{a.name}</text>
          <text x={X.group + PAD + 14} y={y + 41} class="sub">
            {offline ? t().noData : st.text}{a.live?.mem && !offline ? ` · ${mib(a.live.mem)}` : ""}
          </text>
          <circle cx={X.group + W.group - PAD - 16} cy={y + 18} r="4.5" class={`state ${offline ? "" : st.tone}`} />
          {#if a.path}<text x={X.group + W.group - PAD - 14} y={y + 41} class="sub path" text-anchor="end">{a.path}</text>{/if}
        </a>
      {/each}
    </svg>

    <!-- Lo mismo en texto: visible en pantallas chicas; para lectores de pantalla siempre está el SVG. -->
    <div class="plain">
      {#each [{ label: t().publicGroup, list: pub }, { label: t().vpnGroup, list: vpn }] as g}
        <section>
          <h3>{g.label}</h3>
          {#if g.list.length}
            <ul>
              {#each g.list as a (a.name)}
                {@const st = status(a)}
                <li>
                  <a href={`#/app/${a.name}`} class:ghost={a.stopped || !a.live}>
                    <span class="title">{a.name}{#if a.path}<span class="sub"> {a.path}</span>{/if}</span>
                    <span class="sub"><span class={`pdot ${offline ? "" : st.tone}`}></span>{offline ? t().noData : st.text}{a.live?.mem ? ` · ${mib(a.live.mem)}` : ""}</span>
                  </a>
                </li>
              {/each}
            </ul>
          {:else}
            <p class="sub">{t().noneInGroup}</p>
          {/if}
        </section>
      {/each}
    </div>
  </div>

  <!-- La cartela: el recuadro de datos de un plano de obra. -->
  <aside class="cartela" aria-label={t().sheet}>
    <div class="head">{t().sheet}</div>
    <dl>
      <div><dt>{t().domain}</dt><dd>{domain}</dd></div>
      <div><dt>{t().server}</dt><dd>{alias}</dd></div>
      {#if server}
        <div><dt>{t().uptime}</dt><dd>{uptime(server.uptime)}</dd></div>
        <div><dt>{t().load}</dt><dd>{server.load.toFixed(2)} / {server.cpus} {t().cpu}</dd></div>
        <div>
          <dt>{t().ram}</dt>
          <dd>{t().of(bytes(server.mem_used), bytes(server.mem_total))}
            <span class="meter" role="img" aria-label={`${Math.round(pct(server.mem_used, server.mem_total))}%`}><span style:width={`${pct(server.mem_used, server.mem_total)}%`}></span></span>
          </dd>
        </div>
        <div>
          <dt>{t().disk}</dt>
          <dd>{t().of(bytes(server.disk_used), bytes(server.disk_total))}
            <span class="meter" class:hot={pct(server.disk_used, server.disk_total) >= 80} role="img" aria-label={`${Math.round(pct(server.disk_used, server.disk_total))}%`}><span style:width={`${pct(server.disk_used, server.disk_total)}%`}></span></span>
          </dd>
        </div>
      {:else}
        <div><dt>{t().uptime}</dt><dd>{loading ? t().loading : t().noData}</dd></div>
      {/if}
      <div><dt>{t().drawn}</dt><dd>{stamp}</dd></div>
    </dl>
  </aside>

  <Platform {platform} {security} loading={loading} {oncheck} />
</figure>

<style>
  .plan {
    margin: 0;
    border-radius: 14px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 252px;
    gap: var(--space-5);
    padding: var(--space-6) var(--space-6) var(--space-5);
    box-shadow: 0 24px 48px -28px oklch(0.2 0.05 262 / 0.5);
  }
  .drawing { min-width: 0; }
  .svg { display: block; width: 100%; height: auto; max-height: 560px; font-family: var(--sans); }
  .chalk-stroke { stroke: var(--chalk); }
  .group { fill: none; stroke: var(--chalk-dim); stroke-width: 1; stroke-dasharray: 6 5; }
  .label { fill: var(--chalk-dim); font-size: 13px; }
  .label.small { font-size: 12px; }
  .edge { stroke: var(--chalk); stroke-width: 1.5; }
  .node { fill: var(--print-deep); stroke: var(--chalk); stroke-width: 1.25; }
  .node.ghost { fill: none; stroke: var(--chalk-dim); stroke-dasharray: 5 4; }
  .title { fill: var(--chalk); font-size: 15px; font-weight: 600; }
  .title.dim { fill: var(--chalk-dim); }
  .sub { fill: var(--chalk-dim); font-size: 12.5px; }
  .state { fill: var(--chalk-dim); }
  .state.ok { fill: oklch(0.84 0.15 155); }
  .state.warn { fill: oklch(0.87 0.13 85); }
  .state.bad { fill: oklch(0.76 0.17 25); }
  .app-link { cursor: pointer; outline: none; }
  .app-link .node.app { transition: fill 150ms var(--ease), stroke-width 150ms var(--ease); }
  .app-link:hover .node.app { fill: color-mix(in oklch, var(--print-deep) 70%, var(--chalk)); }
  .app-link:focus-visible .node.app { stroke: var(--chalk); stroke-width: 2.5; stroke-dasharray: none; }

  /* En escritorio está el plano (con sus enlaces); el texto es para pantallas chicas. */
  .plain { display: none; }
  .plain h3 { margin: 0 0 var(--space-2); font-size: 13px; font-weight: 500; color: var(--chalk-dim); }
  .plain section + section { margin-top: var(--space-5); }
  .plain ul { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
  .plain a {
    display: grid; gap: 2px; padding: var(--space-3) var(--space-4); border-radius: 6px;
    border: 1px solid color-mix(in oklch, var(--chalk) 60%, transparent); background: var(--print-deep); color: var(--chalk);
  }
  .plain a:hover { text-decoration: none; background: color-mix(in oklch, var(--print-deep) 70%, var(--chalk)); }
  .plain .title { font-weight: 600; }
  .plain a.ghost { background: transparent; border-style: dashed; border-color: var(--chalk-dim); }
  .plain a.ghost .title { color: var(--chalk-dim); }
  .plain .sub { color: var(--chalk-dim); font-size: 13px; display: inline-flex; align-items: center; gap: 7px; }
  .pdot { width: 8px; height: 8px; border-radius: 50%; background: var(--chalk-dim); }
  .pdot.ok { background: oklch(0.84 0.15 155); }
  .pdot.warn { background: oklch(0.87 0.13 85); }
  .pdot.bad { background: oklch(0.76 0.17 25); }

  .cartela {
    align-self: end;
    border: 1px solid var(--chalk-dim);
    font-size: 13px;
    color: var(--chalk);
  }
  .cartela .head {
    padding: 7px 12px; border-bottom: 1px solid var(--chalk-dim);
    font-size: 11.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--chalk-dim);
  }
  .cartela dl { margin: 0; }
  .cartela dl > div { display: grid; grid-template-columns: 84px minmax(0, 1fr); border-bottom: 1px solid color-mix(in oklch, var(--chalk-dim) 55%, transparent); }
  .cartela dl > div:last-child { border-bottom: 0; }
  .cartela dt { padding: 7px 12px; color: var(--chalk-dim); border-right: 1px solid color-mix(in oklch, var(--chalk-dim) 55%, transparent); }
  .cartela dd { margin: 0; padding: 7px 12px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
  .meter { display: block; height: 4px; margin-top: 6px; background: color-mix(in oklch, var(--chalk) 22%, transparent); }
  .meter > span { display: block; height: 100%; background: var(--chalk); }
  .meter.hot > span { background: oklch(0.87 0.13 85); }

  @media (max-width: 1000px) {
    .plan { grid-template-columns: 1fr; }
    .cartela dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  }
  @media (max-width: 640px) {
    .plan { padding: var(--space-5) var(--space-4); border-radius: 10px; }
    .svg { display: none; }
    .plain { display: block; }
  }
  .shared { stroke-dasharray: 3 3; opacity: 0.7; }
  .path { font-family: var(--mono); }
</style>
