# 0038. App de escritorio para Windows, macOS y Linux, compilada en el repo público

- **Estado:** Aceptada
- **Fecha:** 2026-10-28

## Contexto
La app de escritorio (Tauri, ADR 0028) solo tenía instalador de Windows, se compilaba en el repo
privado y se publicaba en un repo de descargas de pruebas. andamio también corre en Linux y macOS.
Compilar para macOS en un repo privado cuesta 10 veces los minutos de Actions, y quien la descarga
no puede ver de qué código salió.

## Decisión
- `desktop/` y `.github/workflows/desktop.yml` van a la plantilla pública (`andamio-me/andamio`) y
  se compilan **ahí**: un tag `desktop-vX.Y.Z` compila Windows (NSIS), Linux (AppImage y `.deb`,
  en Ubuntu 22.04 por la glibc) y macOS (universal: Apple Silicon e Intel), y publica un release con
  todo y `latest.json` para el actualizador. El workflow solo corre en ese repo.
- Las descargas tienen nombre fijo (`andamio-macos.dmg`, …): la landing enlaza a
  `releases/latest/download/<nombre>`.
- La llave privada que firma las actualizaciones está en los secretos del repo público; la pública,
  dentro de la app. gitleaks la permite en `.gitleaks.toml` (no es un secreto).
- Sin certificados de Apple ni de Microsoft por ahora: macOS con firma ad-hoc (se permite una vez en
  Ajustes del Sistema → Privacidad y seguridad), Windows con el aviso de SmartScreen. Se explica en
  el release, el README y la landing.
- En Linux y macOS la app arranca el panel con tu shell de login y suma al PATH donde lo dejan
  `andamio setup` y Homebrew (una app abierta desde el escritorio no hereda el PATH de la terminal).

## Consecuencias
- Cualquiera puede ver que el instalador sale del código público, y compilar es gratis.
- El actualizador de Linux solo actualiza el AppImage; el `.deb` se actualiza a mano.
- Las versiones anteriores a la 0.2.0 buscaban actualizaciones en el repo de pruebas: hay que
  instalar la 0.2.0 a mano una vez.
- Pagar Apple Developer (99 USD al año) y un certificado de Windows quita los avisos: cuando haya
  usuarios que lo justifiquen.
