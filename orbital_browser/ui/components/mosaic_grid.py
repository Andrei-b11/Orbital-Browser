"""Mosaico de pestañas: muestra varias vistas web a la vez en una rejilla de tarjetas.

Cada vista se envuelve en un `MosaicTile` con una cabecera (título + botón para
quitarla del mosaico). Una de las baldosas es la "activa": recibe la navegación
(omnibox, atrás/adelante, recargar) y se resalta con un borde de acento.

La disposición inicial se decide según la configuración:
    - "grid":    rejilla cuadrada (ceil(sqrt(n)) columnas)
    - "columns": todas en una fila
    - "rows":    todas en una columna

Los mosaicos son tipo tarjeta y se pueden redimensionar libremente tanto en X como en Y,
además de poder arrastrar las cabeceras para mover los paneles libremente por la rejilla.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QMimeData, QPoint, QRectF
from PyQt6.QtGui import QIcon, QDrag, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)


class _TileHeader(QFrame):
    """Cabecera de una baldosa; al pulsarla se activa la baldosa y al arrastrarla se desplaza."""

    clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_start_global_pos = None
        self._tile_start_pos = None
        self._has_dragged = False

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_global_pos = event.globalPosition()
            self._tile_start_pos = self.parent().pos()
            self._has_dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and getattr(self, "_drag_start_global_pos", None) is not None:
            delta = event.globalPosition() - self._drag_start_global_pos
            if not self._has_dragged and delta.toPoint().manhattanLength() >= QApplication.startDragDistance():
                self._has_dragged = True
            
            if self._has_dragged:
                new_x = self._tile_start_pos.x() + int(delta.x())
                new_y = self._tile_start_pos.y() + int(delta.y())
                
                # Limitar el movimiento a los bordes de MosaicGrid
                grid = self.parent().parent()
                if isinstance(grid, MosaicGrid):
                    new_x = max(0, min(grid.width() - self.parent().width(), new_x))
                    new_y = max(0, min(grid.height() - self.parent().height(), new_y))
                
                self.parent().move(new_x, new_y)
                
                if isinstance(grid, MosaicGrid):
                    grid.update_tile_geometry(self.parent().view, self.parent().geometry())
                
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not getattr(self, "_has_dragged", False):
                self.clicked.emit()
            self._drag_start_global_pos = None
            self._tile_start_pos = None
            self._has_dragged = False
        super().mouseReleaseEvent(event)


class MosaicTile(QFrame):
    """Una celda del mosaico: cabecera + vista web con márgenes para redimensionamiento en X/Y."""

    activated = pyqtSignal(object)        # emite la vista
    close_requested = pyqtSignal(object)  # emite la vista

    def __init__(self, view, title: str = "") -> None:
        super().__init__()
        self.view = view
        self.setObjectName("MosaicTile")
        self.setProperty("active", False)
        self.setMouseTracking(True)  # Activar detección de hover para redimensionar

        layout = QVBoxLayout(self)
        # Margen derecho e inferior de 5px para detectar los gestos de redimensionamiento
        layout.setContentsMargins(0, 0, 5, 5)
        layout.setSpacing(0)

        header = _TileHeader(self)
        header.setObjectName("MosaicTileHeader")
        header.setFixedHeight(26)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.clicked.connect(lambda: self.activated.emit(self.view))
        h = QHBoxLayout(header)
        h.setContentsMargins(6, 0, 4, 0)
        h.setSpacing(4)

        from utils.icon_loader import get_lucide_icon

        # Botones de navegación
        self.back_btn = QPushButton()
        self.back_btn.setObjectName("MosaicTileNav")
        self.back_btn.setIcon(get_lucide_icon("chevron-left", color="#9696a0", size=11))
        self.back_btn.setFixedSize(18, 18)
        self.back_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setToolTip("Atrás")
        self.back_btn.clicked.connect(lambda: self.view.back())

        self.forward_btn = QPushButton()
        self.forward_btn.setObjectName("MosaicTileNav")
        self.forward_btn.setIcon(get_lucide_icon("chevron-right", color="#9696a0", size=11))
        self.forward_btn.setFixedSize(18, 18)
        self.forward_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.forward_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forward_btn.setToolTip("Adelante")
        self.forward_btn.clicked.connect(lambda: self.view.forward())

        self.reload_btn = QPushButton()
        self.reload_btn.setObjectName("MosaicTileNav")
        self.reload_btn.setIcon(get_lucide_icon("rotate-cw", color="#9696a0", size=10))
        self.reload_btn.setFixedSize(18, 18)
        self.reload_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reload_btn.setToolTip("Recargar")
        self.reload_btn.clicked.connect(lambda: self.view.reload())

        self.home_btn = QPushButton()
        self.home_btn.setObjectName("MosaicTileNav")
        self.home_btn.setIcon(get_lucide_icon("home", color="#9696a0", size=10))
        self.home_btn.setFixedSize(18, 18)
        self.home_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.setToolTip("Página de inicio")
        self.home_btn.clicked.connect(self._go_home)

        self._conns = []
        # Conectar disponibilidad de historial si está disponible
        if hasattr(view, "urlChanged"):
            c = view.urlChanged.connect(self._update_nav_states)
            self._conns.append((view.urlChanged, c))
        if hasattr(view, "loadFinished"):
            c = view.loadFinished.connect(self._on_load_finished)
            self._conns.append((view.loadFinished, c))
        self._update_nav_states()

        self.title_label = QLabel(title or "Pestaña")
        self.title_label.setObjectName("MosaicTileTitle")

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("MosaicTileClose")
        self.close_btn.setIcon(get_lucide_icon("x", color="#9696a0", size=10))
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Quitar del mosaico")
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self.view))

        h.addWidget(self.back_btn)
        h.addWidget(self.forward_btn)
        h.addWidget(self.reload_btn)
        h.addWidget(self.home_btn)
        h.addWidget(self.title_label, 1)
        h.addWidget(self.close_btn)

        layout.addWidget(header)
        layout.addWidget(view, 1)
        
        header.setMouseTracking(True)
        view.show()
        
        self._resize_dir = None
        self._drag_start_pos = None
        self._drag_start_size = None
        self.destroyed.connect(self.cleanup)

    def _go_home(self) -> None:
        home_url = "https://www.google.com"
        main_win = self.window()
        if hasattr(main_win, "settings"):
            home_url = main_win.settings.get("home_url", "https://www.google.com")
        if not home_url.startswith(("http://", "https://", "file://", "orbital://")):
            home_url = "https://" + home_url
        self.view.setUrl(QUrl(home_url))

    def _on_load_finished(self, ok: bool) -> None:
        self._update_nav_states()

    def cleanup(self) -> None:
        if hasattr(self, "_conns"):
            for signal, conn in self._conns:
                try:
                    signal.disconnect(conn)
                except (TypeError, RuntimeError):
                    pass
            self._conns.clear()

    def _update_nav_states(self) -> None:
        if hasattr(self, "view") and hasattr(self.view, "page") and self.view.page() is not None:
            try:
                history = self.view.page().history()
                self.back_btn.setEnabled(history.canGoBack())
                self.forward_btn.setEnabled(history.canGoForward())
            except RuntimeError:
                # El objeto C++ subyacente puede haber sido destruido durante la limpieza
                pass
        else:
            try:
                self.back_btn.setEnabled(False)
                self.forward_btn.setEnabled(False)
            except RuntimeError:
                pass

    def set_active(self, active: bool) -> None:
        if self.property("active") == active:
            return
        self.setProperty("active", active)
        # Re-evaluar el QSS dependiente de la propiedad dinámica `active`.
        self.style().unpolish(self)
        self.style().polish(self)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title or "Pestaña")

    def mouseMoveEvent(self, event) -> None:
        if self._resize_dir is not None:
            # Lógica de arrastre de cambio de tamaño
            delta = event.globalPosition() - self._drag_start_pos
            new_w = self._drag_start_size.width()
            new_h = self._drag_start_size.height()
            
            if self._resize_dir == "horizontal" or self._resize_dir == "both":
                new_w += int(delta.x())
            if self._resize_dir == "vertical" or self._resize_dir == "both":
                new_h += int(delta.y())
                
            new_w = max(150, new_w)
            new_h = max(100, new_h)
            
            self.resize(new_w, new_h)
            
            grid = self.parent()
            if isinstance(grid, MosaicGrid):
                grid.update_tile_geometry(self.view, self.geometry())
            
            event.accept()
            return

        pos = event.position()
        w = self.width()
        h = self.height()
        
        # Detectar si el ratón pasa por encima de la banda de 6px en el borde inferior/derecho
        on_right = (pos.x() >= w - 6)
        on_bottom = (pos.y() >= h - 6)
        
        if on_right and on_bottom:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif on_right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif on_bottom:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            w = self.width()
            h = self.height()
            
            on_right = (pos.x() >= w - 6)
            on_bottom = (pos.y() >= h - 6)
            
            if on_right and on_bottom:
                self._resize_dir = "both"
            elif on_right:
                self._resize_dir = "horizontal"
            elif on_bottom:
                self._resize_dir = "vertical"
            else:
                self._resize_dir = None
                
            if self._resize_dir is not None:
                self._drag_start_pos = event.globalPosition()
                self._drag_start_size = self.size()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resize_dir = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class MosaicGrid(QWidget):
    """Contenedor de varias baldosas usando posicionamiento absoluto y geometrías proporcionales."""

    tile_activated = pyqtSignal(object)
    tile_close_requested = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("MosaicGrid")
        
        self._tiles: dict[object, MosaicTile] = {}
        self._relative_geometries: dict[object, QRectF] = {}
        self._gap = 6

    def set_views(self, views: list, layout: str = "grid", gap: int = 6) -> None:
        """Rehace el mosaico con las vistas dadas utilizando posicionamiento absoluto."""
        self._clear_tiles()
        self._gap = gap
        
        n = len(views)
        if n == 0:
            return

        # Calcular geometrías relativas iniciales (como porcentajes decimales de 0 a 1)
        if layout == "columns":
            w = 1.0 / n
            for i, view in enumerate(views):
                self._relative_geometries[view] = QRectF(i * w, 0.0, w, 1.0)
        elif layout == "rows":
            h = 1.0 / n
            for i, view in enumerate(views):
                self._relative_geometries[view] = QRectF(0.0, i * h, 1.0, h)
        else:  # "grid"
            cols = max(1, math.ceil(math.sqrt(n)))
            rows = math.ceil(n / cols)
            w = 1.0 / cols
            h = 1.0 / rows
            for i, view in enumerate(views):
                r = i // cols
                c = i % cols
                self._relative_geometries[view] = QRectF(c * w, r * h, w, h)

        # Crear y posicionar baldosas
        for view in views:
            tile = MosaicTile(view, title=self._title_of(view))
            tile.activated.connect(self.tile_activated.emit)
            tile.close_requested.connect(self.tile_close_requested.emit)
            self._tiles[view] = tile
            tile.setParent(self)
            tile.show()

        self._layout_tiles()

    @staticmethod
    def _title_of(view) -> str:
        try:
            return view.title() or "Pestaña"
        except Exception:
            return "Pestaña"

    def _clear_tiles(self) -> None:
        """Desmonta las baldosas dejando las vistas sin padre (reparentables)."""
        for view, tile in list(self._tiles.items()):
            tile.cleanup()  # Desconectar señales de la vista
            view.setParent(None)
            tile.setParent(None)
            tile.deleteLater()
        self._tiles.clear()
        self._relative_geometries.clear()

    def detach_views(self) -> list:
        """Devuelve las vistas y desmonta el mosaico."""
        views = list(self._tiles.keys())
        self._clear_tiles()
        return views

    def set_active(self, view) -> None:
        for v, tile in self._tiles.items():
            tile.set_active(v is view)

    def update_title(self, view, title: str) -> None:
        tile = self._tiles.get(view)
        if tile is not None:
            tile.set_title(title)

    def views(self) -> list:
        return list(self._tiles.keys())

    def _layout_tiles(self) -> None:
        if not self._tiles:
            return
        w_total = self.width()
        h_total = self.height()
        gap = self._gap
        
        for view, tile in self._tiles.items():
            rel = self._relative_geometries.get(view)
            if rel is None:
                continue
            
            px_x = int(rel.x() * w_total) + gap
            px_y = int(rel.y() * h_total) + gap
            px_w = int(rel.width() * w_total) - 2 * gap
            px_h = int(rel.height() * h_total) - 2 * gap
            
            px_w = max(150, px_w)
            px_h = max(100, px_h)
            
            tile.setGeometry(px_x, px_y, px_w, px_h)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_tiles()

    def update_tile_geometry(self, view, geom) -> None:
        w_total = self.width()
        h_total = self.height()
        gap = self._gap
        
        # Recalcular posición proporcional relativa
        rel_x = (geom.x() - gap) / w_total if w_total > 0 else 0.0
        rel_y = (geom.y() - gap) / h_total if h_total > 0 else 0.0
        rel_w = (geom.width() + 2 * gap) / w_total if w_total > 0 else 1.0
        rel_h = (geom.height() + 2 * gap) / h_total if h_total > 0 else 1.0
        
        # Clampear a rangos válidos
        rel_x = max(0.0, min(1.0, rel_x))
        rel_y = max(0.0, min(1.0, rel_y))
        rel_w = max(0.05, min(1.0, rel_w))
        rel_h = max(0.05, min(1.0, rel_h))
        
        self._relative_geometries[view] = QRectF(rel_x, rel_y, rel_w, rel_h)


class MosaicPane(QWidget):
    """Contenedor de mosaico que funciona como una sola pestaña."""

    titleChanged = pyqtSignal(str)
    urlChanged = pyqtSignal(QUrl)
    iconChanged = pyqtSignal(QIcon)
    tile_activated = pyqtSignal(object)

    def __init__(self, profile, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.sub_views = []
        self.active_sub_view = None
        self._layout_name = "grid"
        self._gap = 6

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.grid = MosaicGrid(self)
        self.grid.tile_activated.connect(self._on_tile_activated)
        self.grid.tile_close_requested.connect(self._on_tile_close_requested)
        layout.addWidget(self.grid)

    def set_views(self, views: list, layout_name: str = "grid", gap: int = 6) -> None:
        for view in self.sub_views:
            try:
                view.titleChanged.disconnect(self._on_sub_view_title_changed)
                view.urlChanged.disconnect(self._on_sub_view_url_changed)
                view.iconChanged.disconnect(self._on_sub_view_icon_changed)
            except (TypeError, RuntimeError):
                pass

        self.sub_views = views
        self._layout_name = layout_name
        self._gap = gap

        for view in self.sub_views:
            view.titleChanged.connect(self._on_sub_view_title_changed)
            view.urlChanged.connect(self._on_sub_view_url_changed)
            view.iconChanged.connect(self._on_sub_view_icon_changed)

        self.grid.set_views(views, layout_name, gap)
        if views:
            if self.active_sub_view not in views:
                self.active_sub_view = views[0]
            self.grid.set_active(self.active_sub_view)
            
            # Emitir actualizaciones iniciales
            self.titleChanged.emit(self.title())
            self.urlChanged.emit(self.url())
            self.iconChanged.emit(self.icon())
            self.tile_activated.emit(self.active_sub_view)

    def set_active_sub_view(self, view) -> None:
        if view in self.sub_views:
            self.active_sub_view = view
            self.grid.set_active(view)
            self.titleChanged.emit(self.title())
            self.urlChanged.emit(self.url())
            self.iconChanged.emit(self.icon())
            self.tile_activated.emit(view)

    def _on_tile_activated(self, view) -> None:
        self.set_active_sub_view(view)

    def _on_tile_close_requested(self, view) -> None:
        self.grid.tile_close_requested.emit(view)

    def _on_sub_view_title_changed(self, title: str) -> None:
        if self.sender() is self.active_sub_view:
            self.titleChanged.emit(self.title())

    def _on_sub_view_url_changed(self, url: QUrl) -> None:
        if self.sender() is self.active_sub_view:
            self.urlChanged.emit(url)

    def _on_sub_view_icon_changed(self) -> None:
        if self.sender() is self.active_sub_view:
            self.iconChanged.emit(self.active_sub_view.icon())

    def add_view(self, view) -> None:
        if view not in self.sub_views:
            self.sub_views.append(view)
            self.set_views(self.sub_views, self._layout_name, self._gap)
            self.set_active_sub_view(view)

    def remove_view(self, view) -> bool:
        if view in self.sub_views:
            try:
                view.titleChanged.disconnect(self._on_sub_view_title_changed)
                view.urlChanged.disconnect(self._on_sub_view_url_changed)
                view.iconChanged.disconnect(self._on_sub_view_icon_changed)
            except (TypeError, RuntimeError):
                pass
            
            self.sub_views.remove(view)
            if self.active_sub_view == view:
                self.active_sub_view = self.sub_views[0] if self.sub_views else None
            self.set_views(self.sub_views, self._layout_name, self._gap)
            return True
        return False

    def detach_views(self) -> list:
        views = list(self.sub_views)
        for view in views:
            try:
                view.titleChanged.disconnect(self._on_sub_view_title_changed)
                view.urlChanged.disconnect(self._on_sub_view_url_changed)
                view.iconChanged.disconnect(self._on_sub_view_icon_changed)
            except (TypeError, RuntimeError):
                pass
        self.grid._clear_tiles()
        self.sub_views.clear()
        self.active_sub_view = None
        for v in views:
            v.setParent(None)
        return views

    def title(self) -> str:
        if self.sub_views:
            titles = []
            for v in self.sub_views:
                t = v.title()
                if not t or t == "Cargando…":
                    t = "Pestaña"
                titles.append(t)
            return " | ".join(titles[:2]) + ("..." if len(titles) > 2 else "")
        return "Mosaico"

    def url(self) -> QUrl:
        if self.active_sub_view:
            return self.active_sub_view.url()
        return QUrl("orbital://mosaic")

    def icon(self) -> QIcon:
        if self.active_sub_view:
            return self.active_sub_view.icon()
        return QIcon()

    def zoomFactor(self) -> float:
        if self.active_sub_view:
            return self.active_sub_view.zoomFactor()
        return 1.0

    def setZoomFactor(self, factor: float) -> None:
        if self.active_sub_view:
            self.active_sub_view.setZoomFactor(factor)

    def reload(self) -> None:
        if self.active_sub_view:
            self.active_sub_view.reload()

    def back(self) -> None:
        if self.active_sub_view:
            self.active_sub_view.back()

    def forward(self) -> None:
        if self.active_sub_view:
            self.active_sub_view.forward()

    def findText(self, text: str, flags=None) -> None:
        if self.active_sub_view:
            if flags is not None:
                self.active_sub_view.findText(text, flags)
            else:
                self.active_sub_view.findText(text)

    def setUrl(self, url: QUrl) -> None:
        if self.active_sub_view:
            self.active_sub_view.setUrl(url)

    # Arrastrar y soltar
    def dragEnterEvent(self, event) -> None:
        main_win = self.window()
        if hasattr(main_win, "_dragged_view") and main_win._dragged_view is not None:
            if main_win._dragged_view is not self and main_win._dragged_view not in self.sub_views:
                event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        main_win = self.window()
        if hasattr(main_win, "_dragged_view") and main_win._dragged_view is not None:
            view = main_win._dragged_view
            main_win._dragged_view = None
            if hasattr(main_win, "_add_tab_to_mosaic"):
                main_win._add_tab_to_mosaic(view, self)
                event.acceptProposedAction()
