"""Normalización de favicons (Fase 2).

Re-colorea los iconos de los sitios web al color del tema para mantener una
identidad visual coherente (estilo Zen/Arc). Implementación basada en Qt
(QPainter) para no exigir Pillow como dependencia obligatoria.

TODO (Fase 2): pipeline avanzado con Pillow (escala de grises + máscara alpha)
descrito en el plan maestro, como modo opcional de mayor calidad.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap


def tint_pixmap(pixmap: QPixmap, hex_color: str) -> QPixmap:
    """Proyecta la silueta del icono usando un único color del tema."""
    if pixmap.isNull():
        return pixmap

    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.drawPixmap(0, 0, pixmap)
    # Conserva sólo la forma (alpha) del icono y la rellena con el color.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), QColor(hex_color))
    painter.end()
    return result


def tint_icon(icon: QIcon, hex_color: str, size: int = 16) -> QIcon:
    """Versión que opera sobre `QIcon` y devuelve un `QIcon` re-coloreado."""
    if icon.isNull():
        return icon
    pixmap = icon.pixmap(size, size)
    return QIcon(tint_pixmap(pixmap, hex_color))
