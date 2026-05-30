# 01 · Arquitectura y Estructura de Archivos

Patrón modular: separar **UI** de la **lógica del motor / red**.

```text
nexus_browser/
│
├── config/
│   ├── settings.json          # Parámetros de inicialización y flags de Chromium
│   └── theme.qss              # Estilos globales (Qt Style Sheets), diseño minimalista
│
├── core/
│   ├── __init__.py
│   ├── browser_engine.py      # Configuración del perfil de QtWebEngine y contextos
│   ├── privacy_shield.py      # Intercepción de peticiones + filtros AdBlock
│   └── search_engine.py       # Enrutamiento y procesamiento de búsquedas
│
├── ui/
│   ├── __init__.py
│   ├── components/
│   │   ├── address_bar.py     # Omnibox (barra de direcciones inteligente)
│   │   ├── sidebar_tabs.py    # Pestañas verticales
│   │   └── web_view_pane.py   # Contenedor del renderizador web
│   └── main_window.py         # Ventana principal y composición de la UI
│
├── utils/
│   ├── __init__.py
│   ├── db_manager.py          # Gestor SQLite cifrado (historial y marcadores)
│   └── icon_processor.py      # Procesado/re-coloreado de favicons (Pillow)
│
└── main.py                    # Punto de entrada y bucle de eventos
```

## Componentes clave (del plan)
- **`PrivacyShield`** (`QWebEngineUrlRequestInterceptor`): bloquea dominios de una blacklist
  (doubleclick, google-analytics, telemetry, scorecardresearch, adnxs…). Fase 3 ampliará
  esto a listas EasyList/uBlock cargadas de forma asíncrona.
- **`OrbitalSearchRouter`**: decide si la entrada del Omnibox es URL o búsqueda; por defecto
  enruta a DuckDuckGo HTML.
- **`MainBrowserWindow`** (`QMainWindow`): perfil Chromium + UI (top bar con back/forward/
  refresh + Omnibox) + tema QSS oscuro mate (acento `#ff6b00`).

## Pipeline de normalización de favicons (Fase 2)
`iconChanged` → extraer `QPixmap` → escala de grises (Pillow) → máscara alpha →
re-coloreado con color del tema → render en pestaña.

## Paleta del tema (QSS)
- Fondo ventana: `#0f0f11` · Top bar: `#16161a` · Borde: `#23232a`/`#2d2d37`
- Input: `#212127`, texto `#e3e3e9` · Acento/focus/selección: `#ff6b00`
