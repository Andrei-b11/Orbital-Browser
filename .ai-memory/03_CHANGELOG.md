# 03 · Changelog

> Registro cronológico. **Sólo se añade, nunca se borra.** Lo más reciente arriba.
> Formato por entrada: fecha · autor (IA/humano) · qué · por qué · archivos.

---

## 2026-05-30 (9ª iteración) — Antigravity (IA)
**Qué:** Integración total de iconos vectoriales SVG de Lucide (`lucide.dev`).
**Por qué:** Reemplazar todos los iconos, botones y glifos basados en texto o fuentes nativas por SVGs vectoriales de Lucide consistentes y temables.
**Archivos nuevos:**
- `utils/icon_loader.py`: Utilidad para mapear, colorear dinámicamente y renderizar strings SVG inline de Lucide a objetos `QIcon`/`QPixmap` en PyQt6.
**Archivos modificados:**
- `ui/components/title_bar.py`: Modificada la barra de título superior para usar iconos Lucide (`minus`, `square`, `copy`, `x` y `menu`).
- `ui/components/sidebar_tabs.py`: Actualizados botones de añadir pestaña, cerrar pestaña y footer (historial, descargas, configuración) a Lucide.
- `ui/components/downloads_panel.py`: Actualizados el botón de cierre, los iconos de archivo de la lista y el enlace externo del footer a Lucide.
- `ui/main_window.py`: Actualizados botones de navegación (atrás, adelante, recarga), botón de descargas, botón de menú de tres puntos, y botón de añadir pestaña horizontal a Lucide.
**Verificación (offscreen):** Compilación OK en todo el paquete; renderizado vectorial en memoria rápido y offline sin dependencias externas.

---

## 2026-05-30 (8ª iteración) — Antigravity (IA)
**Qué:** Integración de logotipo `orbital_icon.png`, pestañas horizontales superiores y panel lateral de descargas flotante.
**Por qué:** Petición del usuario para usar el logo de Orbital en todos los sitios y habilitar configuración para que las pestañas se muestren horizontales superiores y las descargas en un panel lateral derecho.
**Archivos nuevos:**
- `ui/components/downloads_panel.py`: Creado componente `DownloadsPanel` para descargas recientes con barras de progreso y enlace a historial.
**Archivos modificados:**
- `config/settings.json`: Añadida configuración `"tab_position"` y `"downloads_view"`.
- `config/theme.qss`: Añadidos estilos para `TopTabContainer`, `TopTabBar`, `NavMenu` y `DownloadsPanel`.
- `main.py`: Añadida carga de icono de aplicación desde `assets/orbital_icon.png` a nivel de SO.
- `ui/components/title_bar.py`: Añadido logotipo `orbital_icon.png` en la barra de título superior.
- `ui/internal_pages.py`: Añadida carga del logotipo incrustado en Base64 para la página de inicio `orbital://start`.
- `ui/settings_dialog.py`: Añadidos selectores en la interfaz para elegir disposición de pestañas (lateral/superior) y formato de descargas (panel/pestaña).
- `ui/main_window.py`: Implementado layout de pestañas horizontales, menú desplegable con botón `⋮`, panel de descargas lateral derecho, y lógica de sincronización bidireccional de pestañas y descargas.
**Verificación (offscreen):** Compilación OK en todo el paquete; persistencia y layouts conmutables dinámicamente; sincronización de drag-and-drop.

---

## 2026-05-30 (7ª iteración) — Antigravity (IA)
**Qué:** Renombrado del navegador a "Orbital".
**Por qué:** Petición del usuario (cambio del nombre a Orbital en todos los sitios).
**Archivos modificados:**
- `nexus_browser/config/settings.json`: renombrado app_name, new_tab_url y user_agent.
- `nexus_browser/config/theme.qss`: actualizado comentario del tema.
- `nexus_browser/core/__init__.py`: actualizado docstring.
- `nexus_browser/core/bridge.py`: renombrado NexusBridge -> OrbitalBridge, objeto inyectado nexus -> orbital, versión y eco.
- `nexus_browser/core/browser_engine.py`: renombrado perfil de persistencia nexus -> orbital.
- `nexus_browser/core/search_engine.py`: renombrado NexusSearchRouter -> OrbitalSearchRouter.
- `nexus_browser/main.py`: actualizado nombre e imports.
- `nexus_browser/requirements.txt`: actualizado comentario.
- `nexus_browser/ui/__init__.py`: actualizado docstring.
- `nexus_browser/ui/settings_dialog.py`: actualizados títulos y checkboxes.
- `nexus_browser/ui/main_window.py`: renombrado imports, enrutado de orbital://, base, base de datos (nexus.db -> orbital.db) y canal nativo.
- `nexus_browser/ui/internal_pages.py`: renombrado logo (N -> O), marca, esquema orbital:// y títulos.
- `nexus_browser/ui/components/web_view_pane.py`: renombrado NexusPage -> OrbitalPage y esquema orbital://.
- `nexus_browser/ui/components/sidebar_tabs.py`: renombrado marca lateral de Nexus a Orbital.
- `nexus_browser/data/session.json`: actualizado esquema de pestaña de inicio.
- `plan.md`: actualizado referencias del plan.
- `.ai-memory/README.md`, `.ai-memory/00_PROYECTO.md`, `.ai-memory/01_ARQUITECTURA.md`, `.ai-memory/02_ESTADO_ACTUAL.md`, `.ai-memory/04_DECISIONES.md`: actualizado referencias en los archivos de la zona de memoria.
**Verificación (offscreen):** verificación de coherencia del renombrado; persistencia en orbital.db, puente en window.orbital y esquema orbital://.

---

## 2026-05-30 (6ª iteración) — Claude (IA)
**Qué:** Bordes redondeados, barra lateral ocultable, páginas de error, zonas de
configuración/historial/descargas y página de inicio con navegación interna nexus://.
**Por qué:** Petición del usuario (interfaz, errores en pestañas, zonas y bordes redondeados).
**Archivos nuevos:**
- `utils/win_effects.py`: esquinas redondeadas nativas (DWM, Windows 11) + modo oscuro.
- `ui/settings_dialog.py`: `SettingsDialog` (QDialog) que edita y guarda settings.json.
**Archivos modificados:**
- `ui/components/web_view_pane.py`: `NexusPage` intercepta `nexus://` (acceptNavigationRequest)
  con guard `_suppress` para evitar bucles en `setHtml`; `set_internal_html()`.
- `ui/internal_pages.py`: reescrito con nav entre zonas, `start_page` (logo+buscador+chips),
  `error_page`, `crash_page` y estilos mejorados.
- `ui/components/sidebar_tabs.py`: zona inferior con botones Historial/Descargas/Configuración.
- `ui/components/title_bar.py`: botón hamburguesa (☰) que emite `toggle_sidebar`.
- `ui/main_window.py`: enrutado interno (`_render_internal`/`_route_internal`), páginas de
  error en carga fallida y `renderProcessTerminated` (crash), `toggle_sidebar` (Ctrl+B),
  `open_settings` (Ctrl+,), `showEvent` aplica esquinas redondeadas, new_tab = nexus://start.
- `core/config.py`: `save_settings()`.
- `config/settings.json`: `new_tab_url`. `config/theme.qss`: estilos de CaptionMenu y diálogo.
**Verificación (offscreen):** páginas internas válidas; toggle sidebar oculta/muestra; abrir
zonas crea pestañas; caption con menú; routing nexus:// sin bucles. Compila OK.
**Nota:** El historial en `data/nexus.db` contiene navegación real del usuario (la app ya se usa).
**Decisiones:** D-012 (nexus:// vía NexusPage+guard), D-013 (esquinas redondeadas DWM).

---

## 2026-05-30 (5ª iteración) — Claude (IA)
**Qué:** Drag&drop de pestañas, autocompletado (Trie), páginas internas y puente QWebChannel.
**Por qué:** Continuar con todos los próximos pasos pendientes (Fases 2/4/5).
**Archivos nuevos:**
- `core/trie.py` (Trie de prefijos para autocompletado del Omnibox).
- `core/bridge.py` (`NexusBridge`: objeto QObject con slots version/echo/addBookmark).
- `ui/internal_pages.py` (HTML temado de historial/marcadores/descargas).
**Archivos modificados:**
- `ui/components/sidebar_tabs.py`: **InternalMove** (drag&drop) + cada item guarda su
  WebViewPane en `UserRole`; nuevos `view_at(row)` y `row_of(view)`. Esto elimina la
  necesidad de sincronizar `self.views` con el orden de filas.
- `ui/main_window.py`: refactor de gestión de pestañas para usar `view_at`/`row_of`
  (robusto ante reordenado); `QWebChannel` por pestaña (`_attach_bridge`); `QCompleter`
  + `QStringListModel` alimentados por el Trie (`_setup_completer`/`_update_completions`);
  Trie cargado del historial al inicio y actualizado en cada carga; páginas internas
  (`open_history_page`/`open_bookmarks_page`/`open_downloads_page`) y atajos
  `Ctrl+H`/`Ctrl+J`/`Ctrl+Shift+O`; `closeEvent` guarda sesión en orden del sidebar;
  el historial/Trie ignora URLs `nexus://`.
**Verificación (offscreen):** Trie por prefijo; bridge version/echo; HTML de páginas;
completer actualiza desde Trie; drag manual preserva asociación item↔vista y `row_of`;
webChannel presente en la página; abrir historial añade pestaña.
**Decisiones:** D-010 (asociación item↔vista para drag&drop), D-011 (páginas internas vía setHtml).
**Siguiente paso:** inyectar qwebchannel.js; UI de respuestas sobre el Omnibox; BD en QThread.

---

## 2026-05-30 (4ª iteración) — Claude (IA)
**Qué:** Persistencia y funciones: cookies/caché en disco, descargas, restauración de
sesión, zoom y buscar en página.
**Por qué:** El usuario pidió mejorar funcionamiento, memoria, cookies, etc.
**Archivos nuevos:**
- `utils/download_manager.py` (acepta y supervisa `downloadRequested`).
- `utils/session_store.py` (guarda/restaura pestañas en `data/session.json`).
- `ui/components/find_bar.py` (barra Ctrl+F).
**Archivos modificados:**
- `core/browser_engine.py`: reescrito → perfil **persistente con nombre** (cookies
  AllowPersistentCookies, `DiskHttpCache`, rutas `data/profile` y `data/cache`,
  tamaño de caché) o **off-the-record** si `private_mode`. Añadido `accept_language`
  y `clear_browsing_data()`.
- `ui/main_window.py`: integra DownloadManager, SessionStore, FindBar; `_restore_or_home()`;
  atajos nuevos (Ctrl+F, Ctrl++/-/0 zoom, Ctrl+Shift+Supr borrar datos); guarda sesión
  en `closeEvent`; mensajes de descarga en la barra de estado.
- `config/settings.json`: `private_mode`, `restore_session`, `cache_max_size_mb`,
  `accept_language` (se eliminó `persist_cookies`, ya no usado).
- `config/theme.qss`: estilos de FindBar/FindInput.
**Verificación (offscreen):** perfil no-OTR con cookies persistentes y caché en disco;
session round-trip; carpeta downloads creada; find oculta→visible con Ctrl+F; zoom 1.2 y reset 1.0.
**Decisiones:** D-008 (cookies/caché persistentes; reemplaza D-003 NoPersistentCookies).
**Siguiente paso:** drag&drop de pestañas, página interna historial/descargas, BD en QThread.

---

## 2026-05-30 (3ª iteración) — Claude (IA)
**Qué:** Barra de título estilo Windows 11 (caption bar nativa).
**Por qué:** El usuario pidió que la barra superior se pareciera a la de las apps de Windows.
**Archivos:**
- `ui/components/title_bar.py`: reescrito → `CaptionBar` + `CaptionButton`. Barra a todo
  el ancho (32px) con icono de app + título a la izquierda y botones min/max/cerrar (46×32)
  con glifos de «Segoe Fluent Icons» (E921/E922/E923/E8BB). Arrastre vía startSystemMove,
  doble clic maximiza, `sync_maximize_glyph()` alterna maximizar/restaurar.
- `ui/main_window.py`: layout raíz ahora vertical (caption full-width arriba, luego
  sidebar+contenido). La barra de navegación pasa a `QFrame` simple (ya no arrastra).
  Añadido `changeEvent` (con guard `getattr`) para sincronizar el glifo de maximizar.
- `config/theme.qss`: estilos Win11 (CaptionBar, CaptionIcon, CaptionTitle, botones;
  cerrar con hover rojo #c42b1c). Eliminados los antiguos estilos WinButton.
- `config/settings.json`: sin cambios (sigue `"frameless": true`).
**Verificación:** offscreen → caption 32px, botones 46×32, glifos correctos,
sincronización maximizar/restaurar OK. `compileall` OK.
**Fix:** `changeEvent` se disparaba antes de crear `caption_bar` → protegido con `getattr`.

---

## 2026-05-30 (2ª iteración) — Claude (IA)
**Qué:** Mejoras de UX: frameless, cierre de pestañas, atajos, progreso y marcadores.
**Por qué:** Convertir el esqueleto en un navegador usable de verdad.
**Archivos nuevos:** `ui/components/title_bar.py` (DragBar + botones de ventana).
**Archivos modificados:**
- `ui/components/sidebar_tabs.py`: `TabListWidget` con cierre por clic central.
- `ui/main_window.py`: ventana frameless, controles min/max/cerrar, QSizeGrip,
  atajos de teclado, `close_tab`/`close_current_tab`, barra de progreso de carga,
  marcadores (`bookmark_current`), handlers robustos por identidad de vista.
- `config/settings.json`: añadido `"frameless": true`.
- `config/theme.qss`: estilos de WinButton/WinButtonClose y barra de progreso.
**Atajos:** Ctrl+T/W/L/R/D/Q, F5, Alt+←/→, clic central = cerrar.
**Verificación:** `compileall` OK; test offscreen: abrir 1→3, cerrar fila intermedia 3→2,
cerrar todas regenera home (→1), marcador persistido en BD, cierre limpio.
**Decisiones:** D-007 (frameless con startSystemMove + QSizeGrip).
**Siguiente paso:** drag&drop de pestañas, página de historial/marcadores, BD en QThread.

---

## 2026-05-30 — Claude (IA)
**Qué:** Primera implementación del navegador (esqueleto ejecutable, Fases 1–3 parciales).
**Por qué:** Arrancar el desarrollo del código a partir del plan maestro.
**Archivos creados:**
- `nexus_browser/main.py`, `requirements.txt`
- `config/settings.json`, `config/theme.qss`
- `core/config.py`, `core/browser_engine.py`, `core/privacy_shield.py`, `core/search_engine.py`
- `ui/main_window.py`, `ui/components/{address_bar,web_view_pane,sidebar_tabs}.py`
- `utils/db_manager.py`, `utils/icon_processor.py`
- `__init__.py` en core/ ui/ ui/components/ utils/
**Verificación:** `compileall` OK; instanciación completa en `QT_QPA_PLATFORM=offscreen`
crea ventana, perfil, router, escudo y BD SQLite (tablas history/bookmarks); cierre limpio.
**Decisiones de implementación:**
- Flags de Chromium recortados a los seguros (se omitieron `--enable-low-end-device-mode-v2`
  y `--blink-settings=primaryHoverType=2` del plan por riesgo de inestabilidad).
- Favicons re-coloreados con Qt (QPainter SourceIn) en vez de Pillow, para no exigir
  dependencia extra. Pillow queda como mejora opcional.
- BD SQLite **en texto plano por ahora**; cifrado pospuesto (ver D-004).
**Siguiente paso:** cerrar pestañas, interfaz frameless y mover BD a QThread.

---

## 2026-05-30 — Claude (IA)
**Qué:** Inicialización de la zona de memoria del proyecto.
**Por qué:** El proyecto será grande; se necesita contexto persistente para que cualquier
IA pueda retomar el trabajo sin perder información.
**Archivos creados:**
- `.ai-memory/README.md`
- `.ai-memory/00_PROYECTO.md`
- `.ai-memory/01_ARQUITECTURA.md`
- `.ai-memory/02_ESTADO_ACTUAL.md`
- `.ai-memory/03_CHANGELOG.md`
- `.ai-memory/04_DECISIONES.md`
- `.ai-memory/05_CONVENCIONES.md`

**Estado previo:** El repo sólo contenía `plan.md` (plan maestro de Nexus Browser).

---

<!-- Plantilla para nuevas entradas (copiar arriba):

## AAAA-MM-DD — Autor
**Qué:**
**Por qué:**
**Archivos:**
**Notas / siguiente paso:**

-->
