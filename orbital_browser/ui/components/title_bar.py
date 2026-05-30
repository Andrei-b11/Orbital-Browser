"""Barra de título estilo Windows 11 para ventana sin bordes (Fase 2).

Reproduce la *caption bar* nativa de las apps de Windows: icono + título a la
izquierda y los controles minimizar / maximizar / cerrar a la derecha, con las
métricas (46×32 px) y los glifos de la fuente «Segoe Fluent Icons».

El arrastre y el redimensionado se delegan al sistema operativo mediante
`QWindow.startSystemMove()`, lo que resulta robusto en Windows.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

class CaptionButton(QPushButton):
    """Botón de control de ventana con las dimensiones estándar de Windows."""

    def __init__(self, icon_name: str, tooltip: str, object_name: str) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setFixedSize(46, 38)
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)
        
        from utils.icon_loader import get_lucide_icon
        self.setIcon(get_lucide_icon(icon_name, color="#c8c8d0", size=10))


class CaptionBar(QFrame):
    """Barra de título superior, arrastrable y a todo el ancho de la ventana."""

    toggle_sidebar = pyqtSignal()

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CaptionBar")
        self.setFixedHeight(38)
        self._build(title)

    def _build(self, title: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Botón para ocultar/mostrar la barra lateral ---
        self.menu_btn = QPushButton()
        from utils.icon_loader import get_lucide_icon
        self.menu_btn.setIcon(get_lucide_icon("menu", color="#c8c8d0", size=14))
        self.menu_btn.setObjectName("CaptionMenu")
        self.menu_btn.setFixedSize(34, 28)
        self.menu_btn.setToolTip("Ocultar/mostrar barra lateral")
        self.menu_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn.clicked.connect(self.toggle_sidebar.emit)

        # --- Título de la aplicación ---
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CaptionTitle")

        # --- Contenedor de pestañas integradas (Fase 2) ---
        self.tabs_container = QWidget()
        self.tabs_container.setObjectName("CaptionTabsContainer")
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(4, 0, 4, 0)
        self.tabs_layout.setSpacing(6)
        self.tabs_layout.addStretch(1)
        self.tabs_container.hide()

        layout.addWidget(self.menu_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(8)
        layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.tabs_container, 1)
        layout.addStretch()

        # --- Controles de ventana ---
        self.min_btn = CaptionButton("minus", "Minimizar", "CaptionMin")
        self.max_btn = CaptionButton("square", "Maximizar", "CaptionMax")
        self.close_btn = CaptionButton("x", "Cerrar", "CaptionClose")

        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(lambda: self.window().close())

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    def _toggle_maximize(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def sync_maximize_glyph(self) -> None:
        """Alterna el glifo maximizar/restaurar según el estado de la ventana."""
        from utils.icon_loader import get_lucide_icon
        if self.window().isMaximized():
            self.max_btn.setIcon(get_lucide_icon("copy", color="#c8c8d0", size=10))
            self.max_btn.setToolTip("Restaurar")
        else:
            self.max_btn.setIcon(get_lucide_icon("square", color="#c8c8d0", size=10))
            self.max_btn.setToolTip("Maximizar")

    # --- Arrastre / maximizar al doble clic (zona libre de la barra) ------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._toggle_maximize()
        super().mouseDoubleClickEvent(event)
