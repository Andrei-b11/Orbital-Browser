# 04 · Decisiones Técnicas (ADR ligero)

> Cada decisión de diseño con su justificación. No contradigas una decisión sin anotar
> aquí la nueva y marcar la anterior como "Reemplazada".

---

## D-001 · Stack base: PyQt6 + QtWebEngine
- **Decisión:** Construir el navegador sobre PyQt6 con QtWebEngine (Chromium embebido).
- **Por qué:** Permite reutilizar el motor Chromium completo (renderizado, red,
  interceptores) con UI nativa en Python. Definido en el plan maestro.
- **Estado:** Vigente.

## D-002 · Motor de búsqueda por defecto: DuckDuckGo HTML
- **Decisión:** El `OrbitalSearchRouter` enruta búsquedas a `https://html.duckduckgo.com/html/?q=`.
- **Por qué:** Privacidad por defecto; sin JS pesado. Provisional hasta tener OrbitalSearch propio (Fase 5).
- **Estado:** Vigente (provisional).

## D-003 · Privacidad: interceptor nativo + NoPersistentCookies
- **Decisión:** Bloquear dominios vía `QWebEngineUrlRequestInterceptor`; política de cookies
  no persistentes; spoofing de User-Agent.
- **Por qué:** Reducir rastreo/fingerprinting sin depender de extensiones externas.
- **Estado:** Parcialmente **reemplazada por D-008** (la parte de cookies). El interceptor
  y el UA spoofing siguen vigentes.

---

## D-004 · Cifrado de SQLite pospuesto
- **Decisión:** El historial/marcadores se guardan en SQLite **en texto plano** en esta etapa.
- **Por qué:** Priorizar un navegador funcional; el cifrado (SQLCipher vs. cifrado por campo)
  se decidirá e implementará antes de la distribución (Fase 6).
- **Estado:** Vigente (provisional). Pendiente de elegir mecanismo.

## D-005 · Re-coloreado de favicons con Qt en vez de Pillow
- **Decisión:** `utils/icon_processor.py` usa `QPainter` (SourceIn) para teñir favicons.
- **Por qué:** Evita exigir Pillow como dependencia obligatoria; el resultado monocromo
  coherente es suficiente para la estética Zen. Pillow queda como modo opcional de más calidad.
- **Estado:** Vigente.

## D-006 · Flags de Chromium recortados a los seguros
- **Decisión:** Sólo se inyectan `--disable-gpu-shader-disk-cache` y `--enable-parallel-downloading`.
- **Por qué:** Los flags `--enable-low-end-device-mode-v2` y `--blink-settings=primaryHoverType=2`
  del plan son inestables/no estándar y podían degradar el renderizado.
- **Estado:** Vigente. Revisable en Fase 6 (optimización).

## D-007 · Frameless con startSystemMove + QSizeGrip
- **Decisión:** Ventana sin bordes (`FramelessWindowHint`). El movimiento se delega al SO
  con `QWindow.startSystemMove()` desde la barra superior (`DragBar`); el redimensionado
  usa un `QSizeGrip` (esquina inferior-derecha) por ahora. Controlado por `settings.frameless`.
- **Por qué:** `startSystemMove` es robusto en Windows y evita gestionar manualmente el arrastre.
- **Estado:** Vigente. Pendiente: redimensionado por todos los bordes (TODO en estado actual).

## D-008 · Persistencia: cookies y caché en disco (con modo privado)
- **Decisión:** En modo normal se usa un perfil **con nombre** (`"orbital"`) que guarda cookies
  (`AllowPersistentCookies`) y caché HTTP en disco bajo `data/profile` y `data/cache`.
  `settings.private_mode = true` cambia a un perfil off-the-record (todo en memoria).
- **Por qué:** El usuario quiere que las sesiones/logins se recuerden entre ejecuciones;
  el modo privado se conserva como opción. Se ofrece `Ctrl+Shift+Supr` para borrar datos.
- **Estado:** Vigente. Reemplaza la política de cookies de D-003.

## D-009 · Restauración de sesión vía JSON
- **Decisión:** Las pestañas abiertas se guardan en `data/session.json` al cerrar y se
  restauran al abrir si `settings.restore_session`.
- **Por qué:** Recuperar el espacio de trabajo; simple y suficiente (no requiere BD).
- **Estado:** Vigente.

## D-010 · Pestañas: asociación item↔vista (UserRole)
- **Decisión:** Cada `QListWidgetItem` del sidebar guarda su `WebViewPane` en `UserRole`.
  El mapeo fila→vista se deriva siempre de los items (`view_at`/`row_of`), no de un índice
  paralelo en `self.views`.
- **Por qué:** Permite drag&drop (`InternalMove`) sin sincronizar listas: al mover el item
  se mueve su asociación. `self.views` queda sólo para iteración y mantener vivas las refs.
- **Estado:** Vigente.

## D-011 · Páginas internas vía setHtml (no esquema orbital://)
- **Decisión:** Historial/marcadores/descargas se renderizan generando HTML temado y
  cargándolo con `view.setHtml(html, QUrl("orbital://<label>"))`.
- **Por qué:** Rápido y sin registrar un `QWebEngineUrlSchemeHandler`. El esquema real
  `orbital://` queda como mejora futura si se necesita navegación/recarga nativa.
- **Estado:** Vigente (provisional).

## D-012 · Navegación interna orbital:// vía OrbitalPage + guard
- **Decisión:** `OrbitalPage.acceptNavigationRequest` intercepta esquema `orbital://` y emite
  `internal_requested`; las zonas se renderizan con `setHtml` usando una bandera `_suppress`
  (reseteada con `QTimer.singleShot(0)`) para no re-interceptar su propia carga.
- **Por qué:** Permite enlaces internos entre zonas (inicio/historial/...) sin registrar un
  `QWebEngineUrlSchemeHandler`, evitando bucles infinitos al usar base orbital://.
- **Estado:** Vigente. Sustituye el enfoque ad-hoc de D-011 (setHtml directo).

## D-013 · Esquinas redondeadas con DWM (Windows 11)
- **Decisión:** `utils/win_effects.py` llama a `DwmSetWindowAttribute`
  (`DWMWA_WINDOW_CORNER_PREFERENCE = DWMWCP_ROUND`) sobre el HWND en `showEvent`.
- **Por qué:** Bordes redondeados nativos con sombra real, sin máscaras dentadas. Falla en
  silencio fuera de Windows 11.
- **Estado:** Vigente.

---

<!-- Plantilla:
## D-00X · Título
- **Decisión:**
- **Por qué:**
- **Estado:** Vigente / Reemplazada por D-00Y
-->
