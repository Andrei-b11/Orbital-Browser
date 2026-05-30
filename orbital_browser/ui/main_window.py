"""Ventana principal y composición de la interfaz (Fase 1 + 2).

Orquesta el perfil de Chromium, el escudo de privacidad, el enrutador de
búsqueda, la persistencia SQLite y la UI (sidebar de pestañas + Omnibox +
área de renderizado), con ventana sin bordes, atajos de teclado, cierre de
pestañas e indicador de progreso de carga.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QStringListModel, QUrl, QTimer, QRectF, QVariantAnimation, QPoint
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QPainter, QColor, QPen
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineLoadingInfo, QWebEngineSettings
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
    QDialog,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QLabel,
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
from ui.components.mosaic_grid import MosaicGrid, MosaicPane
from ui.components.downloads_panel import DownloadsPanel
from ui.components.title_bar import CaptionBar
from ui.components.web_view_pane import WebViewPane
from ui.settings_dialog import SettingsDialog
from utils.db_manager import DBManager
from utils.download_manager import DownloadManager
from utils.icon_processor import tint_icon
from utils.icon_loader import get_lucide_icon
from utils.session_store import SessionStore
from utils import win_effects
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


class DownloadNavButton(QPushButton):
    """Botón de descargas con animación de actividad y badge de "novedad".

    Mientras hay una descarga en curso late un punto naranja en la esquina; al
    terminar, queda un punto fijo que indica "algo nuevo" hasta que se abre el
    panel de descargas.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavButton")
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Descargas recientes")
        self.setIcon(get_lucide_icon("download", color="#9696a0", size=15))
        self._active = False
        self._has_new = False
        self._phase = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1100)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_anim_tick)

    def _on_anim_tick(self, value: float) -> None:
        self._phase = float(value)
        self.update()

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        if active:
            self._has_new = False  # mientras descarga, el badge cede al pulso
            self._anim.start()
        else:
            self._anim.stop()
        self.update()

    def set_has_new(self, has_new: bool) -> None:
        if has_new == self._has_new:
            return
        self._has_new = has_new
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)  # fondo + icono de descarga
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if self._active:
            # Pulso triangular 0→1→0 que crece y se desvanece.
            pulse = 1.0 - abs(2.0 * self._phase - 1.0)
            radius = 3.0 + 1.5 * pulse
            color = QColor("#ff6b00")
            color.setAlpha(int(110 + 145 * pulse))
            painter.setBrush(color)
            cx, cy = self.width() - 6.0, self.height() - 6.0
            painter.drawEllipse(QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius))
        elif self._has_new:
            # Punto fijo de "novedad" con un fino borde para destacar del fondo.
            painter.setBrush(QColor("#ff6b00"))
            painter.setPen(QPen(QColor("#16161a"), 1.5))
            radius = 4.0
            cx, cy = self.width() - 6.0, 6.0
            painter.drawEllipse(QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius))
class ChooseTabsDialog(QDialog):
    def __init__(self, tabs: list[tuple[WebViewPane, str]], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crear Mosaico de Pestañas")
        self.resize(320, 400)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #16161a;
                color: #e3e3e9;
            }
            QLabel {
                color: #e3e3e9;
                font-family: 'Segoe UI', system-ui;
                font-size: 12px;
            }
            QListWidget {
                background-color: #212127;
                border: 1px solid #2d2d37;
                color: #e3e3e9;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                color: #e3e3e9;
            }
            QListWidget::item:hover {
                background-color: #2d2d37;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #212127;
                color: #e3e3e9;
                border: 1px solid #2d2d37;
                border-radius: 6px;
                padding: 6px 12px;
                font-family: 'Segoe UI', system-ui;
            }
            QPushButton:hover {
                background-color: #2d2d37;
            }
            QPushButton:pressed {
                background-color: #ff6b00;
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        label = QLabel("Selecciona las pestañas que deseas agrupar en el mosaico:")
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget)
        
        self.tab_items = []
        for view, title in tabs:
            item = QListWidgetItem(title or "Pestaña")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
            self.tab_items.append((view, item))
            
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_views(self) -> list:
        selected = []
        for view, item in self.tab_items:
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(view)
        return selected


class MainBrowserWindow(QMainWindow):
    windows: list[MainBrowserWindow] = []

    def __init__(self, profile_name: str | None = None) -> None:
        super().__init__()
        
        # Cargar configuración global y definir perfil actual
        from core.config import load_global_settings, save_global_settings
        global_settings = load_global_settings()
        if profile_name is None:
            profile_name = global_settings.get("current_profile", "Default")
        self.profile_name = profile_name

        # Registrar ventana activa para evitar la recolección de basura de Python
        MainBrowserWindow.windows.append(self)

        self.settings = load_settings(self.profile_name)
        self.profile, self.privacy_shield = configure_profile(self.settings, self.profile_name)
        # Habilitar soporte de pantalla completa en el perfil de Chromium
        self.profile.settings().setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True
        )
        self.router = OrbitalSearchRouter(self.settings["search_endpoint"])
        
        # Rutas específicas y aisladas para el perfil actual
        profile_dir = DATA_DIR / "profiles" / self.profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = DBManager(str(profile_dir / "orbital.db"))
        self.downloads = DownloadManager(self.profile, str(profile_dir / "downloads"), db=self.db)
        self.session = SessionStore(str(profile_dir / "session.json"))

        # Puente nativo JS↔Python (Fase 4) compartido por todas las pestañas.
        self.bridge = OrbitalBridge(db=self.db)

        # Trie de autocompletado (Fase 5) alimentado con el historial.
        self.trie = Trie()
        self.views: list[WebViewPane] = []

        # Arrastre de vista activa
        self._dragged_view = None

        # Marco personalizado: en Windows conservamos una ventana nativa normal
        # (con WS_THICKFRAME/WS_CAPTION) para que DWM la redondee y le dé sombra,
        # y eliminamos el marco visible en `nativeEvent` (WM_NCCALCSIZE). En otras
        # plataformas recurrimos a FramelessWindowHint, sin redondeo nativo.
        self._custom_frame = False
        if self.settings.get("frameless", False):
            if sys.platform == "win32":
                self._custom_frame = True
            else:
                self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

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
                    if url.startswith("orbital://mosaic?urls="):
                        from urllib.parse import urlparse, parse_qs
                        try:
                            parsed = urlparse(url)
                            qs = parse_qs(parsed.query)
                            sub_urls = qs.get("urls", [""])[0].split(",")
                            sub_views = []
                            for s_url in sub_urls:
                                if s_url:
                                    view = WebViewPane(self.profile, new_tab_factory=self.open_home_tab)
                                    view.setUrl(QUrl(s_url))
                                    self._attach_bridge(view)
                                    view.urlChanged.connect(lambda qurl, v=view: self._on_url_changed(v, qurl))
                                    view.titleChanged.connect(lambda title, v=view: self._on_title_changed(v, title))
                                    view.iconChanged.connect(lambda _icon, v=view: self._on_icon_changed(v))
                                    view.loadStarted.connect(lambda v=view: self._on_load_progress(v, 0))
                                    view.loadProgress.connect(lambda p, v=view: self._on_load_progress(v, p))
                                    view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(v, ok))
                                    view.page().loadingChanged.connect(lambda info, v=view: self._on_loading_changed(v, info))
                                    view.page().internal_requested.connect(lambda u, v=view: self._render_internal(v, u))
                                    view.renderProcessTerminated.connect(lambda *_: self._on_render_crash(view))
                                    sub_views.append(view)
                            if len(sub_views) >= 2:
                                self._group_tabs_into_mosaic(sub_views)
                            elif len(sub_views) == 1:
                                self.add_new_tab(QUrl(sub_urls[0]))
                        except Exception as e:
                            print(f"Error restoring mosaic: {e}")
                    else:
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
        self.sidebar.context_menu_requested.connect(self._show_tab_context_menu)
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
        self.top_tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.top_tab_bar.customContextMenuRequested.connect(self._on_top_tab_context_menu)

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

        # Área de contenido: stacked widget de pestañas (incluidos MosaicPane).
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
        self.top_bar = QFrame()
        self.top_bar.setObjectName("TopBar")
        layout = QHBoxLayout(self.top_bar)
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

        # Botón de Descargas (abre el panel lateral) con animación + badge.
        self.dl_nav_btn = DownloadNavButton()
        self.dl_nav_btn.clicked.connect(self._toggle_downloads_panel)

        # Botón de Mosaico de pestañas
        self.mosaic_nav_btn = self._nav_button("", "Mosaico de pestañas (Ctrl+M)")
        self.mosaic_nav_btn.setIcon(get_lucide_icon("layout-grid", color="#9696a0", size=15))
        self.mosaic_nav_btn.setCheckable(True)
        self.mosaic_nav_btn.clicked.connect(self.toggle_mosaic)

        # Botón de Perfil
        self.profile_nav_btn = self._nav_button("", f"Perfiles (Actual: {self.profile_name})")
        self.profile_nav_btn.setIcon(get_lucide_icon("user", color="#9696a0", size=15))
        self.profile_nav_btn.clicked.connect(self._show_profile_menu)

        # Botón de Menú (menú desplegable clásico)
        self.menu_nav_btn = self._nav_button("", "Menú")
        self.menu_nav_btn.setIcon(get_lucide_icon("more-vertical", color="#9696a0", size=16))
        self._setup_nav_menu()

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.omnibox)
        layout.addWidget(self.dl_nav_btn)
        layout.addWidget(self.mosaic_nav_btn)
        layout.addWidget(self.profile_nav_btn)
        layout.addWidget(self.menu_nav_btn)
        return self.top_bar

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Mantener el asa de redimensionado pegada a la esquina inferior derecha.
        grip = getattr(self, "sizegrip", None)
        if grip is not None:
            grip.move(self.width() - grip.width() - 2, self.height() - grip.height() - 2)

    def nativeEvent(self, eventType, message):
        """Marco personalizado en Windows: quita el área no-cliente y resuelve
        el redimensionado por los bordes, manteniendo el redondeo de DWM."""
        if self._custom_frame and eventType == b"windows_generic_MSG":
            msg = win_effects.read_msg(int(message))
            # WM_NCCALCSIZE con wParam=TRUE: cliente = ventana completa (sin marco).
            if msg.message == win_effects.WM_NCCALCSIZE and msg.wParam:
                if self.isMaximized():
                    win_effects.adjust_maximized_client(msg.lParam)
                return True, 0
            # WM_NCHITTEST: bordes redimensionables (salvo maximizada).
            if msg.message == win_effects.WM_NCHITTEST and not (
                self.isMaximized() or self.isFullScreen()
            ):
                border = max(4, round(8 * self.devicePixelRatioF()))
                result = win_effects.hit_test_border(int(self.winId()), msg.lParam, border)
                if result is not None:
                    return True, result
        # No llamar a super().nativeEvent(): en PyQt6 provoca un access violation.
        # Devolver (False, 0) deja que Qt procese el mensaje con normalidad.
        return False, 0

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
            "Ctrl+M": self.toggle_mosaic,
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
        completions = self.trie.starts_with(text, limit=8)
        self._completer_model.setStringList(completions)
        completer = self.omnibox.completer()
        if completer:
            if completions and text.strip():
                completer.complete()
            else:
                completer.popup().hide()

    # ------------------------------------------------------- Perfiles de Usuario
    def _show_profile_menu(self) -> None:
        from core.config import load_global_settings, load_settings
        menu = QMenu(self)
        
        # Estilo coherente con el tema de la barra
        menu.setStyleSheet("QMenu { background-color: #1e1e24; color: #c8c8d0; border: 1px solid #2d2d35; } QMenu::item:selected { background-color: #2d2d35; }")
        
        global_settings = load_global_settings()
        profiles = global_settings.get("profiles", ["Default"])
        current = self.profile_name
        
        # Título / Cabecera de perfiles
        title_action = menu.addAction(f"Perfil actual: {current}")
        title_action.setEnabled(False)
        menu.addSeparator()
        
        # Lista de perfiles existentes
        from utils.icon_loader import get_lucide_icon
        for p in profiles:
            action = menu.addAction(p)
            action.setCheckable(True)
            action.setChecked(p == current)
            action.triggered.connect(lambda checked, name=p: self._switch_to_profile(name))
            
        menu.addSeparator()
        
        # Crear perfil nuevo
        create_action = menu.addAction("Crear nuevo perfil...")
        create_action.setIcon(get_lucide_icon("user-plus", color="#9696a0", size=14))
        create_action.triggered.connect(self._create_new_profile_dialog)
        
        # Posicionar el menú debajo del botón de perfil
        menu.exec(self.profile_nav_btn.mapToGlobal(QPoint(0, self.profile_nav_btn.height())))

    @classmethod
    def _find_window_for_profile(cls, name: str) -> "MainBrowserWindow | None":
        """Devuelve la ventana abierta para `name`, si existe (una por perfil)."""
        for win in cls.windows:
            if getattr(win, "profile_name", None) == name:
                return win
        return None

    def _switch_to_profile(self, name: str) -> None:
        if name == self.profile_name:
            return

        from core.config import load_global_settings, save_global_settings
        global_settings = load_global_settings()
        global_settings["current_profile"] = name
        save_global_settings(global_settings)

        # Una ventana por perfil: si ya hay una abierta para ese perfil, se activa
        # en lugar de duplicarla. Abrir dos ventanas del mismo perfil provoca dos
        # conexiones a su orbital.db (fallos de historial) y choques en el
        # almacenamiento de Chromium (los inicios de sesión no se guardan).
        existing = self._find_window_for_profile(name)
        if existing is not None:
            target = existing
            target.showNormal()
            target.raise_()
            target.activateWindow()
        else:
            target = MainBrowserWindow(name)
            target.show()
        target.statusBar().showMessage(f"Perfil activo: {name}", 4000)

        # Cerrar la ventana anterior (cambio real de perfil, no acumular ventanas
        # que mantengan el proceso vivo y bloqueen el almacenamiento del perfil).
        if target is not self:
            QTimer.singleShot(0, self.close)

    def _create_new_profile_dialog(self) -> None:
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        from core.config import load_global_settings, save_global_settings, load_settings
        name, ok = QInputDialog.getText(
            self, 
            "Crear Perfil", 
            "Introduce el nombre del nuevo perfil:",
            text=""
        )
        if ok and name.strip():
            name = name.strip()
            global_settings = load_global_settings()
            profiles = global_settings.get("profiles", ["Default"])
            
            if name in profiles:
                QMessageBox.warning(self, "Error", f"El perfil '{name}' ya existe.")
                return
                
            # Agregar a la lista global y seleccionar por defecto
            profiles.append(name)
            global_settings["profiles"] = profiles
            global_settings["current_profile"] = name
            save_global_settings(global_settings)
            
            # Inicializar la configuración del nuevo perfil copiando la de Default
            _ = load_settings(name)

            # Abrir la ventana del perfil nuevo y cerrar la actual (un perfil =
            # una ventana, para no bloquear el almacenamiento ni el historial).
            new_win = MainBrowserWindow(name)
            new_win.show()
            new_win.statusBar().showMessage(f"¡Perfil '{name}' creado con éxito!", 4000)
            QTimer.singleShot(0, self.close)

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
        # Detener la animación si ya no queda ninguna descarga activa.
        if self._active_downloads() == 0:
            self.dl_nav_btn.set_active(False)
        # Avisar de que hay algo nuevo, salvo que el panel ya esté abierto.
        if not self.downloads_panel.isVisible():
            self.dl_nav_btn.set_has_new(True)

    def _active_downloads(self) -> int:
        return sum(1 for it in self.downloads.items if not it.isFinished())

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
        # add_tab_item selecciona la fila internamente; bloquear la señal evita
        # que _on_tab_selected disuelva el mosaico antes de ubicar la pestaña.
        self.sidebar.tab_list.blockSignals(True)
        row = self.sidebar.add_tab_item(view, "Cargando…")
        self.sidebar.tab_list.blockSignals(False)
        
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

        self.sidebar.tab_list.blockSignals(True)
        self.sidebar.set_current_row(row)
        self.sidebar.tab_list.blockSignals(False)
        self.stack.setCurrentWidget(view)

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
            # Actualizar todos los mosaicos existentes con los nuevos valores de diseño y espaciado
            for view in self.views:
                if isinstance(view, MosaicPane):
                    layout_name = self.settings.get("mosaic_layout", "grid")
                    gap = int(self.settings.get("mosaic_gap", 6))
                    view.set_views(view.sub_views, layout_name, gap)
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
        if view is not None:
            self._select_view(view)
            # Sincronizar la barra de pestañas superior
            self.top_tab_bar.blockSignals(True)
            self.top_tab_bar.setCurrentIndex(row)
            self.top_tab_bar.blockSignals(False)

    def _select_view(self, view: QWidget) -> None:
        self.stack.setCurrentWidget(view)
        # Sincronizar el botón de mosaico
        if isinstance(view, MosaicPane):
            self.mosaic_nav_btn.setChecked(True)
            if view.active_sub_view:
                self.omnibox.setText(view.active_sub_view.url().toString())
        else:
            self.mosaic_nav_btn.setChecked(False)
            if hasattr(view, "url"):
                self.omnibox.setText(view.url().toString())

    def close_current_tab(self) -> None:
        self.close_tab(self.sidebar.current_row())

    def close_tab(self, row: int) -> None:
        view = self.sidebar.view_at(row)
        if view is None:
            return

        if view in self.views:
            self.views.remove(view)
        self.stack.removeWidget(view)
        
        # Liberar sub-vistas del mosaico si aplica
        if isinstance(view, MosaicPane):
            sub_views = view.detach_views()
            for sv in sub_views:
                sv.deleteLater()
        
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
        if isinstance(widget, MosaicPane):
            return widget.active_sub_view
        if isinstance(widget, WebViewPane):
            return widget
        return None

    def _with_view(self, action) -> None:
        view = self._current_view()
        if view is not None:
            action(view)

    def handle_html5_fullscreen(self, view, request) -> None:
        if request.toggleOn():
            self.setUpdatesEnabled(False)
            try:
                # Guardar estado de maximizado de la ventana
                self._was_maximized = self.isMaximized()
                
                # Ocultar todos los controles de interfaz del navegador
                self.top_bar.hide()
                self.sidebar.hide()
                self.top_tab_container.hide()
                if self.caption_bar:
                    self.caption_bar.hide()
                self.statusBar().hide()
                
                self._fullscreen_view = view
                self._fullscreen_parent_tile = None
                self._fullscreen_parent_grid = None
                
                # Buscar si está dentro de una baldosa de mosaico
                tile = view.parent()
                from ui.components.mosaic_grid import MosaicTile, MosaicGrid
                if isinstance(tile, MosaicTile):
                    self._fullscreen_parent_tile = tile
                    grid = tile.parent()
                    if isinstance(grid, MosaicGrid):
                        self._fullscreen_parent_grid = grid
                        
                        # Ocultar la cabecera de la baldosa activa
                        for child in tile.findChildren(QWidget):
                            if child.objectName() == "MosaicTileHeader":
                                child.hide()
                        
                        # Eliminar márgenes
                        tile.layout().setContentsMargins(0, 0, 0, 0)
                        
                        # Ocultar otras tarjetas
                        for other_view, other_tile in grid._tiles.items():
                            if other_view is not view:
                                other_tile.hide()
                                
                        # Ajustar la baldosa activa al tamaño completo del grid
                        self._old_tile_geometry = tile.geometry()
                        tile.setGeometry(0, 0, grid.width(), grid.height())
                
                self.showFullScreen()
                request.accept()
            finally:
                self.setUpdatesEnabled(True)
        else:
            self.setUpdatesEnabled(False)
            try:
                # Restaurar controles de interfaz del navegador
                self.top_bar.show()
                self._apply_tab_layout()
                if self.caption_bar:
                    self.caption_bar.show()
                self.statusBar().show()
                
                # Restaurar estado del mosaico
                if hasattr(self, "_fullscreen_view") and self._fullscreen_view:
                    view = self._fullscreen_view
                    tile = self._fullscreen_parent_tile
                    grid = self._fullscreen_parent_grid
                    
                    if tile and grid:
                        # Mostrar cabecera
                        for child in tile.findChildren(QWidget):
                            if child.objectName() == "MosaicTileHeader":
                                child.show()
                        
                        # Restaurar márgenes
                        tile.layout().setContentsMargins(0, 0, 5, 5)
                        
                        # Mostrar otras tarjetas
                        for other_view, other_tile in grid._tiles.items():
                            if other_view is not view:
                                other_tile.show()
                                
                        # Reposicionar tarjetas a su estado relativo
                        grid._layout_tiles()
                
                if getattr(self, "_was_maximized", False):
                    self.showMaximized()
                else:
                    self.showNormal()
                    
                self._fullscreen_view = None
                self._fullscreen_parent_tile = None
                self._fullscreen_parent_grid = None
                request.accept()
            finally:
                self.setUpdatesEnabled(True)

    # --------------------------------------------------- Mosaico de pestañas
    def toggle_mosaic(self) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, MosaicPane):
            self._dissolve_mosaic_pane(current)
            self.mosaic_nav_btn.setChecked(False)
        elif isinstance(current, WebViewPane):
            self._prompt_create_mosaic(current)
            self.mosaic_nav_btn.setChecked(False)

    def _group_tabs_into_mosaic(self, views_to_group: list[WebViewPane]) -> MosaicPane | None:
        if len(views_to_group) < 2:
            return None

        # Crear el panel de mosaico
        mosaic_pane = MosaicPane(self.profile)

        # Conectar señales del panel de mosaico al main_window
        mosaic_pane.urlChanged.connect(lambda qurl, v=mosaic_pane: self._on_url_changed(v, qurl))
        mosaic_pane.titleChanged.connect(lambda title, v=mosaic_pane: self._on_title_changed(v, title))
        mosaic_pane.iconChanged.connect(lambda _icon, v=mosaic_pane: self._on_icon_changed(v))

        # Registrar eventos internos del mosaico
        mosaic_pane.tile_activated.connect(self._on_mosaic_tile_activated)
        mosaic_pane.grid.tile_close_requested.connect(self._on_mosaic_tile_close_requested)

        # Quitar los WebViewPane de self.views y del sidebar/top tab bar, SIN destruirlos
        for view in views_to_group:
            row = self.sidebar.row_of(view)
            if row >= 0:
                self.sidebar.tab_list.blockSignals(True)
                item = self.sidebar.tab_list.takeItem(row)
                del item
                self.sidebar.tab_list.blockSignals(False)

                self.top_tab_bar.blockSignals(True)
                self.top_tab_bar.removeTab(row)
                self.top_tab_bar.blockSignals(False)

            if view in self.views:
                self.views.remove(view)
            self.stack.removeWidget(view)

        # Añadir las vistas al mosaico
        mosaic_pane.set_views(
            views_to_group,
            self.settings.get("mosaic_layout", "grid"),
            int(self.settings.get("mosaic_gap", 6))
        )

        # Añadir el mosaico a la ventana principal
        self.views.append(mosaic_pane)
        self.stack.addWidget(mosaic_pane)

        # Añadir el mosaico al sidebar y top tab bar
        self.sidebar.tab_list.blockSignals(True)
        row = self.sidebar.add_tab_item(mosaic_pane, mosaic_pane.title())
        self.sidebar.tab_list.blockSignals(False)

        initial_icon = self._get_default_tab_icon("orbital://mosaic")
        self.sidebar.set_tab_icon(row, initial_icon)

        self.top_tab_bar.blockSignals(True)
        idx = self.top_tab_bar.addTab(initial_icon, mosaic_pane.title())
        self._add_custom_close_button(idx)
        self.top_tab_bar.setCurrentIndex(idx)
        self.top_tab_bar.blockSignals(False)

        self.sidebar.set_current_row(row)
        self.stack.setCurrentWidget(mosaic_pane)

        return mosaic_pane

    def _dissolve_mosaic_pane(self, mosaic_pane: MosaicPane) -> None:
        sub_views = mosaic_pane.detach_views()

        # Quitar el mosaico de las listas
        if mosaic_pane in self.views:
            self.views.remove(mosaic_pane)
        self.stack.removeWidget(mosaic_pane)

        row = self.sidebar.row_of(mosaic_pane)
        if row >= 0:
            self.sidebar.tab_list.blockSignals(True)
            item = self.sidebar.tab_list.takeItem(row)
            del item
            self.sidebar.tab_list.blockSignals(False)

            self.top_tab_bar.blockSignals(True)
            self.top_tab_bar.removeTab(row)
            self.top_tab_bar.blockSignals(False)

        mosaic_pane.deleteLater()

        # Volver a añadir las sub-vistas como pestañas normales
        for view in sub_views:
            self.views.append(view)
            self.stack.addWidget(view)

            self.sidebar.tab_list.blockSignals(True)
            r = self.sidebar.add_tab_item(view, view.title() or "Pestaña")
            self.sidebar.tab_list.blockSignals(False)

            icon = view.icon()
            if icon.isNull():
                icon = self._get_default_tab_icon(view.url().toString())
            self.sidebar.set_tab_icon(r, icon)

            self.top_tab_bar.blockSignals(True)
            idx = self.top_tab_bar.addTab(icon, view.title() or "Pestaña")
            self._add_custom_close_button(idx)
            self.top_tab_bar.blockSignals(False)

        if sub_views:
            self.sidebar.set_current_row(self.sidebar.count() - 1)

    def _add_tab_to_mosaic(self, source_view: WebViewPane, target_mosaic: MosaicPane) -> None:
        row = self.sidebar.row_of(source_view)
        if row >= 0:
            self.sidebar.tab_list.blockSignals(True)
            item = self.sidebar.tab_list.takeItem(row)
            del item
            self.sidebar.tab_list.blockSignals(False)

            self.top_tab_bar.blockSignals(True)
            self.top_tab_bar.removeTab(row)
            self.top_tab_bar.blockSignals(False)

        if source_view in self.views:
            self.views.remove(source_view)
        self.stack.removeWidget(source_view)

        # Añadir al mosaico
        target_mosaic.add_view(source_view)

        # Seleccionar la pestaña de mosaico
        m_row = self.sidebar.row_of(target_mosaic)
        if m_row >= 0:
            self.sidebar.set_current_row(m_row)

    def _change_mosaic_layout(self, mosaic_pane: MosaicPane, layout_name: str) -> None:
        mosaic_pane.set_views(
            mosaic_pane.sub_views,
            layout_name,
            mosaic_pane._gap
        )

    def _prompt_create_mosaic(self, initial_view: WebViewPane) -> None:
        other_tabs = []
        for v in self.views:
            if isinstance(v, WebViewPane) and v is not initial_view:
                row = self.sidebar.row_of(v)
                widget = self.sidebar._widget_at(row) if row >= 0 else None
                title = widget.title_label._full if (widget and widget.title_label) else (v.title() or "Pestaña")
                other_tabs.append((v, title))

        if not other_tabs:
            self.statusBar().showMessage(
                "No hay otras pestañas abiertas para crear un mosaico", 4000
            )
            return

        dialog = ChooseTabsDialog(other_tabs, self)
        if dialog.exec():
            selected = dialog.get_selected_views()
            if selected:
                views_to_group = [initial_view] + selected
                self._group_tabs_into_mosaic(views_to_group)

    def _show_tab_context_menu(self, index: int, global_pos: QPoint) -> None:
        view = self.views[index]
        menu = QMenu(self)
        menu.setObjectName("TabContextMenu")

        if isinstance(view, WebViewPane):
            act_group = menu.addAction("Crear mosaico con...")
            act_group.triggered.connect(lambda: self._prompt_create_mosaic(view))

            existing_mosaics = [v for v in self.views if isinstance(v, MosaicPane)]
            if existing_mosaics:
                add_to_menu = menu.addMenu("Añadir a mosaico")
                for m in existing_mosaics:
                    act_add = add_to_menu.addAction(m.title())
                    act_add.triggered.connect(
                        lambda checked, target_m=m, source_v=view: self._add_tab_to_mosaic(source_v, target_m)
                    )

        elif isinstance(view, MosaicPane):
            act_dissolve = menu.addAction("Deshacer mosaico")
            act_dissolve.triggered.connect(lambda: self._dissolve_mosaic_pane(view))

            menu.addSeparator()

            layout_menu = menu.addMenu("Disposición de mosaico")
            for lay in ["grid", "columns", "rows"]:
                label = "Rejilla" if lay == "grid" else ("Columnas" if lay == "columns" else "Filas")
                act_lay = layout_menu.addAction(label)
                act_lay.setCheckable(True)
                act_lay.setChecked(view._layout_name == lay)
                act_lay.triggered.connect(
                    lambda checked, l=lay, m=view: self._change_mosaic_layout(m, l)
                )

        menu.addSeparator()
        act_close = menu.addAction("Cerrar pestaña")
        act_close.triggered.connect(lambda: self.close_tab(index))

        menu.exec(global_pos)

    def _on_top_tab_context_menu(self, pos: QPoint) -> None:
        idx = self.top_tab_bar.tabAt(pos)
        if idx >= 0:
            global_pos = self.top_tab_bar.mapToGlobal(pos)
            self._show_tab_context_menu(idx, global_pos)

    def _on_mosaic_tile_activated(self, view: WebViewPane) -> None:
        self.omnibox.setText(view.url().toString())
        mosaic_pane = self.sender()
        if isinstance(mosaic_pane, MosaicPane):
            # Forzar actualización de la pestaña contenedora
            row = self.sidebar.row_of(mosaic_pane)
            if row >= 0:
                self.sidebar.set_tab_title(row, mosaic_pane.title())
                self.top_tab_bar.setTabText(row, mosaic_pane.title())
                self.sidebar.set_tab_icon(row, mosaic_pane.icon())
                self.top_tab_bar.setTabIcon(row, mosaic_pane.icon())

    def _on_mosaic_tile_close_requested(self, view: WebViewPane) -> None:
        mosaic_pane = self.sender()
        if not isinstance(mosaic_pane, MosaicPane):
            # Si el sender es el Grid, obtener su parent
            grid = self.sender()
            if isinstance(grid, MosaicGrid) and isinstance(grid.parent(), MosaicPane):
                mosaic_pane = grid.parent()
            else:
                return

        if mosaic_pane.remove_view(view):
            # Devolver la vista al stack principal y registrar como pestaña normal
            self.views.append(view)
            self.stack.addWidget(view)

            self.sidebar.tab_list.blockSignals(True)
            r = self.sidebar.add_tab_item(view, view.title() or "Pestaña")
            self.sidebar.tab_list.blockSignals(False)

            icon = view.icon()
            if icon.isNull():
                icon = self._get_default_tab_icon(view.url().toString())
            self.sidebar.set_tab_icon(r, icon)

            self.top_tab_bar.blockSignals(True)
            idx = self.top_tab_bar.addTab(icon, view.title() or "Pestaña")
            self._add_custom_close_button(idx)
            self.top_tab_bar.blockSignals(False)

            if len(mosaic_pane.sub_views) < 2:
                self._dissolve_mosaic_pane(mosaic_pane)

    # ------------------------------------------------------ Barra lateral
    def toggle_sidebar(self) -> None:
        """Alterna entre las pestañas del panel lateral y las de la barra superior.

        Son mutuamente excluyentes: si la barra lateral pasa a estar visible se
        ocultan las pestañas de arriba, y al ocultarla se muestran arriba. Así
        nunca se ven los dos juegos de pestañas a la vez.
        """
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self._mount_top_tabs()
        else:
            self._hide_top_tabs()
            self.sidebar.show()

    # -------------------------------------------------- Sincronización y Layouts
    def _mount_top_tabs(self) -> None:
        """Coloca y muestra la barra de pestañas en la zona superior.

        Si la ventana es *frameless* las integra en la barra de título; en caso
        contrario usa el contenedor de pestañas horizontal independiente.
        """
        if self.settings.get("frameless", False) and self.caption_bar:
            self.caption_bar.tabs_layout.insertWidget(0, self.top_tab_bar)
            self.caption_bar.tabs_layout.insertWidget(1, self.add_tab_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            self.caption_bar.tabs_container.show()
            self.caption_bar.title_label.hide()
            self.top_tab_container.hide()
        else:
            self.top_tab_container.layout().insertWidget(0, self.top_tab_bar)
            self.top_tab_container.layout().insertWidget(1, self.add_tab_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            self.top_tab_container.show()
            if self.caption_bar:
                self.caption_bar.tabs_container.hide()
                self.caption_bar.title_label.show()

    def _hide_top_tabs(self) -> None:
        """Oculta cualquier presentación de pestañas en la zona superior."""
        self.top_tab_container.hide()
        if self.caption_bar:
            self.caption_bar.tabs_container.hide()
            self.caption_bar.title_label.show()

    def _apply_tab_layout(self) -> None:
        position = self.settings.get("tab_position", "left")

        if position == "top":
            # Pestañas arriba; la barra lateral se oculta.
            self.sidebar.hide()
            self._mount_top_tabs()
        else:
            # Pestañas verticales en la barra lateral; nada arriba.
            self._hide_top_tabs()
            self.sidebar.show()

    def _on_top_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self.views):
            self.sidebar.tab_list.blockSignals(True)
            self.sidebar.set_current_row(index)
            self.sidebar.tab_list.blockSignals(False)

            self._select_view(self.views[index])

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
        # El widget recién creado nace sin estado activo; resincronizar el título.
        self.sidebar._apply_selection(self.sidebar.current_row())

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
        self.dl_nav_btn.set_has_new(False)  # ya se han visto las descargas

    def _toggle_downloads_panel(self) -> None:
        if self.downloads_panel.isVisible():
            self.downloads_panel.hide()
        else:
            self._show_downloads_panel()

    def _on_download_started(self, name: str) -> None:
        self.statusBar().showMessage(f"⬇ Descargando {name}…")
        self.dl_nav_btn.set_active(True)  # arranca la animación de actividad
        if self.settings.get("downloads_view", "panel") == "panel":
            self._show_downloads_panel()

    def _setup_nav_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("NavMenu")
        
        act_new_tab = menu.addAction("Nueva pestaña")
        act_new_tab.setShortcut("Ctrl+T")
        act_new_tab.triggered.connect(self.open_home_tab)

        act_mosaic = menu.addAction("Mosaico de pestañas")
        act_mosaic.setShortcut("Ctrl+M")
        act_mosaic.triggered.connect(self.toggle_mosaic)

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
            hwnd = int(self.winId())
            apply_rounded_corners(hwnd)  # DWMWCP_ROUND
            if self._custom_frame:
                # Forzar un WM_NCCALCSIZE para que se elimine el marco visible.
                win_effects.force_frame_recalc(hwnd)
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
        from utils.icon_loader import get_lucide_icon
        if "mosaic" in url_str:
            return get_lucide_icon("layout-grid", color="#ff6b00", size=16)
        if url_str.startswith("orbital://"):
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets",
                "orbital_icon.png"
            )
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        
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
                elif isinstance(view, MosaicPane):
                    sub_urls = [v.url().toString() for v in view.sub_views]
                    urls.append(f"orbital://mosaic?urls={','.join(sub_urls)}")
            self.session.save(urls, max(0, self.sidebar.current_row()))
        self.db.close()
        
        # Eliminar ventana de la lista global de referencias activas
        if self in MainBrowserWindow.windows:
            MainBrowserWindow.windows.remove(self)
            
        super().closeEvent(event)
