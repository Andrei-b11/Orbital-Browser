"""Barra de búsqueda dentro de la página (Ctrl+F) — Fase 2.

Emite señales de intención (buscar, siguiente, anterior, cerrar); la lógica de
`page().findText(...)` vive en la ventana principal.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton


class FindBar(QFrame):
    """Barra flotante para buscar texto en la página actual."""

    search = pyqtSignal(str)      # texto a buscar (hacia delante)
    find_next = pyqtSignal()
    find_prev = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FindBar")
        self._build()
        self.hide()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setObjectName("FindInput")
        self.input.setPlaceholderText("Buscar en la página…")
        self.input.textChanged.connect(self.search.emit)
        self.input.returnPressed.connect(self.find_next.emit)

        prev_btn = self._small_button("‹", "Anterior")
        next_btn = self._small_button("›", "Siguiente")
        close_btn = self._small_button("✕", "Cerrar")
        prev_btn.clicked.connect(self.find_prev.emit)
        next_btn.clicked.connect(self.find_next.emit)
        close_btn.clicked.connect(self.dismiss)

        layout.addWidget(self.input)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)
        layout.addWidget(close_btn)

    def _small_button(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setFixedSize(26, 26)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setToolTip(tooltip)
        return btn

    def activate(self) -> None:
        self.show()
        self.input.setFocus()
        self.input.selectAll()

    def dismiss(self) -> None:
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(event)
