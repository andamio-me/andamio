// Compila el panel (andamio ui) a ../ui: archivos estáticos que sirve bin/andamio. Quien usa
// andamio no necesita Node; solo quien cambia la interfaz (tools/ui-build.sh, en Docker).
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: "../ui",
    emptyOutDir: true,
    assetsDir: "assets",
    // Sin inlining: la CSP del panel (default-src 'self') no deja data: para fuentes ni scripts.
    assetsInlineLimit: 0,
    modulePreload: { polyfill: false },
    sourcemap: false,
  },
});
