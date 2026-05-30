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


class TabItemWidget(QWidget):
    """Contenido visual de una pestaña: icono, título y botón de cierre."""

    close_clicked = pyqtSignal(object)  # emite la vista asociada

    def __init__(self, view: object, title: str) -> None:
        super().__init__()
        self.view = view
        self.setObjectName("TabItem")
        self.setFixedHeight(TAB_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(7)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setObjectName("TabIcon")

        self.title_label = _ElidedLabel(title)
        self.title_label.setObjectName("TabTitle")

        self.close_btn = QPushButton()
        from utils.icon_loader import get_lucide_icon
        self.close_btn.setIcon(get_lucide_icon("x", color="#6c6c78", size=10))
        self.close_btn.setObjectName("TabClose")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setToolTip("Cerrar pestaña")
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit(self.view))

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.close_btn)

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


class Sidebar(QFrame):
    """Barra lateral con la lista de pestañas y controles básicos."""

    new_tab_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(int)  # índice de fila
    tab_selected = pyqtSignal(int)         # índice de fila
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
        if row >= 0:
            self.tab_selected.emit(row)

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

    def count(self) -> int:
        return self.tab_list.count()
