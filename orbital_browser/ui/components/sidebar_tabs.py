"""Sistema de pestañas verticales colapsables (Fase 2).

Cada pestaña es un widget compacto con favicon + título recortado + botón de
cierre (✕). El reordenado por arrastre (InternalMove) mantiene la asociación
item↔vista guardada en `UserRole`, así que no hay que sincronizar nada.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

TAB_HEIGHT = 30


class _ElidedLabel(QLabel):
    """Etiqueta que recorta el texto con puntos suspensivos si no cabe."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full = text
        self.setText(text)

    def setFullText(self, text: str) -> None:
        self._full = text or ""
        self.setToolTip(self._full)
        self._relayout()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        metrics = self.fontMetrics()
        self.setText(metrics.elidedText(self._full, Qt.TextElideMode.ElideRight, self.width()))


class _TabCloseButton(QPushButton):
    """Botón de cierre con icono que pasa a blanco al pasar el ratón.

    Replica el comportamiento de `TopTabCloseButton` de la barra superior para
    que las pestañas del panel lateral se vean idénticas.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TabClose")
        self.setFixedSize(18, 18)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Cerrar pestaña")
        self._update_icon(False)

    def _update_icon(self, hovered: bool) -> None:
        from utils.icon_loader import get_lucide_icon
        color = "#ffffff" if hovered else "#9696a0"
        self.setIcon(get_lucide_icon("x", color=color, size=10))

    def enterEvent(self, event) -> None:
        self._update_icon(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._update_icon(False)
        super().leaveEvent(event)


class TabItemWidget(QWidget):
    """Contenido visual de una pestaña: icono, título y botón de cierre."""

    close_clicked = pyqtSignal(object)  # emite la vista asociada

    def __init__(self, view: object, title: str) -> None:
        super().__init__()
        self.view = view
        self.setObjectName("TabItem")
        self.setFixedHeight(TAB_HEIGHT)
        self._hovered = False
        self._selected = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(7)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setObjectName("TabIcon")

        self.title_label = _ElidedLabel(title)
        self.title_label.setObjectName("TabTitle")

        self.close_btn = _TabCloseButton()
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit(self.view))

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.close_btn)
        self._refresh_title_color()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._refresh_title_color()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._refresh_title_color()
        super().leaveEvent(event)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._refresh_title_color()

    def _refresh_title_color(self) -> None:
        # Texto blanco al pasar el ratón o cuando la pestaña está activa, igual
        # que el comportamiento de TopTabBar; gris en reposo.
        color = "#ffffff" if (self._hovered or self._selected) else "#9696a0"
        self.title_label.setStyleSheet(f"color:{color}; background:transparent;")

    def set_title(self, title: str) -> None:
        self.title_label.setFullText(title or "Sin título")

    def set_icon(self, icon: QIcon) -> None:
        if icon is not None and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(16, 16))
        else:
            self.icon_label.clear()


class TabListWidget(QListWidget):
    """Lista de pestañas que cierra una pestaña al hacer clic central sobre ella."""

    middle_clicked = pyqtSignal(int)  # fila bajo el cursor

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None:
                self.middle_clicked.emit(self.row(item))
                return
        super().mousePressEvent(event)

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        if item is not None:
            view = item.data(Qt.ItemDataRole.UserRole)
            main_win = self.window()
            if main_win:
                main_win._dragged_view = view
        super().startDrag(supportedActions)


class Sidebar(QFrame):
    """Barra lateral con la lista de pestañas y controles básicos."""

    new_tab_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(int)  # índice de fila
    tab_selected = pyqtSignal(int)         # índice de fila
    context_menu_requested = pyqtSignal(int, object)  # índice, global_pos
    history_requested = pyqtSignal()
    downloads_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(214)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(6)

        # --- Cabecera: título + nueva pestaña ---
        header = QHBoxLayout()
        header.setContentsMargins(12, 0, 8, 0)
        title = QLabel("Orbital")
        title.setStyleSheet("color:#e3e3e9; font-weight:600; font-size:14px;")

        self.new_button = QPushButton()
        from utils.icon_loader import get_lucide_icon
        self.new_button.setIcon(get_lucide_icon("plus", color="#9696a0", size=14))
        self.new_button.setObjectName("SidebarButton")
        self.new_button.setFixedSize(26, 26)
        self.new_button.setToolTip("Nueva pestaña")
        self.new_button.clicked.connect(self.new_tab_requested.emit)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.new_button)
        layout.addLayout(header)

        # --- Lista de pestañas (con reordenado por arrastre) ---
        self.tab_list = TabListWidget()
        self.tab_list.setObjectName("TabList")
        self.tab_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.tab_list.setSpacing(1)
        self.tab_list.currentRowChanged.connect(self._on_row_changed)
        self.tab_list.middle_clicked.connect(self.close_tab_requested.emit)
        
        # Habilitar menú contextual personalizado
        self.tab_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_list.customContextMenuRequested.connect(self._on_custom_context_menu)
        
        layout.addWidget(self.tab_list)

        # --- Zona inferior: accesos a Historial / Descargas / Configuración ---
        footer = QHBoxLayout()
        footer.setContentsMargins(10, 4, 10, 0)
        footer.setSpacing(4)
        from utils.icon_loader import get_lucide_icon
        for icon_name, tip, signal in (
            ("history", "Historial", self.history_requested),
            ("download", "Descargas", self.downloads_requested),
            ("settings", "Configuración", self.settings_requested),
        ):
            btn = QPushButton()
            btn.setIcon(get_lucide_icon(icon_name, color="#9696a0", size=14))
            btn.setObjectName("SidebarButton")
            btn.setFixedSize(30, 28)
            btn.setToolTip(tip)
            btn.clicked.connect(signal.emit)
            footer.addWidget(btn)
        footer.addStretch()
        layout.addLayout(footer)

    def _on_row_changed(self, row: int) -> None:
        self._apply_selection(row)
        if row >= 0:
            self.tab_selected.emit(row)

    def _on_custom_context_menu(self, pos) -> None:
        item = self.tab_list.itemAt(pos)
        if item is not None:
            row = self.tab_list.row(item)
            global_pos = self.tab_list.mapToGlobal(pos)
            self.context_menu_requested.emit(row, global_pos)

    def _apply_selection(self, row: int) -> None:
        """Marca como activa la fila `row` para pintar su título en blanco.

        El fondo y el borde los gestiona el QSS (::item:selected), pero el color
        del título vive en un QLabel hijo, así que hay que sincronizarlo aquí.
        Se llama también desde `set_current_row`, porque la ventana principal
        cambia de fila con las señales bloqueadas y `_on_row_changed` no dispara.
        """
        for r in range(self.tab_list.count()):
            widget = self._widget_at(r)
            if widget is not None:
                widget.set_selected(r == row)

    # --- API usada por la ventana principal -----------------------------
    # Cada item guarda su WebViewPane en UserRole y muestra un TabItemWidget.
    def add_tab_item(self, view: object, title: str = "Nueva pestaña") -> int:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, view)
        item.setSizeHint(QSize(0, TAB_HEIGHT))
        self.tab_list.addItem(item)

        widget = TabItemWidget(view, title)
        widget.close_clicked.connect(self._on_close_clicked)
        self.tab_list.setItemWidget(item, widget)

        row = self.tab_list.row(item)
        self.tab_list.setCurrentRow(row)
        return row

    def _on_close_clicked(self, view: object) -> None:
        row = self.row_of(view)
        if row >= 0:
            self.close_tab_requested.emit(row)

    def _widget_at(self, row: int) -> TabItemWidget | None:
        item = self.tab_list.item(row)
        if item is None:
            return None
        widget = self.tab_list.itemWidget(item)
        return widget if isinstance(widget, TabItemWidget) else None

    def view_at(self, row: int) -> object | None:
        item = self.tab_list.item(row)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def row_of(self, view: object) -> int:
        for row in range(self.tab_list.count()):
            if self.tab_list.item(row).data(Qt.ItemDataRole.UserRole) is view:
                return row
        return -1

    def set_tab_title(self, row: int, title: str) -> None:
        widget = self._widget_at(row)
        if widget is not None:
            widget.set_title(title)

    def set_tab_icon(self, row: int, icon: QIcon) -> None:
        widget = self._widget_at(row)
        if widget is not None:
            widget.set_icon(icon)

    def remove_tab_item(self, row: int) -> None:
        item = self.tab_list.takeItem(row)
        del item

    def current_row(self) -> int:
        return self.tab_list.currentRow()

    def set_current_row(self, row: int) -> None:
        self.tab_list.setCurrentRow(row)
        self._apply_selection(row)

    def count(self) -> int:
        return self.tab_list.count()
