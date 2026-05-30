"""Ventana principal y composición de la interfaz (Fase 1 + 2).

Orquesta el perfil de Chromium, el escudo de privacidad, el enrutador de
búsqueda, la persistencia SQLite y la UI (sidebar de pestañas + Omnibox +
área de renderizado), con ventana sin bordes, atajos de teclado, cierre de
pestañas e indicador de progreso de carga.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QStringListModel, QUrl, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineLoadingInfo
from PyQt6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QTabBar,
    QMenu,
)

from core.bridge import OrbitalBridge
from core.browser_engine import clear_browsing_data, configure_profile
from core.config import DATA_DIR, load_settings
from core.search_engine import OrbitalSearchRouter
from core.trie import Trie
from ui import internal_pages
from ui.components.address_bar import AddressBar
from ui.components.find_bar import FindBar
from ui.components.sidebar_tabs import Sidebar, TabItemWidget
from ui.components.downloads_panel import DownloadsPanel
from ui.components.title_bar import CaptionBar
from ui.components.web_view_pane import WebViewPane
from ui.settings_dialog import SettingsDialog
from utils.db_manager import DBManager
from utils.download_manager import DownloadManager
from utils.icon_processor import tint_icon
from utils.icon_loader import get_lucide_icon
from utils.session_store import SessionStore
from utils.win_effects import apply_rounded_corners

ZOOM_STEP = 0.1
ZOOM_MIN = 0.25
ZOOM_MAX = 5.0


class TopTabCloseButton(QPushButton):
    """Botón de cierre personalizado que renderiza un aspa SVG de Lucide nítida.
    
    Usa el motor QSvgRenderer en memoria para evitar problemas de carga de archivos en QSS.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopTabCloseButton")
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._update_icon(False)

    def _update_icon(self, hovered: bool) -> None:
        color = "#ffffff" if hovered else "#9696a0"
        self.setIcon(get_lucide_icon("x", color=color, size=10))

    def enterEvent(self, event) -> None:
        self._update_icon(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._update_icon(False)
        super().leaveEvent(event)


class MainBrowserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.profile, self.privacy_shield = configure_profile(self.settings)
        self.router = OrbitalSearchRouter(self.settings["search_endpoint"])
        self.db = DBManager(str(DATA_DIR / "orbital.db"))
        self.downloads = DownloadManager(self.profile, str(DATA_DIR / "downloads"))
        self.session = SessionStore(str(DATA_DIR / "session.json"))

        # Puente nativo JS↔Python (Fase 4) compartido por todas las pestañas.
        self.bridge = OrbitalBridge(db=self.db)

        # Trie de autocompletado (Fase 5) alimentado con el historial.
        self.trie = Trie()
        self.views: list[WebViewPane] = []

        if self.settings.get("frameless", False):
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._build_ui()
        self._install_shortcuts()
        self._wire_downloads()
        self._apply_tab_layout()
        
        # Deferir la carga del historial y la restauración de sesión para que la interfaz se muestre de inmediato
        QTimer.singleShot(0, self._deferred_init)

    def _deferred_init(self) -> None:
        self._load_trie_from_history()
        self._restore_or_home()
        # Enfocar el Omnibox (barra de direcciones) al iniciar para permitir escribir de inmediato sin esperar la carga web
        self.omnibox.setFocus()
        self.omnibox.selectAll()

    def _load_trie_from_history(self) -> None:
        for record in self.db.recent_history(limit=500):
            self.trie.insert(record["url"])

    def _restore_or_home(self) -> None:
        """Restaura la sesión anterior o abre la página de inicio."""
        if self.settings.get("restore_session", False):
            urls, active = self.session.load()
            if urls:
                for url in urls:
                    self.add_new_tab(QUrl(url))
                self.sidebar.set_current_row(active)
                return
        
        # Si no restauramos la sesión, abrir la página de inicio del motor de búsqueda actual
        engine_home = self._get_current_search_engine_home()
        self.add_new_tab(QUrl(engine_home))

    def _get_current_search_engine_home(self) -> str:
        """Devuelve la página de inicio asociada al motor de búsqueda actual."""
        endpoint = self.settings.get("search_endpoint", "")
        if "google.com" in endpoint:
            return "https://www.google.com"
        elif "duckduckgo.com" in endpoint:
            return "https://duckduckgo.com"
        elif "bing.com" in endpoint:
            return "https://www.bing.com"
        elif "ecosia.org" in endpoint:
            return "https://www.ecosia.org"
        
        # Si es personalizado, extraer el esquema y dominio base
        qurl = QUrl(endpoint)
        if qurl.isValid() and qurl.host():
            scheme = qurl.scheme() or "https"
            return f"{scheme}://{qurl.host()}"
        
        return self.settings.get("home_url", "https://www.google.com")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.setWindowTitle(self.settings.get("app_name", "Orbital"))
        win = self.settings.get("window", {})
        self.resize(win.get("width", 1280), win.get("height", 800))

        central = QWidget()
        central.setObjectName("CentralContainer")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Barra de título estilo Windows (a todo el ancho, sólo frameless) ---
        self.caption_bar = None
        if self.settings.get("frameless", False):
            self.caption_bar = CaptionBar(self.settings.get("app_name", "Orbital"))
            self.caption_bar.toggle_sidebar.connect(self.toggle_sidebar)
            root.addWidget(self.caption_bar)

        # --- Cuerpo: sidebar (izquierda) + contenido (derecha) ---
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.new_tab_requested.connect(self.open_home_tab)
        self.sidebar.tab_selected.connect(self._on_tab_selected)
        self.sidebar.close_tab_requested.connect(self.close_tab)
        self.sidebar.history_requested.connect(self.open_history_page)
        self.sidebar.downloads_requested.connect(self.open_downloads_page)
        self.sidebar.settings_requested.connect(self.open_settings)
        self.sidebar.tab_list.model().rowsMoved.connect(self._on_sidebar_rows_moved)
        body.addWidget(self.sidebar)

        # --- Columna derecha: barra de navegación + área web ---
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # --- Barra de pestañas horizontal superior (para modo horizontal) ---
        self.top_tab_container = QWidget()
        self.top_tab_container.setObjectName("TopTabContainer")
        top_tab_layout = QHBoxLayout(self.top_tab_container)
        top_tab_layout.setContentsMargins(8, 2, 8, 2)
        top_tab_layout.setSpacing(6)

        self.top_tab_bar = QTabBar()
        self.top_tab_bar.setObjectName("TopTabBar")
        self.top_tab_bar.setTabsClosable(False)  # Usamos botones de cierre personalizados
        self.top_tab_bar.setMovable(True)
        self.top_tab_bar.setDrawBase(False)
        self.top_tab_bar.currentChanged.connect(self._on_top_tab_changed)
        self.top_tab_bar.tabMoved.connect(self._on_top_tab_moved)

        self.add_tab_btn = QPushButton()
        self.add_tab_btn.setIcon(get_lucide_icon("plus", color="#9696a0", size=14))
        self.add_tab_btn.setObjectName("TopTabAddButton")
        self.add_tab_btn.setFixedSize(24, 24)
        self.add_tab_btn.setToolTip("Nueva pestaña")
        self.add_tab_btn.clicked.connect(self.open_home_tab)

        top_tab_layout.addWidget(self.top_tab_bar)
        top_tab_layout.addWidget(self.add_tab_btn)
        top_tab_layout.addStretch()

        right.addWidget(self.top_tab_container)
        right.addWidget(self._build_top_bar())

        self.stack = QStackedWidget()
        right.addWidget(self.stack)

        # Barra "buscar en la página" (Ctrl+F), oculta por defecto.
        self.find_bar = FindBar()
        self.find_bar.search.connect(self._find_text)
        self.find_bar.find_next.connect(lambda: self._find_again(False))
        self.find_bar.find_prev.connect(lambda: self._find_again(True))
        self.find_bar.closed.connect(lambda: self._with_view(lambda v: v.findText("")))
        right.addWidget(self.find_bar)

        # Barra de progreso fina bajo la barra de direcciones.
        self.progress = QProgressBar()
        self.progress.setObjectName("LoadProgress")
        self.progress.setMaximumHeight(2)
        self.progress.setTextVisible(False)
        self.progress.hide()
        right.addWidget(self.progress)

        right_container = QWidget()
        right_container.setLayout(right)
        body.addWidget(right_container, 1)

        # --- Panel flotante de descargas (flota sobre la ventana principal) ---
        self.downloads_panel = DownloadsPanel(self.downloads, self)
        self.downloads_panel.open_full_downloads.connect(self.open_downloads_page)
        self.downloads_panel.hide()

        root.addLayout(body)

        # Ocultar la barra de estado inferior negra
        self.statusBar().hide()

        # Añadir un asa de redimensionado (SizeGrip) flotante transparente en la esquina inferior derecha
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setFixedSize(16, 16)
        self.sizegrip.setStyleSheet("background: transparent;")
        self.sizegrip.raise_()

    def _build_top_bar(self) -> QFrame:
        # Barra de herramientas de navegación (no arrastra la ventana).
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.back_button = self._nav_button("", "Atrás")
        self.back_button.setIcon(get_lucide_icon("chevron-left", color="#9696a0", size=16))
        self.forward_button = self._nav_button("", "Adelante")
        self.forward_button.setIcon(get_lucide_icon("chevron-right", color="#9696a0", size=16))
        self.refresh_button = self._nav_button("", "Recargar")
        self.refresh_button.setIcon(get_lucide_icon("rotate-cw", color="#9696a0", size=14))

        self.omnibox = AddressBar()
        self.omnibox.returnPressed.connect(self._navigate)
        self._setup_completer()

        self.back_button.clicked.connect(lambda: self._with_view(lambda v: v.back()))
        self.forward_button.clicked.connect(lambda: self._with_view(lambda v: v.forward()))
        self.refresh_button.clicked.connect(lambda: self._with_view(lambda v: v.reload()))

        # Botón de Descargas (abre el panel lateral)
        self.dl_nav_btn = self._nav_button("", "Descargas recientes")
        self.dl_nav_btn.setIcon(get_lucide_icon("download", color="#9696a0", size=15))
        self.dl_nav_btn.clicked.connect(self._toggle_downloads_panel)

        # Botón de Menú (menú desplegable clásico)
        self.menu_nav_btn = self._nav_button("", "Menú")
        self.menu_nav_btn.setIcon(get_lucide_icon("more-vertical", color="#9696a0", size=16))
        self._setup_nav_menu()

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.omnibox)
        layout.addWidget(self.dl_nav_btn)
        layout.addWidget(self.menu_nav_btn)
        return bar

    def _nav_button(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setFixedSize(28, 28)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setToolTip(tooltip)
        return btn

    def changeEvent(self, event) -> None:
        # Mantener el glifo maximizar/restaurar sincronizado con el estado real.
        # (puede dispararse durante la construcción, antes de crear la barra)
        caption_bar = getattr(self, "caption_bar", None)
        if caption_bar is not None:
            caption_bar.sync_maximize_glyph()
        super().changeEvent(event)

    # ------------------------------------------------------------- Atajos
    def _install_shortcuts(self) -> None:
        mapping = {
            "Ctrl+T": self.open_home_tab,
            "Ctrl+W": self.close_current_tab,
            "Ctrl+L": self._focus_omnibox,
            "Ctrl+R": lambda: self._with_view(lambda v: v.reload()),
            "F5": lambda: self._with_view(lambda v: v.reload()),
            "Alt+Left": lambda: self._with_view(lambda v: v.back()),
            "Alt+Right": lambda: self._with_view(lambda v: v.forward()),
            "Ctrl+D": self.bookmark_current,
            "Ctrl+H": self.open_history_page,
            "Ctrl+J": self.open_downloads_page,
            "Ctrl+Shift+O": self.open_bookmarks_page,
            "Ctrl+B": self.toggle_sidebar,
            "Ctrl+,": self.open_settings,
            "Ctrl+F": self._open_find,
            "Ctrl++": lambda: self._zoom(ZOOM_STEP),
            "Ctrl+=": lambda: self._zoom(ZOOM_STEP),
            "Ctrl+-": lambda: self._zoom(-ZOOM_STEP),
            "Ctrl+0": self._zoom_reset,
            "Ctrl+Shift+Delete": self._clear_browsing_data,
            "Ctrl+Q": self.close,
        }
        for keys, slot in mapping.items():
            QShortcut(QKeySequence(keys), self, activated=slot)

    def _focus_omnibox(self) -> None:
        self.omnibox.setFocus()
        self.omnibox.selectAll()

    # ------------------------------------------------------- Autocompletado
    def _setup_completer(self) -> None:
        self._completer_model = QStringListModel(self)
        completer = QCompleter(self._completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.omnibox.setCompleter(completer)
        self.omnibox.textEdited.connect(self._update_completions)

    def _update_completions(self, text: str) -> None:
        self._completer_model.setStringList(self.trie.starts_with(text, limit=8))

    # ----------------------------------------------------------- Descargas
    def _wire_downloads(self) -> None:
        self.downloads.started.connect(self._on_download_started)
        self.downloads.progress.connect(self._on_download_progress)
        self.downloads.finished.connect(self._on_download_finished)

    def _on_download_progress(self, name: str, percent: int) -> None:
        if percent >= 0:
            self.statusBar().showMessage(f"⬇ {name} — {percent}%")

    def _on_download_finished(self, name: str, ok: bool) -> None:
        estado = "completada" if ok else "fallida"
        self.statusBar().showMessage(f"⬇ Descarga {estado}: {name}", 5000)

    # --------------------------------------------------------- Buscar/Zoom
    def _open_find(self) -> None:
        self.find_bar.activate()

    def _find_text(self, text: str) -> None:
        self._with_view(lambda v: v.findText(text))

    def _find_again(self, backward: bool) -> None:
        text = self.find_bar.input.text()
        flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
        self._with_view(lambda v: v.findText(text, flags))

    def _zoom(self, delta: float) -> None:
        view = self._current_view()
        if view is not None:
            factor = max(ZOOM_MIN, min(ZOOM_MAX, view.zoomFactor() + delta))
            view.setZoomFactor(factor)
            self.statusBar().showMessage(f"Zoom: {int(factor * 100)}%", 1500)

    def _zoom_reset(self) -> None:
        view = self._current_view()
        if view is not None:
            view.setZoomFactor(1.0)
            self.statusBar().showMessage("Zoom: 100%", 1500)

    def _clear_browsing_data(self) -> None:
        clear_browsing_data(self.profile)
        self.privacy_shield.blocked_count = 0
        self.statusBar().showMessage("🧹 Cookies y caché borradas", 4000)

    # --------------------------------------------------------------- Tabs
    def open_home_tab(self) -> WebViewPane:
        return self.add_new_tab(QUrl(self.settings.get("new_tab_url", "orbital://start")))

    def add_new_tab(self, url: QUrl) -> WebViewPane:
        view = WebViewPane(self.profile, new_tab_factory=self.open_home_tab)
        self.views.append(view)
        self.stack.addWidget(view)
        self._attach_bridge(view)
        row = self.sidebar.add_tab_item(view, "Cargando…")
        
        # Obtener y establecer el icono por defecto inicial para esta pestaña
        initial_icon = self._get_default_tab_icon(url.toString())
        self.sidebar.set_tab_icon(row, initial_icon)

        # Añadir y sincronizar la barra de pestañas superior
        self.top_tab_bar.blockSignals(True)
        idx = self.top_tab_bar.addTab(initial_icon, "Cargando…")
        self._add_custom_close_button(idx)
        self.top_tab_bar.setCurrentIndex(idx)
        self.top_tab_bar.blockSignals(False)

        # Señales por pestaña (capturamos la vista concreta en el lambda).
        view.urlChanged.connect(lambda qurl, v=view: self._on_url_changed(v, qurl))
        view.titleChanged.connect(lambda title, v=view: self._on_title_changed(v, title))
        view.iconChanged.connect(lambda _icon, v=view: self._on_icon_changed(v))
        view.loadStarted.connect(lambda v=view: self._on_load_progress(v, 0))
        view.loadProgress.connect(lambda p, v=view: self._on_load_progress(v, p))
        view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(v, ok))
        view.page().loadingChanged.connect(lambda info, v=view: self._on_loading_changed(v, info))
        view.page().internal_requested.connect(lambda u, v=view: self._render_internal(v, u))
        view.renderProcessTerminated.connect(lambda *_: self._on_render_crash(view))

        self.stack.setCurrentWidget(view)
        self.sidebar.set_current_row(row)

        # Las URLs internas (orbital://) se renderizan localmente; el resto se cargan.
        if url.scheme() == "orbital":
            self._render_internal(view, url)
        else:
            view.setUrl(url)
        return view

    # --------------------------------------------------------- Páginas internas
    def _render_internal(self, view: WebViewPane, url: QUrl) -> None:
        """Renderiza una zona interna (orbital://…) dentro de la vista dada."""
        zone = url.host() or url.path().strip("/") or "start"
        base = QUrl(f"orbital://{zone}")
        if zone == "start":
            view.set_internal_html(self._start_html(), base)
        elif zone == "history":
            view.set_internal_html(internal_pages.history_page(self.db.recent_history(200)), base)
        elif zone == "bookmarks":
            view.set_internal_html(internal_pages.bookmarks_page(self.db.list_bookmarks()), base)
        elif zone == "downloads":
            view.set_internal_html(internal_pages.downloads_page(self.downloads.items), base)
        elif zone == "settings":
            self.open_settings()
        else:
            view.set_internal_html(self._start_html(), QUrl("orbital://start"))

    def _start_html(self) -> str:
        action = self.settings["search_endpoint"].split("?")[0]
        quick = [(r["url"], r["title"]) for r in self.db.recent_history(6)]
        return internal_pages.start_page(action, "q", quick)

    def open_history_page(self) -> None:
        self.add_new_tab(QUrl("orbital://history"))

    def open_bookmarks_page(self) -> None:
        self.add_new_tab(QUrl("orbital://bookmarks"))

    def open_downloads_page(self) -> None:
        self.add_new_tab(QUrl("orbital://downloads"))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = load_settings()
            self._apply_tab_layout()
            self.statusBar().showMessage(
                "⚙ Configuración guardada (algunos cambios requieren reiniciar)", 5000
            )

    def _attach_bridge(self, view: WebViewPane) -> None:
        """Registra el objeto nativo `orbital` en el canal de la página (Fase 4)."""
        channel = QWebChannel(view.page())
        channel.registerObject("orbital", self.bridge)
        view.page().setWebChannel(channel)

    def _on_tab_selected(self, row: int) -> None:
        view = self.sidebar.view_at(row)
        if isinstance(view, WebViewPane):
            self.stack.setCurrentWidget(view)
            self.omnibox.setText(view.url().toString())
            
            # Sincronizar la barra de pestañas superior
            self.top_tab_bar.blockSignals(True)
            self.top_tab_bar.setCurrentIndex(row)
            self.top_tab_bar.blockSignals(False)

    def close_current_tab(self) -> None:
        self.close_tab(self.sidebar.current_row())

    def close_tab(self, row: int) -> None:
        view = self.sidebar.view_at(row)
        if not isinstance(view, WebViewPane):
            return
        if view in self.views:
            self.views.remove(view)
        self.stack.removeWidget(view)
        view.deleteLater()
        
        # Eliminar de la barra lateral y superior
        self.sidebar.remove_tab_item(row)
        
        self.top_tab_bar.blockSignals(True)
        self.top_tab_bar.removeTab(row)
        self.top_tab_bar.blockSignals(False)

        if self.sidebar.count() == 0:
            self.open_home_tab()
        else:
            new_row = min(row, self.sidebar.count() - 1)
            self.sidebar.set_current_row(new_row)
            
            self.top_tab_bar.blockSignals(True)
            self.top_tab_bar.setCurrentIndex(new_row)
            self.top_tab_bar.blockSignals(False)

    # ------------------------------------------------------- Señales web
    def _on_url_changed(self, view: WebViewPane, qurl: QUrl) -> None:
        if view is self._current_view():
            self.omnibox.setText(qurl.toString())
            self.omnibox.clearFocus()
            
        # Si la URL cambia a un esquema orbital://, forzar de inmediato el logo de la app
        if qurl.scheme() == "orbital":
            row = self.sidebar.row_of(view)
            if row >= 0:
                icon = self._get_default_tab_icon(qurl.toString())
                self.sidebar.set_tab_icon(row, icon)
                self.top_tab_bar.setTabIcon(row, icon)

    def _on_title_changed(self, view: WebViewPane, title: str) -> None:
        row = self.sidebar.row_of(view)
        if row >= 0:
            self.sidebar.set_tab_title(row, title)
            self.top_tab_bar.setTabText(row, title)

    def _on_icon_changed(self, view: WebViewPane) -> None:
        row = self.sidebar.row_of(view)
        if row < 0:
            return
        icon = view.icon()
        if icon.isNull():
            icon = self._get_default_tab_icon(view.url().toString())
        elif self.settings.get("tint_favicons", False):
            icon = tint_icon(icon, self.settings.get("favicon_tint_color", "#c8c8d0"))
        self.sidebar.set_tab_icon(row, icon)
        self.top_tab_bar.setTabIcon(row, icon)

    def _on_load_progress(self, view: WebViewPane, percent: int) -> None:
        if view is not self._current_view():
            return
        if 0 < percent < 100:
            self.progress.setValue(percent)
            self.progress.show()
        else:
            self.progress.hide()

    def _on_load_finished(self, view: WebViewPane, ok: bool) -> None:
        if view is self._current_view():
            self.progress.hide()
        url = view.url().toString()
        if ok:
            if not url.startswith(("orbital://", "data:")):
                self.db.add_history(url, view.title())
                self.trie.insert(url)  # nuevas visitas alimentan el autocompletado
            self.statusBar().showMessage(
                f"Listo · Peticiones bloqueadas: {self.privacy_shield.blocked_count}"
            )

    def _on_loading_changed(self, view: WebViewPane, info: QWebEngineLoadingInfo) -> None:
        if info.status() == QWebEngineLoadingInfo.LoadStatus.LoadFailedStatus:
            # Ignorar cancelaciones (ERR_ABORTED -3) como el inicio de descargas o redirecciones de descarga
            if info.errorCode() == -3:
                return
            
            url = info.url().toString()
            if url.startswith(("http://", "https://")):
                view.set_internal_html(internal_pages.error_page(url), QUrl("orbital://error"))
                row = self.sidebar.row_of(view)
                if row >= 0:
                    self.sidebar.set_tab_title(row, "Error de carga")

    def _on_render_crash(self, view: WebViewPane) -> None:
        url = view.url().toString()
        view.set_internal_html(internal_pages.crash_page(url), QUrl("orbital://crash"))
        row = self.sidebar.row_of(view)
        if row >= 0:
            self.sidebar.set_tab_title(row, "Pestaña interrumpida")

    # --------------------------------------------------------- Navegación
    def _navigate(self) -> None:
        url = self.router.resolve(self.omnibox.text())
        if url is not None:
            self._with_view(lambda v: v.setUrl(url))

    def bookmark_current(self) -> None:
        view = self._current_view()
        if view is not None:
            self.db.add_bookmark(view.url().toString(), view.title())
            self.statusBar().showMessage("★ Marcador guardado", 3000)

    def _current_view(self) -> WebViewPane | None:
        widget = self.stack.currentWidget()
        return widget if isinstance(widget, WebViewPane) else None

    def _with_view(self, action) -> None:
        view = self._current_view()
        if view is not None:
            action(view)

    # ------------------------------------------------------ Barra lateral
    def toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    # -------------------------------------------------- Sincronización y Layouts
    def _apply_tab_layout(self) -> None:
        position = self.settings.get("tab_position", "left")
        is_frameless = self.settings.get("frameless", False)

        if position == "top" and is_frameless and self.caption_bar:
            # Integrar pestañas en la barra de título superior
            self.caption_bar.tabs_layout.insertWidget(0, self.top_tab_bar)
            self.caption_bar.tabs_layout.insertWidget(1, self.add_tab_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            
            self.caption_bar.tabs_container.show()
            self.caption_bar.title_label.hide()
            self.top_tab_container.hide()
            self.sidebar.hide()
        elif position == "top":
            # Pestañas horizontales normales (barra separada)
            self.top_tab_container.layout().insertWidget(0, self.top_tab_bar)
            self.top_tab_container.layout().insertWidget(1, self.add_tab_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            
            self.top_tab_container.show()
            if self.caption_bar:
                self.caption_bar.tabs_container.hide()
                self.caption_bar.title_label.show()
            self.sidebar.hide()
        else:
            # Pestañas verticales en la barra lateral
            if self.caption_bar:
                self.caption_bar.tabs_container.hide()
                self.caption_bar.title_label.show()
            self.top_tab_container.hide()
            self.sidebar.show()

    def _on_top_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self.views):
            self.sidebar.tab_list.blockSignals(True)
            self.sidebar.set_current_row(index)
            self.sidebar.tab_list.blockSignals(False)
            
            view = self.views[index]
            self.stack.setCurrentWidget(view)
            self.omnibox.setText(view.url().toString())

    def _on_top_tab_close_requested(self, index: int) -> None:
        self.close_tab(index)

    def _on_top_tab_moved(self, from_idx: int, to_idx: int) -> None:
        if from_idx == to_idx:
            return
        # Reordenar views
        view = self.views.pop(from_idx)
        self.views.insert(to_idx, view)

        # Reordenar sidebar
        self.sidebar.tab_list.blockSignals(True)
        item = self.sidebar.tab_list.takeItem(from_idx)
        self.sidebar.tab_list.insertItem(to_idx, item)
        
        # Obtener título e icono actuales de la barra superior
        title = self.top_tab_bar.tabText(to_idx)
        icon = self.top_tab_bar.tabIcon(to_idx)
        
        # Recrear widget
        widget = TabItemWidget(view, title)
        widget.close_clicked.connect(self.sidebar._on_close_clicked)
        if icon:
            widget.set_icon(icon)
        self.sidebar.tab_list.setItemWidget(item, widget)
        self.sidebar.tab_list.blockSignals(False)

    def _on_sidebar_rows_moved(self, parent, start: int, end: int, destination, dest_row: int) -> None:
        self.top_tab_bar.blockSignals(True)
        new_views = []
        new_tabs = []
        for row in range(self.sidebar.count()):
            view = self.sidebar.view_at(row)
            new_views.append(view)
            
            widget = self.sidebar._widget_at(row)
            title = widget.title_label._full if widget else "Pestaña"
            pixmap = widget.icon_label.pixmap() if widget else None
            if pixmap and not pixmap.isNull():
                qicon = QIcon(pixmap)
            else:
                qicon = self._get_default_tab_icon(view.url().toString())
            new_tabs.append((title, qicon))
            
        self.views = new_views
        self.top_tab_bar.clear()
        for title, qicon in new_tabs:
            idx = self.top_tab_bar.addTab(qicon, title)
            self._add_custom_close_button(idx)
            
        self.top_tab_bar.setCurrentIndex(self.sidebar.current_row())
        self.top_tab_bar.blockSignals(False)

    def _show_downloads_panel(self) -> None:
        # Calcular posición global justo debajo del botón de descargas
        btn_pos = self.dl_nav_btn.mapToGlobal(self.dl_nav_btn.rect().bottomLeft())
        # Alinear borde derecho del panel con el del botón
        x = btn_pos.x() + self.dl_nav_btn.width() - self.downloads_panel.width()
        y = btn_pos.y() + 4  # Margen de 4px
        x = max(10, x)  # Evitar que se salga de la pantalla por la izquierda
        self.downloads_panel.move(x, y)
        self.downloads_panel.show()
        self.downloads_panel.refresh()
        self.downloads_panel.raise_()
        self.downloads_panel.activateWindow()

    def _toggle_downloads_panel(self) -> None:
        if self.downloads_panel.isVisible():
            self.downloads_panel.hide()
        else:
            self._show_downloads_panel()

    def _on_download_started(self, name: str) -> None:
        self.statusBar().showMessage(f"⬇ Descargando {name}…")
        if self.settings.get("downloads_view", "panel") == "panel":
            self._show_downloads_panel()

    def _setup_nav_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("NavMenu")
        
        act_new_tab = menu.addAction("Nueva pestaña")
        act_new_tab.setShortcut("Ctrl+T")
        act_new_tab.triggered.connect(self.open_home_tab)
        
        menu.addSeparator()
        
        act_history = menu.addAction("Historial")
        act_history.setShortcut("Ctrl+H")
        act_history.triggered.connect(self.open_history_page)
        
        act_bookmarks = menu.addAction("Marcadores")
        act_bookmarks.setShortcut("Ctrl+Shift+O")
        act_bookmarks.triggered.connect(self.open_bookmarks_page)
        
        act_downloads = menu.addAction("Descargas")
        act_downloads.setShortcut("Ctrl+J")
        act_downloads.triggered.connect(self.open_downloads_page)
        
        menu.addSeparator()
        
        act_settings = menu.addAction("Configuración")
        act_settings.setShortcut("Ctrl+,")
        act_settings.triggered.connect(self.open_settings)
        
        menu.addSeparator()
        
        act_exit = menu.addAction("Salir")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        
        self.menu_nav_btn.setMenu(menu)

    # ---------------------------------------------------- Efectos ventana
    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Esquinas redondeadas nativas (Windows 11); sólo una vez, ya con winId válido.
        if not getattr(self, "_corners_done", False):
            apply_rounded_corners(int(self.winId()))
            self._corners_done = True

    def _add_custom_close_button(self, index: int) -> None:
        # Crear un contenedor transparente que actúe como buffer de posicionamiento
        container = QWidget()
        container.setObjectName("TopTabCloseContainer")
        container.setFixedSize(36, 18)
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Crear el botón real dentro del contenedor utilizando la clase personalizada SVG
        close_btn = TopTabCloseButton(container)
        
        # Desplazarlo a la izquierda para dejar espacio de padding a la izquierda y 8px libres a la derecha de la pestaña
        close_btn.move(8, 1)
        close_btn.clicked.connect(self._on_custom_close_clicked)
        
        self.top_tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, container)

    def _on_custom_close_clicked(self) -> None:
        button = self.sender()
        if not button:
            return
        container = button.parent()
        for row in range(self.top_tab_bar.count()):
            btn = self.top_tab_bar.tabButton(row, QTabBar.ButtonPosition.RightSide)
            if btn is container:
                self.close_tab(row)
                break

    def _get_default_tab_icon(self, url_str: str) -> QIcon:
        import os
        from PyQt6.QtGui import QIcon
        if url_str.startswith("orbital://"):
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets",
                "orbital_icon.png"
            )
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        
        from utils.icon_loader import get_lucide_icon
        return get_lucide_icon("globe", color="#9696a0", size=16)

    # ------------------------------------------------------------- Cierre
    def closeEvent(self, event) -> None:
        # Guardar la sesión respetando el orden visible del sidebar (drag&drop).
        if self.settings.get("restore_session", False):
            urls = []
            for row in range(self.sidebar.count()):
                view = self.sidebar.view_at(row)
                if isinstance(view, WebViewPane):
                    urls.append(view.url().toString())
            self.session.save(urls, max(0, self.sidebar.current_row()))
        self.db.close()
        super().closeEvent(event)
