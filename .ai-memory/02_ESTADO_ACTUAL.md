# 02 · Estado Actual del Proyecto

> Actualiza este archivo **al final de cada sesión**. `[ ]` = pendiente · `[~]` = en curso · `[x]` = hecho.

_Última actualización: 2026-05-30 (6ª iteración)_

## Resumen
- Existe el **plan maestro** (`plan.md`) y la **zona de memoria** (`.ai-memory/`).
- **Navegador funcional y ya en uso real** (el historial contiene navegación del usuario).
- UI: ventana frameless con **esquinas redondeadas** (DWM Win11), barra de título con logotipo pixmap de Orbital, pestañas
  (abrir/cerrar/clic-central/**drag&drop**), Omnibox con **autocompletado (Trie)**, progreso. Todos los controles de la interfaz usan iconos vectoriales SVG de **Lucide Icons** (`lucide.dev`).
- **Logotipo de la App:** Integrado `orbital_icon.png` en la ventana, la barra de título superior y en el HTML base de la página de inicio `orbital://start`.
- **Modos de UI Configurables:** Opción de alternar entre pestañas laterales (verticales) y superiores (horizontales, tipo Chrome), y entre descargas en pestaña o a través de un **panel lateral derecho flotante** (`DownloadsPanel`).
- **Zonas**: Historial (`orbital://history`/Ctrl+H), Descargas (`orbital://downloads`/Ctrl+J o panel),
  Marcadores (`orbital://bookmarks`/Ctrl+Shift+O), **Configuración** (diálogo nativo, Ctrl+,).
- **Páginas de error y de crash** temadas cuando una pestaña falla o el render muere.
- **Persistencia**: perfil con cookies y caché en disco (o privado); restauración de sesión;
  descargas; zoom; buscar en página.
- **Puente QWebChannel** (objeto `orbital`; falta inyectar `qwebchannel.js`).
- Entorno: **Python 3.14.5**, **PyQt6 6.11** + **PyQt6-WebEngine 6.11**.
- Ejecutar con: `python nexus_browser/main.py`.
- ⚠️ La config actual tiene `home_url`/`search_endpoint = "google.com"` (cambiado por el
  usuario); para que la búsqueda funcione debería ser p.ej. `https://www.google.com/search?q=`.

## Datos persistidos en `nexus_browser/data/`
- `profile/` cookies y storage del perfil · `cache/` caché HTTP en disco
- `nexus.db` (historial + marcadores en SQLite, migrado a `orbital.db`) · `session.json` pestañas abiertas
- `downloads/` archivos descargados

## Atajos de teclado disponibles
`Ctrl+T` nueva · `Ctrl+W` cerrar · `Ctrl+L` Omnibox · `Ctrl+R`/`F5` recargar ·
`Alt+←/→` atrás/adelante · `Ctrl+D` marcador · `Ctrl+H` historial · `Ctrl+J` descargas ·
`Ctrl+Shift+O` marcadores · `Ctrl+F` buscar en página · `Ctrl++/-/0` zoom ·
`Ctrl+B` ocultar/mostrar barra lateral · `Ctrl+,` configuración ·
`Ctrl+Shift+Supr` borrar cookies/caché · `Ctrl+Q` salir · clic central = cerrar pestaña ·
arrastrar pestaña = reordenar.

## Progreso por fase

### Fase 1 · Core & Arquitectura
- [x] Estructura de carpetas `nexus_browser/`
- [x] `main.py` ejecutable (ventana + WebView + flags Chromium)
- [x] `core/browser_engine.py` (perfil persistente: cookies+caché en disco / modo privado;
  UA spoofing; accept-language; `clear_browsing_data()`)
- [x] `core/config.py` (carga de settings.json y theme.qss)
- [x] `utils/download_manager.py` (gestor de descargas)
- [x] `utils/session_store.py` (restauración de sesión)
- [ ] Multihilo con `QThread` (acceso a BD aún en hilo de UI)
- [x] `utils/db_manager.py` (SQLite: historial + marcadores) — **sin cifrar todavía**

### Fase 2 · UI/UX & Iconografía
- [x] Interfaz frameless con **barra de título estilo Windows 11** (`ui/components/title_bar.py`:
  `CaptionBar` 32px, icono+título con pixmap de Orbital, botones 46×32 con iconos Lucide, QSizeGrip)
- [x] `ui/components/sidebar_tabs.py` (pestañas verticales, cierre con clic central, drag&drop, iconos Lucide)
- [x] `ui/components/address_bar.py` (Omnibox)
- [x] `ui/components/web_view_pane.py` (vista web + apertura de nuevas pestañas)
- [x] `ui/components/find_bar.py` (buscar en página, Ctrl+F)
- [x] `utils/icon_loader.py` (cargador y renderizador dinámico en memoria de iconos vectoriales Lucide SVG)
- [x] `config/theme.qss` (estilos para pestañas superiores, menú desplegable y panel de descargas)
- [x] Atajos de teclado globales (incl. zoom Ctrl++/-/0 y buscar)
- [x] Barra de progreso de carga
- [x] **Drag-and-drop** para reordenar pestañas (verticales y horizontales)
- [x] **Páginas internas** inicio/historial/marcadores/descargas + nav (`ui/internal_pages.py` con logo Orbital)
- [x] **Páginas de error y crash** en pestañas que fallan
- [x] **Barra lateral ocultable** (Ctrl+B / botón ☰) + zona inferior con accesos
- [x] **Zona de configuración** (`ui/settings_dialog.py`, diálogo nativo para pestañas superiores y descargas en panel)
- [x] **Esquinas redondeadas** nativas (`utils/win_effects.py`, DWM Win11)
- [x] **Pestañas horizontales superiores** opcionales (sincronizadas bidireccionalmente con la barra lateral)
- [x] **Panel lateral derecho de descargas recientes** (`DownloadsPanel`)
- [ ] Redimensionado por todos los bordes (sólo asa inferior-derecha por ahora)

### Fase 3 · Privacidad & Ad-block
- [x] `core/privacy_shield.py` (interceptor + blacklist básica, contador de bloqueos)
- [ ] Carga asíncrona de filtros EasyList/uBlock
- [ ] Aislamiento de almacenamiento por pestaña/perfil

### Fase 4 · Sistema de Extensiones
- [x] Puente `QWebChannel` (`core/bridge.py` `OrbitalBridge`: version/echo/addBookmark, registrado por pestaña)
- [ ] Inyección de `qwebchannel.js` para que `window.orbital` exista en la página
- [ ] Emulación parcial WebExtensions (`chrome.runtime`, `chrome.tabs`)

### Fase 5 · Motor de Búsqueda (OrbitalSearch)
- [x] `core/search_engine.py` / `NexusSearchRouter`
- [x] Autocompletado local (Trie en RAM, `core/trie.py`, alimentado del historial)
- [ ] UI de resultados/respuestas rápidas sobre el Omnibox
- [ ] Meta-query router con anonimización/proxy

### Fase 6 · Distribución Binaria
- [ ] Script de compilación Nuitka
- [ ] Flags de Chromium para rendimiento

## Próximos pasos sugeridos
1. Inyectar `qwebchannel.js` en las páginas para que `window.orbital` sea usable desde JS (Fase 4).
2. UI de respuestas rápidas sobre el Omnibox (Fase 5) y filtros EasyList/uBlock (Fase 3).
3. Mover el acceso a SQLite a un `QThread` dedicado (Fase 1, multihilo).
4. Redimensionado frameless por todos los bordes; empezar script de Nuitka (Fase 6).

## Bloqueos / pendientes de decisión
- Definir librería de cifrado para SQLite (SQLCipher vs. cifrado a nivel de campo) → D-004.
- Python actual es 3.14; PyQt6-WebEngine instaló ruedas `cp310-abi3` (compatibles). OK.
