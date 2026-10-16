<!-- El andamio: dos postes, tres tablones y una diagonal que lo arriostra (la marca de ejemplo.com). -->
<script lang="ts">
  let { size = 18 }: { size?: number } = $props();
</script>

<svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
  <path d="M6 3v18M18 3v18" />
  <path d="M4 7h16M4 13h16M4 19h16" />
  <path d="M6 13l12-6" stroke-width="1.5" />
</svg>
