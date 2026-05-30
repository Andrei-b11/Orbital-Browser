"""Omnibox: barra de direcciones y búsqueda unificada (Fase 2)."""
from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QWidget


class AddressBar(QLineEdit):
    """Campo de entrada inteligente para URLs y búsquedas cifradas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Omnibox")
        self.setPlaceholderText(
            "Introduce una URL o realiza una búsqueda cifrada…"
        )
        self.setClearButtonEnabled(True)
